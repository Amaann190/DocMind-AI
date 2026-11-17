"""Saved conversation endpoints and Word export."""
import io
import secrets

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from backend import history
from backend.workspace import (
    get_session,
    open_conversation,
    operation,
    save_conversation,
    snapshot,
)

router = APIRouter()


@router.post("/api/conversations")
def new_conversation(request: Request):
    session = get_session(request)
    with operation(session):
        save_conversation(session)
        if session["messages"]:
            draft = next((c for c in history.listing(session["owner"]) if not c["started"]), None)
            if draft:
                open_conversation(session, history.read(session["owner"], draft["id"]))
            else:
                session.update(conversation_id=secrets.token_hex(16), title="New conversation", renamed=False, title_generated=False,
                               messages=[], rag_history_start=0, chat_history_start=0)
    return snapshot(session)


@router.get("/api/conversations")
def search_conversations(request: Request, q: str = ""):
    return history.listing(get_session(request)["owner"], q[:200])


class ConversationTitle(BaseModel):
    title: str = Field(min_length=1, max_length=100)


@router.put("/api/conversations/{conversation_id}")
def rename_conversation(conversation_id: str, title: ConversationTitle, request: Request):
    session = get_session(request)
    if not title.title.strip():
        raise HTTPException(400, "Enter a conversation name.")
    with operation(session):
        record = history.read(session["owner"], conversation_id)
        if not record:
            raise HTTPException(404, "Conversation not found.")
        record["payload"]["renamed"] = True
        history.save(session["owner"], conversation_id, title.title.strip(), record["payload"])
        if conversation_id == session["conversation_id"]:
            session.update(title=title.title.strip(), renamed=True)
    return snapshot(session)


@router.post("/api/conversations/{conversation_id}/open")
def switch_conversation(conversation_id: str, request: Request):
    session = get_session(request)
    with operation(session):
        record = history.read(session["owner"], conversation_id)
        if not record:
            raise HTTPException(404, "Conversation not found.")
        save_conversation(session)
        open_conversation(session, record)
    return snapshot(session)


@router.delete("/api/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, request: Request):
    session = get_session(request)
    with operation(session):
        if not history.read(session["owner"], conversation_id):
            raise HTTPException(404, "Conversation not found.")
        history.delete(session["owner"], conversation_id)
        if conversation_id == session["conversation_id"]:
            session.update(conversation_id=secrets.token_hex(16), title="New conversation", renamed=False, title_generated=False,
                           messages=[], rag_history_start=0, chat_history_start=0)
    return snapshot(session)


@router.get("/api/export")
def export(request: Request):
    from docx import Document
    session = get_session(request)
    document = Document()
    document.add_heading("DocMind — Conversation", 0)
    for message in list(session["messages"]):
        document.add_heading(message["role"].title(), 2)
        document.add_paragraph(message["content"])
        for source in message.get("sources", []):
            document.add_paragraph(f"[{source['number']}] {source['name']}\n{source['text']}")
    output = io.BytesIO()
    document.save(output)
    return Response(output.getvalue(), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": 'attachment; filename="DocMind-conversation.docx"'})
