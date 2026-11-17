"""In-memory workspaces keyed by an HttpOnly cookie, and their conversation state.

Run one API worker: document indexes live in this process."""
import secrets
import threading
import time
from contextlib import contextmanager

from fastapi import HTTPException

from backend import history
from backend.settings import Settings
from utils import helpers, ollama
from utils.runtime import request_state

sessions = {}


sessions_lock = threading.Lock()


COOKIE = "docmind_workspace"


def new_session():
    return {"config": Settings(), "messages": [], "sources": [], "warnings": [],
            "documents": [], "query_engine": None, "lock": threading.Lock(),
            "conversation_id": secrets.token_hex(16), "title": "New conversation", "renamed": False,
            "title_generated": False, "naming_titles": set(),
            "corpus_id": "empty", "source_inputs": {}, "cancel": threading.Event(),
            "touched": time.monotonic(), "status": "Ready", "progress": None}


def save_conversation(session):
    if not session.get("owner"):
        return
    if not session["renamed"] and not session.get("title_generated"):
        first = next((m["content"] for m in session["messages"] if m["role"] == "user"), "")
        session["title"] = " ".join(first.split()[:8])[:70] or "New conversation"
    history.save(session["owner"], session["conversation_id"], session["title"], {
        "messages": session["messages"], "renamed": session["renamed"], "corpus_id": session["corpus_id"],
        "title_generated": session.get("title_generated", False),
        "rag_history_start": session.get("rag_history_start", 0), "chat_history_start": session.get("chat_history_start", 0)})


def open_conversation(session, record):
    payload = record["payload"]
    messages = payload["messages"]
    same_corpus = payload.get("corpus_id") == session["corpus_id"]
    session.update(conversation_id=record["id"], title=record["title"], messages=messages,
        renamed=payload.get("renamed", False), title_generated=payload.get("title_generated", False),
        rag_history_start=payload.get("rag_history_start", 0) if same_corpus else len(messages),
        chat_history_start=payload.get("chat_history_start", 0) if same_corpus else len(messages))


def start_title(session):
    """Name once in the background; re-read ownership/state before saving the result."""
    conversation_id = session["conversation_id"]
    if session["renamed"] or session.get("title_generated") or conversation_id in session["naming_titles"]:
        return
    cfg = session["config"].model_copy()
    owner = session["owner"]
    question = next(m["content"] for m in session["messages"] if m["role"] == "user")
    answer = session["messages"][-1]["content"]
    session["naming_titles"].add(conversation_id)

    def generate_title():
        title = ""
        try:
            if not cfg.r2r:
                with request_state({"eco_mode": cfg.eco}):
                    title = ollama.conversation_title(question, answer, model=cfg.chat_model,
                        base_url=cfg.endpoint, api_key=cfg.api_key, backend=cfg.provider)
        except Exception:
            pass  # Naming is optional; keep the saved fallback if the provider is unavailable.
        try:
            with session["lock"]:
                record = history.read(owner, conversation_id)
                first = next((m["content"] for m in record["payload"]["messages"] if m["role"] == "user"), "") if record else ""
                if record and first == question and not record["payload"].get("renamed"):
                    title = title or record["title"]
                    record["payload"]["title_generated"] = True
                    history.save(owner, conversation_id, title, record["payload"])
                    if session["conversation_id"] == conversation_id:
                        session.update(title=title, title_generated=True)
        except Exception:
            pass  # A title failure must never interrupt an answer or resurrect a deleted chat.
        finally:
            with session["lock"]:
                session["naming_titles"].discard(conversation_id)

    thread = threading.Thread(target=generate_title, daemon=True)
    thread.start()
    return thread


def get_session(request):
    with sessions_lock:
        session = sessions.get(request.cookies.get(COOKIE))
    if session is None:
        raise HTTPException(401, "Workspace expired. Reload to start a new session.")
    session["touched"] = time.monotonic()
    return session


@contextmanager
def operation(session):
    if not session["lock"].acquire(blocking=False):
        raise HTTPException(409, "A task is still running. Wait for it to finish.")
    try:
        with request_state(session):
            configure(session)
            yield
            save_conversation(session)
    finally:
        session["progress"] = None
        session["status"] = "Ready"
        session["lock"].release()


def configure(session):
    cfg = session["config"]
    session.update(llm_backend=cfg.provider, selected_model=cfg.chat_model,
        ollama_endpoint=cfg.endpoint, ollama_embedding_model=cfg.embedding_model,
        openai_base_url=cfg.endpoint, openai_model=cfg.chat_model,
        openai_embedding_model=cfg.embedding_model, openai_api_key=cfg.api_key,
        temperature=cfg.temperature, top_k=cfg.top_k, similarity_cutoff=cfg.similarity,
        eco_mode=cfg.eco, system_prompt=f"You are DocMind, a careful document assistant. Answer in a {cfg.style.lower()} style. Be factual and cite supplied evidence.")


def snapshot(session):
    return {"settings": session["config"].model_dump(exclude={"api_key", "r2r_key"}),
        "conversation_id": session["conversation_id"], "title": session["title"],
        "naming": bool(session["naming_titles"]),
        "conversations": history.listing(session["owner"]) if session.get("owner") else [],
        "sources": session["sources"], "messages": session["messages"],
        "warnings": session["warnings"], "busy": session["lock"].locked(),
        "status": session["status"], "progress": session["progress"],
        "has_index": session.get("query_engine") is not None or bool(session.get("r2r_document_ids")),
        "formats": sorted(helpers.ALLOWED_UPLOAD_EXTENSIONS)}
