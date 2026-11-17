"""Source upload, import, retry, replace and removal endpoints."""
import asyncio
import secrets
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from backend.sources import (
    clear_corpus,
    commit_documents,
    corpus_changed,
    ingest_uploads,
    put_source,
    read_uploads,
    source_record,
    tag_documents,
)
from backend.workspace import get_session, operation, snapshot
from utils import helpers
from utils import llama_index as indexer
from utils.r2r import R2RClient

router = APIRouter()


@router.post("/api/upload")
async def upload(request: Request, files: list[UploadFile]):
    session = get_session(request)
    uploads = await read_uploads(files)
    try:
        return await asyncio.to_thread(ingest_uploads, session, uploads)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(400, str(error)) from error


class ImportSource(BaseModel):
    kind: Literal["website", "github", "sample"]
    value: str = Field(default="", max_length=4000)


@router.post("/api/import")
def import_source(source: ImportSource, request: Request):
    session = get_session(request)
    try:
        with operation(session):
            if session["config"].r2r:
                raise ValueError("R2R supports file uploads. Turn it off to import this source.")
            session["status"] = "Reading source content"
            warnings = []
            if source.kind == "website":
                docs = helpers.load_website_documents(source.value.splitlines())
            elif source.kind == "github":
                repo = helpers.normalize_github_repo(source.value)
                directory = helpers.clone_github_repo(repo)
                if not directory:
                    raise ValueError("Repository could not be cloned. Check its name and public access.")
                try:
                    docs = indexer.load_documents(directory, errors=warnings)
                finally:
                    helpers.remove_dir_retry(directory)
            else:
                from llama_index.core.schema import Document
                docs = [Document(text=("Northstar Studio — Project brief (sample document).\n"
                    "The Aurora website redesign launches on November 12, 2026. The budget is $24,000. "
                    "Maya Chen leads design and Omar Shah leads engineering. The project covers a new "
                    "homepage, product pages, and accessible navigation. The first design review is October 22. "
                    "Success means a 20 percent improvement in sign-up conversion and a page load time under 2 seconds. "
                    "The launch depends on content approval by November 5. The project does not include a mobile app."),
                    metadata={"file_name": "Northstar — Project brief.txt"})]
            grouped = {}
            for doc in docs:
                name = doc.metadata.get("file_name") or doc.metadata.get("source") or "Document"
                grouped.setdefault(name, []).append(doc)
            for group in grouped.values():
                tag_documents(group, secrets.token_hex(16), source.kind)
            commit_documents(session, session["documents"] + docs, warnings)
        return snapshot(session)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(400, str(error)) from error


@router.delete("/api/sources")
def delete_sources(request: Request):
    session = get_session(request)
    with operation(session):
        clear_corpus(session)
    return snapshot(session)


@router.delete("/api/sources/{source_id}")
def delete_source(source_id: str, request: Request):
    session = get_session(request)
    with operation(session):
        source = source_record(session, source_id)
        if source.get("remote_id"):
            if R2RClient(**session["r2r_document_origin"]).delete_documents([source["remote_id"]]):
                raise HTTPException(502, "Remote source could not be deleted. Retry when R2R is available.")
            session["r2r_document_ids"].remove(source["remote_id"])
        elif source.get("status") != "error":
            docs = [d for d in session["documents"] if d.metadata.get("docmind_source_id") != source_id]
            try:
                commit_documents(session, docs)
            except Exception as error:
                raise HTTPException(400, str(error)) from error
        session["sources"] = [s for s in session["sources"] if s["id"] != source_id]
        session["source_inputs"].pop(source_id, None)
        corpus_changed(session)
    return snapshot(session)


@router.post("/api/sources/{source_id}/retry")
def retry_source(source_id: str, request: Request):
    session = get_session(request)
    with operation(session):
        source_record(session, source_id)
        try:
            item = session["source_inputs"].get(source_id)
            if item:
                put_source(session, source_id, item)
            else:
                # Imported website/repository text can be reindexed without another network fetch.
                commit_documents(session, session["documents"])
        except Exception as error:
            raise HTTPException(400, str(error)) from error
    return snapshot(session)


@router.put("/api/sources/{source_id}")
async def replace_source(source_id: str, request: Request, files: list[UploadFile]):
    session = get_session(request)
    uploads = await read_uploads(files)
    if len(uploads) != 1:
        raise HTTPException(400, "Choose exactly one replacement file.")
    def replace():
        with operation(session):
            source_record(session, source_id)
            try:
                put_source(session, source_id, {"kind": "file", "name": uploads[0].name, "data": uploads[0].getvalue()})
            except Exception as error:
                raise HTTPException(400, str(error)) from error
        return snapshot(session)
    return await asyncio.to_thread(replace)
