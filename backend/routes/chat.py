"""Streaming chat, stop and clear endpoints."""
import asyncio
import json
import sqlite3
import threading

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

import utils.logs as logs
from backend import workspace
from backend.workspace import (
    configure,
    get_session,
    operation,
    save_conversation,
    snapshot,
)
from utils import ollama
from utils.r2r import R2RClient
from utils.runtime import request_state

router = APIRouter()


@router.delete("/api/chat")
def clear_chat(request: Request):
    session = get_session(request)
    with operation(session):
        session.update(messages=[], chat_history_start=0, rag_history_start=0, title_generated=False)
    return snapshot(session)


class Question(BaseModel):
    text: str = Field(min_length=1, max_length=6000)
    without_documents: bool = False
    regenerate: bool = False


@router.post("/api/chat")
async def chat(question: Question, request: Request):
    session = get_session(request)
    # Acquire before sending stream headers, so concurrent requests get a real 409.
    if not session["lock"].acquire(False):
        raise HTTPException(409, "A task is already running.")
    if question.regenerate:
        messages = session["messages"]
        if len(messages) < 2 or messages[-1]["role"] != "assistant" or messages[-2]["role"] != "user":
            session["lock"].release()
            raise HTTPException(400, "There is no answer to regenerate.")
        question.text = messages[-2]["content"]
        question.without_documents = messages[-2].get("without_documents", False)
        session["messages"] = messages[:-2]
        for key in ("rag_history_start", "chat_history_start"):
            session[key] = min(session.get(key, 0), len(session["messages"]))
    session["cancel"].clear()
    queue = asyncio.Queue()
    loop = asyncio.get_running_loop()
    def emit(payload):
        if not loop.is_closed():
            loop.call_soon_threadsafe(queue.put_nowait, payload)
    def generate():
        content = ""
        chunks = None
        completed = False
        try:
            with request_state(session):
                configure(session)
                session["status"] = "Reading and thinking"
                session["last_doc_passages"] = []
                session["last_rag_no_result"] = False
                session["messages"].append({"role": "user", "content": question.text, "without_documents": question.without_documents})
                cfg = session["config"]
                if cfg.r2r and not question.without_documents:
                    if not session.get("r2r_document_ids") or session.get("r2r_ingestion_failed"):
                        raise ValueError("Upload documents to R2R before asking a question.")
                    chunks = [R2RClient(cfg.r2r_url, cfg.r2r_key).rag(question.text, session["r2r_document_ids"])]
                elif session.get("query_engine") and not question.without_documents:
                    chunks = ollama.context_chat(question.text, session["query_engine"])
                else:
                    chunks = ollama.chat(question.text)
                for chunk in chunks:
                    if session["cancel"].is_set():
                        break
                    content += chunk
                    emit({"type": "token", "text": chunk})
                sources = session.get("last_doc_passages", [])
                message = {"role": "assistant", "content": content, "sources": sources,
                    "stopped": session["cancel"].is_set(),
                    "no_evidence": session.get("last_rag_no_result", False)}
                session["messages"].append(message)
                completed = not message["stopped"] and bool(content.strip())
                emit({"type": "done", "message": message})
        except Exception as error:  # noqa: BLE001 - any provider failure ends the stream with a message
            logs.log.exception("Chat answer failed")
            message = {"role": "assistant", "content": content + "\n\nResponse interrupted: " + str(error), "sources": []}
            session["messages"].append(message)
            emit({"type": "error", "message": message})
        finally:
            try:
                if hasattr(chunks, "close"):
                    chunks.close()
                save_conversation(session)
                if completed:
                    workspace.start_title(session)
            except (OSError, sqlite3.Error) as error:
                logs.log.error(f"Saving the conversation failed: {error}")
                emit({"type": "warning", "text": "The answer is available, but could not be saved to disk. Export it before closing."})
            finally:
                session["status"] = "Ready"
                session["lock"].release()
                emit(None)
    threading.Thread(target=generate, daemon=True).start()
    async def events():
        try:
            while True:
                value = await queue.get()
                if value is None:
                    break
                yield json.dumps(value) + "\n"
        finally:
            if session["lock"].locked():
                session["cancel"].set()
    return StreamingResponse(events(), media_type="application/x-ndjson", headers={"Cache-Control": "no-store"})


@router.post("/api/chat/stop")
def stop_chat(request: Request):
    session = get_session(request)
    session["cancel"].set()
    return {"stopping": True}
