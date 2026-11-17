"""Session, settings and model discovery endpoints."""
import hashlib
import re
import secrets
import time

from fastapi import APIRouter, HTTPException, Request, Response

from backend import history
from backend.settings import Settings
from backend.sources import clear_corpus, restore_sources
from backend.workspace import (
    COOKIE,
    configure,
    get_session,
    new_session,
    open_conversation,
    operation,
    save_conversation,
    sessions,
    sessions_lock,
    snapshot,
)
from utils import ollama
from utils.runtime import request_state
from utils.session_workspace import clear_session_workspace

router = APIRouter()


@router.get("/api/health")
def health():
    return {"ok": True}


@router.post("/api/session")
def init(request: Request, response: Response):
    token = request.cookies.get(COOKIE)
    with sessions_lock:
        # Local workspaces expire after eight idle hours; never discard remote cleanup IDs.
        for key, state in list(sessions.items()):
            if time.monotonic() - state["touched"] > 28800 and not state["lock"].locked() and not state.get("r2r_document_ids"):
                clear_session_workspace(state)
                del sessions[key]
        if token not in sessions:
            if len(sessions) >= 64:
                raise HTTPException(503, "Too many workspaces. Restart the local server to release them.")
            owner = hashlib.sha256(token.encode()).hexdigest() if token and re.fullmatch(r"[\w-]{43}", token) else ""
            saved = history.listing(owner) if owner else []
            if not saved or not token:
                token = secrets.token_urlsafe(32)
                owner = hashlib.sha256(token.encode()).hexdigest()
            sessions[token] = new_session()
            sessions[token]["owner"] = owner
            if saved:
                open_conversation(sessions[token], history.read(owner, saved[0]["id"]))
                restore_sources(sessions[token])
            else:
                save_conversation(sessions[token])
        session = sessions[token]
    assert token is not None  # every branch above finds or creates a token
    response.set_cookie(COOKIE, token, httponly=True, samesite="strict", max_age=365 * 86400)
    return snapshot(session)


@router.get("/api/state")
def state(request: Request):
    return snapshot(get_session(request))


@router.put("/api/settings")
def settings(config: Settings, request: Request):
    session = get_session(request)
    with operation(session):
        old = session["config"]
        if not config.api_key and old.endpoint == config.endpoint and old.provider == config.provider:
            config.api_key = old.api_key
        if not config.r2r_key and old.r2r_url == config.r2r_url:
            config.r2r_key = old.r2r_key
        index_keys = ("provider", "endpoint", "embedding_model", "chunk_size", "overlap", "api_key", "r2r", "r2r_url", "r2r_key")
        if any(getattr(old, key) != getattr(config, key) for key in index_keys):
            clear_corpus(session)
        session["config"] = config
        configure(session)
    return snapshot(session)


@router.get("/api/models")
def models(request: Request):
    session = get_session(request)
    probe = {"config": session["config"]}
    # Discovery is read-only: do not lock out settings or chat while a server is slow.
    with request_state(probe):
        configure(probe)
        if probe["config"].provider == "Ollama":
            chat, embeddings = ollama.get_models(), ollama.get_embedding_models()
        else:
            chat = ollama.get_openai_models(probe["config"].endpoint, probe["config"].api_key)
            embeddings = chat
    return {"chat": chat, "embeddings": embeddings, "online": bool(chat)}


@router.delete("/api/session")
def reset(request: Request):
    session = get_session(request)
    with operation(session):
        clear_corpus(session)
        history.delete(session["owner"])
        session.update(conversation_id=secrets.token_hex(16), title="New conversation", renamed=False, title_generated=False)
        session.update(config=Settings(), messages=[], chat_history_start=0, rag_history_start=0)
    return snapshot(session)
