"""Per-session on-disk index cache keyed by content and embedding settings."""
import hashlib
import json
import os
import re
import shutil
from pathlib import Path

import utils.logs as logs
from llama_index.core import (
    StorageContext,
    load_index_from_storage,
)
from utils import runtime
from utils.llama_index.ingestion import _document_text
from utils.llama_index.settings import INDEX_CACHE_KEEP, INDEX_CACHE_VERSION
from utils.session_workspace import session_directory


def index_cache_key(documents) -> str:
    """Return a stable cache key for a document set + embedding settings."""
    hasher = hashlib.sha256()
    hasher.update(str(INDEX_CACHE_VERSION).encode("utf-8"))
    hasher.update(json.dumps(runtime.st.session_state.get("embedding_config", {}), sort_keys=True).encode())
    records = []
    for document in documents:
        metadata = {key: value for key, value in (getattr(document, "metadata", {}) or {}).items()
                    if key not in {"file_path", "creation_date", "last_modified_date", "file_size"}}
        records.append(json.dumps([_document_text(document), metadata], sort_keys=True, ensure_ascii=False))
    # A structured list preserves record boundaries: ['ab', 'c'] != ['a', 'bc'].
    hasher.update(json.dumps(sorted(records), ensure_ascii=False).encode("utf-8"))
    return hasher.hexdigest()[:20]


def index_cache_dir(documents) -> str | None:
    """Return the cache directory for these documents, or None on failure."""
    try:
        return str(session_directory("cache") / index_cache_key(documents))
    except (OSError, RuntimeError, ValueError):  # no workspace or unwritable temp dir
        return None


def load_index_from_cache(cache_dir: str):
    """Load a persisted index, or return None if it can't be restored."""
    try:
        if Path(cache_dir).resolve().parent != session_directory("cache").resolve():
            return None
        if not os.path.isdir(cache_dir):
            return None
        storage_context = StorageContext.from_defaults(persist_dir=cache_dir)
        index = load_index_from_storage(storage_context, embed_model=runtime.st.session_state["embedding_model"])
        logs.log.info(f"Index loaded from cache: {cache_dir}")
        return index
    except Exception as err:  # noqa: BLE001 - any unreadable cache is rebuilt from source
        logs.log.warning(f"Failed to load cached index, rebuilding: {err}")
        return None


def persist_index_to_cache(index, cache_dir: str):
    """Persist an index to disk and prune old caches."""
    try:
        if Path(cache_dir).resolve().parent != session_directory("cache").resolve():
            raise ValueError("Cache directory does not belong to this session.")
        os.makedirs(cache_dir, exist_ok=True)
        index.storage_context.persist(persist_dir=cache_dir)
        logs.log.info(f"Index persisted to cache: {cache_dir}")
        _prune_index_cache()
        return True
    except (OSError, ValueError) as err:
        logs.log.warning(f"Failed to persist index cache: {err}")
        return False


def _prune_index_cache(keep: int = INDEX_CACHE_KEEP):
    """Remove the oldest cache entries beyond `keep`."""
    try:
        cache_root = session_directory("cache")
        entries = sorted(
            (
                os.path.getmtime(os.path.join(cache_root, name)),
                os.path.join(cache_root, name),
            )
            for name in os.listdir(cache_root)
            if re.fullmatch(r"[0-9a-f]{20}", name) and (cache_root / name).is_dir()
            and not (cache_root / name).is_symlink()
        )
        for _, path in entries[:-keep]:
            shutil.rmtree(path, ignore_errors=True)
    except OSError as err:
        logs.log.debug(f"Index cache pruning skipped: {err}")


###################################
#
# Create Query Engine
#
###################################
