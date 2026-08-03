from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
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
from app.services.chat_memory_service import ChatMemoryService

router = APIRouter(prefix="/chat", tags=["Chat Memory"])


@router.post("/ask", response_model=ChatAnswerResponse)
async def ask_chat(
    body: ChatMessageCreate,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    result = await ChatMemoryService.ask(
        session=session,
        user=user,
        session_id=body.session_id,
        message=body.message,
        model=body.model or "auto",
        context_limit=body.context_limit,
    )
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
