"""Source lifecycle: reading uploads, indexing, replacing and removing sources."""
import io
import secrets
import tempfile
import threading
from pathlib import Path

from fastapi import HTTPException

import utils.logs as logs
from backend import history, source_store
from backend.settings import Settings
from backend.workspace import configure, open_conversation, operation, snapshot, sync_sources
from utils import helpers, ollama
from utils import llama_index as indexer
from utils.r2r import R2RClient, clear_remote_documents
from utils.runtime import request_state
from utils.session_workspace import clear_session_workspace, session_directory


def clear_corpus(session):
    if not clear_remote_documents(session):
        session["r2r_ingestion_failed"] = True
        raise HTTPException(502, "Remote documents could not be deleted. Restore the original R2R connection and retry.")
    session.update(query_engine=None, retriever=None, documents=[], sources=[], warnings=[],
        source_inputs={}, corpus_id="empty",
        last_doc_sources=[], last_doc_passages=[], last_rag_no_result=False,
        rag_history_start=len(session["messages"]), chat_history_start=len(session["messages"]))
    clear_session_workspace(session)


def index_documents(session, documents, kind, warnings=None):
    if not documents:
        raise ValueError("At least one readable document is required.")
    helpers.validate_ingested_documents(documents)
    cfg = session["config"]
    session["status"] = "Connecting to embedding model"
    session_directory("cache", session)
    candidate = dict(session)
    def progress(done, total):
        session["status"] = "Building your document index"
        session["progress"] = {"done": done, "total": total}
    # Build separately: a failed replacement must not destroy the working index.
    with request_state(candidate):
        indexer.setup_embedding_model(cfg.embedding_model, cfg.chunk_size, cfg.overlap, cfg.provider, cfg.endpoint, cfg.api_key)
        candidate["llm"] = ollama.create_llm(cfg.chat_model, cfg.endpoint, cfg.api_key, backend=cfg.provider)
        indexer.create_query_engine(documents, progress_callback=progress)
    for key in ("embedding_model", "embedding_config", "llm", "retriever", "query_engine"):
        session[key] = candidate.get(key)
    session["documents"] = documents
    grouped = {}
    for doc in documents:
        name = doc.metadata.get("file_name") or doc.metadata.get("source") or "Document"
        source_id = doc.metadata.get("docmind_source_id", name)
        grouped.setdefault(source_id, {"name": name, "kind": doc.metadata.get("docmind_kind", kind), "texts": []})["texts"].append(doc.get_content())
    session["sources"] = [{"id": source_id, "name": group["name"], "kind": group["kind"], "status": "ready",
        "characters": sum(map(len, group["texts"])), "preview": "\n\n".join(group["texts"])[:16000]}
        for source_id, group in grouped.items()]
    session["warnings"] = warnings or []


def tag_documents(documents, source_id, kind):
    for doc in documents:
        doc.metadata.update(docmind_source_id=source_id, docmind_kind=kind)
        for key in ("docmind_source_id", "docmind_kind"):
            if key not in doc.excluded_embed_metadata_keys:
                doc.excluded_embed_metadata_keys.append(key)
            if key not in doc.excluded_llm_metadata_keys:
                doc.excluded_llm_metadata_keys.append(key)
    return documents


def corpus_changed(session):
    corpus_id = secrets.token_hex(16) if session.get("query_engine") or session.get("r2r_document_ids") else "empty"
    session.update(corpus_id=corpus_id, rag_history_start=len(session["messages"]),
                   chat_history_start=len(session["messages"]), last_doc_sources=[], last_doc_passages=[])


def commit_documents(session, documents, warnings=None):
    # ponytail: rebuild the bounded (300 documents / 4 MB text) index per edit;
    # use incremental indexing if measured edit latency becomes a problem.
    failed = [s for s in session["sources"] if s.get("status") == "error"]
    if documents:
        index_documents(session, documents, "file", warnings)
    else:
        session.update(documents=[], sources=[], query_engine=None, retriever=None, warnings=warnings or [])
    ready_ids = {s["id"] for s in session["sources"]}
    session["sources"].extend(s for s in failed if s["id"] not in ready_ids)
    corpus_changed(session)


def source_record(session, source_id):
    source = next((s for s in session["sources"] if s["id"] == source_id), None)
    if source is None:
        raise HTTPException(404, "Source not found in this workspace.")
    return source


def load_input(session, item, source_id):
    warnings = []
    with tempfile.TemporaryDirectory(dir=session_directory("data")) as directory:
        upload = io.BytesIO(item["data"])
        upload.name = item["name"]
        helpers.save_uploaded_file(upload, directory)
        docs = indexer.load_documents(directory, input_files=[str(Path(directory) / item["name"])], errors=warnings)
    if not docs:
        raise ValueError("; ".join(map(str, warnings)) or "No readable text found. Replace this file with a readable copy.")
    return tag_documents(docs, source_id, "file"), warnings


def remote_upload(session, item):
    cfg = session["config"]
    client = R2RClient(cfg.r2r_url, cfg.r2r_key)
    ids = []
    session["r2r_document_origin"] = {"base_url": client.base_url, "api_key": cfg.r2r_key}
    try:
        with tempfile.TemporaryDirectory(dir=session_directory("data")) as directory:
            upload = io.BytesIO(item["data"])
            upload.name = item["name"]
            helpers.save_uploaded_file(upload, directory)
            client.upload_documents([str(Path(directory) / item["name"])], ids)
        return ids[0]
    except Exception:
        # Preserve timed-out uploads for a later owned-ID cleanup.
        failed = client.delete_documents(ids)
        session.setdefault("r2r_document_ids", []).extend(failed)
        if failed:
            session["r2r_ingestion_failed"] = True
        raise


def put_source(session, source_id, item):
    previous = next((s for s in session["sources"] if s["id"] == source_id), None)
    retained = sum(len(v.get("data", b"")) for k, v in session["source_inputs"].items() if k != source_id)
    if retained + len(item.get("data", b"")) > helpers.MAX_TOTAL_UPLOAD_BYTES:
        raise ValueError("This workspace can retain up to 100 MB of files. Remove a source first.")
    if session["config"].r2r:
        remote_id = remote_upload(session, item)
        if previous and previous.get("remote_id"):
            client = R2RClient(**session["r2r_document_origin"])
            if client.delete_documents([previous["remote_id"]]):
                failed = client.delete_documents([remote_id])
                session.setdefault("r2r_document_ids", []).extend(failed)
                if failed:
                    session["r2r_ingestion_failed"] = True
                raise ValueError("The old remote source could not be removed. It has been kept; retry when R2R is available.")
            session["r2r_document_ids"].remove(previous["remote_id"])
        session.setdefault("r2r_document_ids", []).append(remote_id)
        session["sources"] = [s for s in session["sources"] if s["id"] != source_id] + [{
            "id": source_id, "name": item["name"], "kind": "r2r", "status": "ready", "remote_id": remote_id,
            "characters": 0, "preview": "This document is indexed on your R2R server."}]
        corpus_changed(session)
    else:
        docs, warnings = load_input(session, item, source_id)
        remaining = [d for d in session["documents"] if d.metadata.get("docmind_source_id") != source_id]
        commit_documents(session, remaining + docs, warnings)
    session["source_inputs"][source_id] = item


async def read_uploads(files):
    if not files or len(files) > 10:
        raise HTTPException(400, "Choose 1–10 files.")
    uploads, total = [], 0
    try:
        for file in files:
            helpers.safe_uploaded_filename(file.filename)
            data = await file.read(helpers.MAX_UPLOAD_FILE_BYTES + 1)
            total += len(data)
            if len(data) > helpers.MAX_UPLOAD_FILE_BYTES or total > helpers.MAX_TOTAL_UPLOAD_BYTES:
                raise ValueError("Use files under 25 MB each and 100 MB combined.")
            item = io.BytesIO(data)
            item.name = file.filename
            uploads.append(item)
        helpers.validate_uploaded_files(uploads)
        return uploads
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    finally:
        for file in files:
            await file.close()


def ingest_uploads(session, uploads):
    with operation(session):
        session["status"] = "Reading your documents"
        warnings = []
        for upload in uploads:
            if len(session["sources"]) >= 300:
                raise ValueError("Remove a source before adding more than 300 sources.")
            source_id = secrets.token_hex(16)
            item = {"kind": "file", "name": upload.name, "data": upload.getvalue()}
            retained = sum(len(v.get("data", b"")) for v in session["source_inputs"].values())
            if retained + len(item["data"]) > helpers.MAX_TOTAL_UPLOAD_BYTES:
                raise ValueError("This workspace can retain up to 100 MB of files. Remove a source first.")
            try:
                put_source(session, source_id, item)
                warnings.extend(session["warnings"])
            except Exception as error:  # noqa: BLE001 - a failed file is recorded and the rest continue
                session["source_inputs"][source_id] = item
                session["sources"].append({"id": source_id, "name": item["name"], "kind": "file", "status": "error",
                    "characters": 0, "preview": "", "error": str(error)})
                warnings.append({"file": item["name"], "error": str(error)})
        session["warnings"] = warnings
    return snapshot(session)


def restore_sources(session):
    """Rebuild opt-in saved sources in the background after a backend restart.

    Returns the restoring thread, or None when nothing is saved. The workspace
    lock is held until the index is rebuilt, so the UI shows progress and
    other operations wait.
    """
    bundle = source_store.load(session["owner"])
    if not bundle:
        return None
    try:
        config = Settings(**{**bundle["settings"], "keep_sources": True})
    except ValueError as error:
        logs.log.warning(f"Discarding saved sources with invalid settings: {error}")
        try:
            source_store.delete(session["owner"])
        except OSError as delete_error:
            logs.log.error(f"Could not delete invalid saved sources: {delete_error}")
        return None
    saved = [{**source, "preview": ""} for source in bundle["sources"]]
    session.update(config=config, sources=[{**s, "status": "restoring"} for s in saved],
                   status="Restoring your sources")
    session["lock"].acquire()

    def rebuild():
        try:
            with request_state(session):
                configure(session)
                session["source_inputs"] = source_store.inputs(bundle)
                documents = source_store.documents(bundle)
                try:
                    if documents:
                        index_documents(session, documents, "file")
                    else:
                        session["sources"] = []
                except Exception as error:  # noqa: BLE001 - e.g. the embedding server is not running yet
                    logs.log.warning(f"Restoring sources failed: {error}")
                    session["documents"] = documents
                    session["sources"] = [{**s, "status": "error", "error": (
                        f"Could not rebuild the index after restart: {error} Retry when the model server is available.")}
                        for s in saved]
                else:
                    ready = {s["id"] for s in session["sources"]}
                    session["sources"].extend(s for s in saved if s["id"] not in ready)
                session["corpus_id"] = bundle["corpus_id"]
                record = history.read(session["owner"], session["conversation_id"])
                if record:
                    open_conversation(session, record)
                sync_sources(session)
        finally:
            session.update(status="Ready", progress=None)
            session["lock"].release()

    thread = threading.Thread(target=rebuild, daemon=True)
    thread.start()
    return thread
