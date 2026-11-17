"""Opt-in persistence of a workspace's sources across backend restarts.

Off by default: with ``keep_sources`` disabled, uploads and indexes stay in
temporary storage and disappear when the backend stops. When a user turns it on,
the extracted document text, source list and original uploaded files are saved
as one JSON file per workspace owner under the data directory (next to the
conversation history). Nothing is encrypted; credentials are never saved.
Turning the setting off, resetting the workspace or removing all sources
deletes the file. R2R workspaces are not persisted (their documents live on the
R2R server).
"""
import base64
import json
import os
import tempfile
from pathlib import Path

from llama_index.core.schema import Document

from backend import history

VERSION = 1


def _path(owner):
    if not owner or not all(c in "0123456789abcdef" for c in owner):
        raise ValueError("Invalid workspace owner.")
    return Path(history.DB_PATH).parent / "sources" / f"{owner}.json"


def enabled(session):
    config = session["config"]
    return bool(getattr(config, "keep_sources", False)) and not config.r2r


def sync(session):
    """Save or delete the owner's sources to match the current workspace and setting."""
    owner = session.get("owner")
    if not owner:
        return
    if not enabled(session) or not session["sources"]:
        delete(owner)
        session["_saved_corpus"] = None
        return
    fingerprint = (session["corpus_id"], tuple(sorted(session["source_inputs"])), len(session["sources"]))
    if session.get("_saved_corpus") == fingerprint:
        return
    payload = {
        "version": VERSION,
        "settings": session["config"].model_dump(exclude={"api_key", "r2r_key"}),
        "corpus_id": session["corpus_id"],
        "sources": [{k: v for k, v in source.items() if k != "preview"} for source in session["sources"]],
        "documents": [{"text": doc.get_content(), "metadata": doc.metadata,
                       "excluded_embed": list(doc.excluded_embed_metadata_keys),
                       "excluded_llm": list(doc.excluded_llm_metadata_keys)} for doc in session["documents"]],
        "inputs": {source_id: {"kind": item["kind"], "name": item["name"],
                               "data": base64.b64encode(item["data"]).decode("ascii")}
                   for source_id, item in session["source_inputs"].items() if "data" in item},
    }
    path = _path(owner)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write atomically so a crash never leaves a half-written file behind.
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp") as handle:
        json.dump(payload, handle)
        temporary = handle.name
    os.replace(temporary, path)
    session["_saved_corpus"] = fingerprint


def load(owner):
    """Return the saved bundle for this owner, or None."""
    try:
        path = _path(owner)
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if data.get("version") == VERSION else None


def delete(owner):
    """Remove the saved copy. OSError propagates: callers must tell the user it is still on disk."""
    try:
        path = _path(owner)
    except ValueError:
        return
    path.unlink(missing_ok=True)


def documents(bundle):
    """Rebuild LlamaIndex documents from a saved bundle."""
    result = []
    for item in bundle["documents"]:
        doc = Document(text=item["text"], metadata=item["metadata"])
        doc.excluded_embed_metadata_keys = item.get("excluded_embed", [])
        doc.excluded_llm_metadata_keys = item.get("excluded_llm", [])
        result.append(doc)
    return result


def inputs(bundle):
    return {source_id: {"kind": item["kind"], "name": item["name"], "data": base64.b64decode(item["data"])}
            for source_id, item in bundle.get("inputs", {}).items()}
