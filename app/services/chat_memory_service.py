from __future__ import annotations

from app.utils.time import utcnow

import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.user import User
from app.services.ai_service import AIToolsService
from app.services.hf_storage.chat import HFChatStorageService
from app.services.supabase_service import SupabaseService
import logging

logger = logging.getLogger("services.chat_memory_service")

def _clean_title(value: str) -> str:
    value = " ".join((value or "").split()).strip()
    return (value[:60] or "New Chat").strip()

def _build_context_messages(messages: list[ChatMessage]) -> list[dict[str, str]]:
    return [{"role": msg.role, "content": msg.content} for msg in messages]

def _extract_text(result: Any) -> str:
    if isinstance(result, str):
        return result
    if isinstance(result, list) and result:
        if isinstance(result[0], str):
            return "".join(result)
        if isinstance(result[0], dict):
            return result[0].get("content") or result[0].get("text") or result[0].get("url") or ""
    if isinstance(result, dict):
        if "choices" in result and result["choices"]:
            choice = result["choices"][0]
            if isinstance(choice, dict):
                return choice.get("message", {}).get("content", "")
        return result.get("content") or result.get("text") or result.get("output") or ""
    return str(result)

class ChatMemoryService:
    @staticmethod
    def create_session(session: Session, user: User, title: str | None = None) -> ChatSession:
        chat_session = ChatSession(
            id=f"chat_{uuid.uuid4().hex[:16]}",
            user_id=user.id,
            title=_clean_title(title or "New Chat"),
            created_at=utcnow(),
            updated_at=utcnow(),
            last_message_at=None,
        )
        session.add(chat_session)
        session.commit()
        session.refresh(chat_session)
        return chat_session

    @staticmethod
    def get_session(session: Session, user: User, session_id: str) -> ChatSession:
        chat_session = session.get(ChatSession, session_id)
        if not chat_session or chat_session.user_id != user.id:
            raise HTTPException(status_code=404, detail="Chat session not found")
        return chat_session

    @staticmethod
    def list_sessions(session: Session, user: User, limit: int = 20) -> list[ChatSession]:
        limit = max(1, min(limit, 100))
        rows = session.exec(
            select(ChatSession)
            .where(ChatSession.user_id == user.id)
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
        ).all()
        return list(rows)

    @staticmethod
    def list_messages(session: Session, user: User, session_id: str, limit: int = 50) -> list[ChatMessage]:
        ChatMemoryService.get_session(session, user, session_id)
        limit = max(1, min(limit, 200))
        rows = session.exec(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id, ChatMessage.user_id == user.id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
        ).all()
        return list(rows)

    @staticmethod
    def _generate_session_title(first_user_message: str, answer: str | None = None) -> str:
        source = answer or first_user_message
        if not source:
            return "New Chat"
        text = " ".join(source.split())
        return _clean_title(text[:60])

    @staticmethod
    def add_message(
        session: Session,
        user: User,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        tokens_used: int | None = None,
    ) -> ChatMessage:
        ChatMemoryService.get_session(session, user, session_id)
        msg = ChatMessage(
            id=f"msg_{uuid.uuid4().hex[:16]}",
            session_id=session_id,
            user_id=user.id,
            role=role,
            content=content,
            created_at=utcnow(),
            metadata_json=json.dumps(metadata or {}, ensure_ascii=True, separators=(",", ":")),
            tokens_used=tokens_used,
        )
        session.add(msg)
        session.commit()
        session.refresh(msg)
        chat_session = session.get(ChatSession, session_id)
        if chat_session:
            chat_session.updated_at = utcnow()
            chat_session.last_message_at = utcnow()
            session.add(chat_session)
            session.commit()
        return msg

    @staticmethod
    async def ask(
        session: Session,
        user: User,
        session_id: str | None,
        message: str,
        model: str = "auto",
        context_limit: int = 12,
    ) -> dict[str, Any]:
        if session_id:
            chat_session = ChatMemoryService.get_session(session, user, session_id)
        else:
            chat_session = ChatMemoryService.create_session(session, user, title=message)
            session_id = chat_session.id

        past_messages = ChatMemoryService.list_messages(session, user, session_id, limit=context_limit)
        context_messages = _build_context_messages(past_messages)

        system_prompt = (
            "You are a context-aware assistant. Use the previous chat history to answer the user's current message. "
            "If the latest question is related to earlier messages, resolve it using that context. "
            "If the context is insufficient, ask a concise clarifying question. "
            "Stay direct, factual, and consistent with earlier turns."
        )

        llm_messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        llm_messages.extend(context_messages)
        llm_messages.append({"role": "user", "content": message})

        prompt = message
        if context_messages:
            prompt = (
                "Conversation context:\n"
                + "\n".join(f"{m['role']}: {m['content']}" for m in context_messages)
                + f"\n\nCurrent user message:\n{message}"
            )

        user_profile_facts = await SupabaseService.get_user_profile_facts(str(user.id))

        identity_lines = []
        if user.full_name and user.full_name.strip():
            identity_lines.append(f"Logged in as: {user.full_name.strip()} ({user.email})")
        else:
            identity_lines.append(f"Logged in as: {user.email}")

        if user_profile_facts:
            if user_profile_facts.get("full_name"):
                identity_lines = [
                    f"Logged in as: {user_profile_facts['full_name']} ({user.email})"
                ]
            facts = []
            for key, label in [
                ("hometown", "hometown"),
                ("favorite_color", "favorite_color"),
                ("gf_name", "gf_name"),
                ("extra_notes", "notes"),
            ]:
                value = user_profile_facts.get(key)
                if value:
                    facts.append(f"{label}={value}")
            if facts:
                identity_lines.append(
                    "Known facts about the user: " + ", ".join(facts)
                )

        identity_lines.append(
            "Instruction: Sirf inhi diye gaye facts ka use karo. Koi bhi fact jo yahan nahi diya gaya hai, use mat banao ya guess mat karo."
        )
        system_prompt = system_prompt + "\n\n" + "\n".join(identity_lines)

        answer = await AIToolsService.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            tier=1,
            provider=model or "auto",
        )
        answer_text = _extract_text(answer).strip() or "I could not generate a response."

        first_user_message = next((msg.content for msg in past_messages if msg.role == "user"), message)
        if chat_session.title == "New Chat":
            chat_session.title = ChatMemoryService._generate_session_title(first_user_message, answer_text)
            chat_session.updated_at = utcnow()
            session.add(chat_session)
            session.commit()

        user_msg = ChatMemoryService.add_message(session, user, session_id, "user", message)
        assistant_msg = ChatMemoryService.add_message(
            session,
            user,
            session_id,
            "assistant",
            answer_text,
            metadata={"model": model, "context_limit": context_limit},
        )

        history = ChatMemoryService.list_messages(session, user, session_id, limit=context_limit + 2)
        
        # Synchronize to Hugging Face Dataset Storage
        try:
            formatted_messages = [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at.isoformat() if hasattr(m.created_at, "isoformat") else str(m.created_at),
                }
                for m in history
            ]
            HFChatStorageService.sync_session(
                user_id=user.id,
                session_id=session_id,
                title=chat_session.title,
                messages=formatted_messages,
            )
        except Exception as exc:
            logger.warning("Failed to sync chat session %s to HF storage: %s", session_id, exc)

        return {
            "session_id": session_id,
            "title": chat_session.title,
            "answer": answer_text,
            "history": history,
            "metadata": {
                "model": model,
                "context_limit": context_limit,
                "message_id": user_msg.id,
                "answer_id": assistant_msg.id,
            },
        }
