from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session

from app.db.session import get_session
from app.models.user import User
from app.routers.auth import get_current_user_auth
from app.schemas.chat import (
    ChatAnswerResponse,
    ChatMessageCreate,
    ChatMessageItem,
    ChatSessionCreateResponse,
    ChatSessionListItem,
    ChatSessionListResponse,
)
from app.services.attachments.service import AttachmentService
from app.services.attachments.validator import AttachmentValidationError
from app.services.chat_memory_service import ChatMemoryService

router = APIRouter(prefix="/chat", tags=["Chat Memory"])


@router.post("/ask", response_model=ChatAnswerResponse)
async def ask_chat(
    body: Optional[ChatMessageCreate] = None,
    message: Optional[str] = Form(default=None),
    session_id: Optional[str] = Form(default=None),
    model: Optional[str] = Form(default="auto"),
    context_limit: int = Form(default=12),
    files: list[UploadFile] = File(default_factory=list),
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    message_text = message
    if body is not None:
        message_text = body.message or message_text
        session_id = body.session_id or session_id
        model = body.model or model
        context_limit = body.context_limit or context_limit

    if not message_text or not message_text.strip():
        raise HTTPException(status_code=400, detail="Message is required.")

    attachment_metadata: list[dict[str, Any]] = []
    uploaded_attachments: list[UploadFile] = files or []

    try:
        attachments, normalized = await AttachmentService.process(uploaded_attachments, user.id)
        attachment_metadata = normalized
    except AttachmentValidationError as exc:
        raise HTTPException(
            status_code=400, 
            detail=f"File validation error: {exc.code} - {exc.message}"
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, 
            detail=f"Upload error: {str(exc)}"
        ) from exc

    try:
        result = await ChatMemoryService.ask(
            session=session,
            user=user,
            session_id=session_id,
            message=message_text,
            model=model or "auto",
            context_limit=context_limit,
            attachments=attachment_metadata,
        )
        result["metadata"] = {
            **(result.get("metadata") or {}),
            "attachments": [
                {
                    "id": item.get("id"),
                    "filename": item.get("filename"),
                    "mime_type": item.get("mime_type"),
                    "size": item.get("size"),
                }
                for item in attachment_metadata
            ],
        }
        return {
            "success": True,
            "session_id": result["session_id"],
            "title": result["title"],
            "answer": result["answer"],
            "history": [
                ChatMessageItem(
                    id=item.id,
                    session_id=item.session_id,
                    role=item.role,
                    content=item.content,
                    created_at=item.created_at,
                )
                for item in result["history"]
            ],
            "metadata": result["metadata"],
        }
    finally:
        if attachment_metadata:
            for attachment in attachment_metadata:
                temp_path = attachment.get("temp_path") or attachment.get("path")
                if temp_path:
                    try:
                        import os
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                    except Exception:
                        pass


@router.post("/session/new", response_model=ChatSessionCreateResponse)
async def create_chat_session(
    title: str = "New Chat",
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    chat_session = ChatMemoryService.create_session(session, user, title=title)
    return {
        "success": True,
        "session_id": chat_session.id,
        "title": chat_session.title,
    }


@router.get("/sessions", response_model=ChatSessionListResponse)
async def list_chat_sessions(
    limit: int = 20,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    sessions = ChatMemoryService.list_sessions(session, user, limit=limit)
    return {
        "success": True,
        "items": [
            ChatSessionListItem(
                id=item.id,
                title=item.title,
                last_message_at=item.last_message_at,
                created_at=item.created_at,
            )
            for item in sessions
        ],
    }


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageItem])
async def list_chat_messages(
    session_id: str,
    limit: int = 50,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    messages = ChatMemoryService.list_messages(session, user, session_id, limit=limit)
    return [
        ChatMessageItem(
            id=item.id,
            session_id=item.session_id,
            role=item.role,
            content=item.content,
            created_at=item.created_at,
        )
        for item in messages
    ]
