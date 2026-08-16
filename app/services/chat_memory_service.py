from __future__ import annotations

from app.utils.time import utcnow

import asyncio
import json
import re
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.user import User
from app.services.ai_service import AIToolsService
from app.services.hf_storage.chat import HFChatStorageService
from app.services.supabase_service import SupabaseService
from app.services.redis_chat_memory import RedisChatMemory
from app.services.search_router import SearchRouter
from app.services.search_decision_engine import SearchDecisionEngine
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


def _as_message_text(message: Any) -> str:
    if isinstance(message, ChatMessage):
        return message.content or ""
    if isinstance(message, dict):
        return str(message.get("content") or "")
    return str(message or "")


class ChatMemoryService:
    @staticmethod
    def extract_user_facts(messages: list[Any]) -> dict[str, Any]:
        """Extract reusable user facts from earlier chat history, especially school-score facts."""
        score_facts: dict[str, int] = {}

        def add_fact(grade_key: str, percent: int) -> None:
            if not grade_key or not (0 <= percent <= 100):
                return
            score_facts[grade_key] = percent
            digits = re.sub(r"\D+", "", grade_key)
            if digits:
                score_facts[digits] = percent

        for message in messages or []:
            if isinstance(message, dict):
                role = str(message.get("role") or "").lower()
                content = str(message.get("content") or "")
            else:
                role = str(getattr(message, "role", "")).lower()
                content = str(getattr(message, "content", "") or "")

            if role != "user" or not content:
                continue

            text = " ".join(content.split())
            lowered = text.lower()
            patterns = [
                r"(?P<grade>\d{1,2})(?:st|nd|rd|th)?\s*(?:me|mai|in|main|class|cls)?\s*(?P<percent>\d{1,3})\s*(?:%|percent(?:age)?)",
                r"(?P<grade>\d{1,2})(?:st|nd|rd|th)?\s*(?:class|cls)?\s*(?:mein|me|in|mai)?\s*(?:.*?)(?P<percent>\d{1,3})\s*(?:%|percent(?:age)?)",
                r"(?P<percent>\d{1,3})\s*(?:%|percent(?:age)?)\s*(?:.*?)(?:me|mai|in|class|cls)?\s*(?P<grade>\d{1,2})(?:st|nd|rd|th)?",
            ]

            for pattern in patterns:
                for match in re.finditer(pattern, lowered):
                    grade = (match.group("grade") or "").strip()
                    percent = match.group("percent")
                    if not grade or not percent:
                        continue
                    try:
                        grade_number = int(grade)
                        percent_number = int(percent)
                    except ValueError:
                        continue
                    if grade_number > 100:
                        continue
                    grade_label = f"{grade_number}th" if grade_number <= 12 else str(grade_number)
                    add_fact(grade_label, percent_number)
                    add_fact(str(grade_number), percent_number)

            # Handles direct sentences like "10th me 90 percent aaya tha" with extra words between grade and percent.
            for key in (r"(?P<grade>\d{1,2})th\s*(?:me|mai|in|main|class|cls)?\s*(?:.*?)(?P<percent>\d{1,3})\s*(?:%|percent(?:age)?)",
                         r"(?P<grade>\d{1,2})\s*(?:me|mai|in|main|class|cls)?\s*(?:.*?)(?P<percent>\d{1,3})\s*(?:%|percent(?:age)?)"):
                for match in re.finditer(key, lowered):
                    grade = match.group("grade")
                    percent = match.group("percent")
                    try:
                        percent_number = int(percent)
                    except ValueError:
                        continue
                    if 0 <= percent_number <= 100:
                        add_fact(f"{grade}th", percent_number)
                        add_fact(grade, percent_number)

        return {"score_facts": score_facts}

    @staticmethod
    async def save_memory_facts_to_supabase(user: User, facts: dict[str, Any]) -> None:
        """Persist remembered facts in Supabase JSON for later session reuse."""
        try:
            from app.services.supabase_service import SupabaseService

            if not SupabaseService.is_configured():
                return

            await SupabaseService.save_user_details(
                str(user.id),
                "chat_memory_json",
                facts,
            )
        except Exception as exc:
            logger.warning("Failed to persist chat memory JSON for user_id=%s: %s", getattr(user, "id", None), exc)

    @staticmethod
    async def load_memory_facts_from_supabase(user: User) -> dict[str, Any]:
        try:
            from app.services.supabase_service import SupabaseService

            if not SupabaseService.is_configured():
                return {}

            saved = await SupabaseService.get_user_details(str(user.id))
            payload = saved.get("chat_memory_json") if isinstance(saved, dict) else None
            if isinstance(payload, str):
                try:
                    return json.loads(payload)
                except json.JSONDecodeError:
                    return {}
            if isinstance(payload, dict):
                return payload
            return {}
        except Exception as exc:
            logger.warning("Failed to load chat memory JSON for user_id=%s: %s", getattr(user, "id", None), exc)
            return {}

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
        """
        List messages for a conversation.
        
        Strategy:
        1. Try to get messages from Redis cache (fast)
        2. If cache miss, fetch from database and restore to Redis
        3. Return messages in chronological order
        
        Args:
            session: SQLModel database session
            user: Authenticated user
            session_id: Chat session ID
            limit: Maximum messages to return
        
        Returns:
            List of ChatMessage objects
        
        This function is synchronous but tries to handle async Redis gracefully.
        For fully async context retrieval before AI calls, use get_context_for_ai() instead.
        """
        ChatMemoryService.get_session(session, user, session_id)
        limit = max(1, min(limit, 200))
        
        rows = session.exec(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id, ChatMessage.user_id == user.id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
        ).all()
        
        result = list(rows)
        
        # Try to restore to Redis cache for next retrieval
        # (This is async but we don't wait for it)
        try:
            asyncio.create_task(
                RedisChatMemory.restore_from_database(
                    user_id=user.id,
                    conversation_id=session_id,
                    db_messages=result,
                )
            )
        except Exception as e:
            logger.warning("Failed to queue Redis restoration: %s", e)
        
        return result

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
        request_id: Optional[str] = None,
    ) -> ChatMessage:
        """
        Add a message to both database (permanent storage) and Redis cache.
        
        Args:
            session: SQLModel database session
            user: Authenticated user
            session_id: Chat session ID
            role: Message role ('user', 'assistant', 'system')
            content: Message content
            metadata: Optional metadata dict
            tokens_used: Optional token count
            request_id: Optional request ID for idempotency
        
        Returns:
            ChatMessage object from database
        
        The message is saved to:
        1. Database (permanent source of truth)
        2. Redis cache (fast retrieval for same session)
        
        If Redis is unavailable, the message is still saved to the database.
        """
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
        
        # Also save to Redis cache for faster retrieval
        # This runs asynchronously and doesn't block the response
        try:
            asyncio.create_task(
                RedisChatMemory.save_message(
                    user_id=user.id,
                    conversation_id=session_id,
                    role=role,
                    content=content,
                    message_id=msg.id,
                    request_id=request_id,
                )
            )
        except Exception as e:
            logger.warning("Failed to queue Redis message save: %s", e)
        
        return msg

    @staticmethod
    async def ask(
        session: Session,
        user: User,
        session_id: str | None,
        message: str,
        model: str = "auto",
        context_limit: int = 12,
        attachments: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if session_id:
            chat_session = ChatMemoryService.get_session(session, user, session_id)
        else:
            chat_session = ChatMemoryService.create_session(session, user)
            session_id = chat_session.id

        past_messages = ChatMemoryService.list_messages(session, user, session_id, limit=context_limit)
        context_messages = _build_context_messages(past_messages)
        extracted_facts = ChatMemoryService.extract_user_facts(past_messages)
        saved_memory = await ChatMemoryService.load_memory_facts_from_supabase(user)
        merged_facts = extracted_facts
        if saved_memory:
            score_facts = {**saved_memory.get("score_facts", {}), **extracted_facts.get("score_facts", {})}
            merged_facts = {"score_facts": score_facts}

        system_prompt = (
            "You are a context-aware assistant. Use the previous chat history to answer the user's current message. "
            "If the latest question is related to earlier messages, resolve it using that context. "
            "If the context is insufficient, ask a concise clarifying question. "
            "Stay direct, factual, and consistent with earlier turns."
        )

        if merged_facts.get("score_facts"):
            fact_lines = [
                f"- {grade}: {percent}%"
                for grade, percent in sorted(merged_facts["score_facts"].items(), key=lambda item: str(item[0]))
            ]
            system_prompt += "\n\nRemembered user score facts from earlier chat:\n" + "\n".join(fact_lines)

        await ChatMemoryService.save_memory_facts_to_supabase(user, merged_facts)

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
            system_prompt = (
                system_prompt
                + "\n\nAnalyze the user’s latest request in the context of previous conversation and answer accordingly. "
                + "If the user asks about their name or account, use the logged-in identity."
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

        # ───────────────────────────────────────────────────────────────
        # INTELLIGENT WEB SEARCH INTEGRATION
        # ───────────────────────────────────────────────────────────────
        search_results = None
        search_metadata = {}
        
        try:
            # Check if web search is needed
            should_search = SearchDecisionEngine.should_search(message)
            search_reason = SearchDecisionEngine.get_search_reason(message)
            request_type = SearchDecisionEngine.classify_request(message)
            
            logger.debug(
                "Chat ask - Search decision: should_search=%s type=%s reason=%s",
                should_search,
                request_type,
                search_reason,
            )
            
            if should_search:
                logger.info("Performing web search for chat message: %s", message[:80])
                
                # Perform web search
                search_results = await SearchRouter.search_with_decision(
                    query=message,
                    num_results=8,
                )
                
                if search_results and search_results.get("results"):
                    logger.info(
                        "Web search found %d results (provider=%s)",
                        search_results.get("result_count", 0),
                        search_results.get("provider", "unknown"),
                    )
                    
                    # Build search context for system prompt
                    search_context = ChatMemoryService._build_search_context(search_results)
                    
                    # Add search context to system prompt
                    system_prompt += "\n\n" + search_context
                    
                    # Store search metadata
                    search_metadata = {
                        "web_search_performed": True,
                        "search_provider": search_results.get("provider"),
                        "search_result_count": search_results.get("result_count", 0),
                        "search_reason": search_reason,
                        "request_type": request_type,
                    }
                    
                    logger.debug("Web search context added to system prompt")
                else:
                    logger.warning("Web search did not return results for: %s", message[:80])
                    search_metadata = {
                        "web_search_attempted": True,
                        "search_result_count": 0,
                        "search_reason": search_reason,
                    }
            else:
                logger.debug("Web search not needed: %s", search_reason)
                search_metadata = {
                    "web_search_needed": False,
                    "search_reason": search_reason,
                    "request_type": request_type,
                }
        
        except Exception as e:
            logger.warning("Web search integration error (continuing without search): %s", str(e))
            search_metadata = {"search_error": str(e)[:100]}

        if attachments:
            image_attachments = [
                {
                    "mime_type": item.get("mime_type"),
                    "data": item.get("data"),
                    "filename": item.get("filename"),
                }
                for item in attachments
                if item.get("mime_type", "").startswith("image/")
            ]
            if image_attachments:
                model_name = (model or "auto").lower()
                supports_vision = (
                    "gpt-4o" in model_name or "gemini" in model_name or "vision" in model_name or "qwen" in model_name or "claude" in model_name
                )
                if not supports_vision:
                    raise HTTPException(status_code=400, detail={
                        "success": False,
                        "error": {
                            "code": "MODEL_DOES_NOT_SUPPORT_VISION",
                            "message": "The selected model does not support image analysis."
                        }
                    })
                system_prompt = system_prompt + "\n\nThe user attached image(s). Analyze the attached image content along with the message."

        answer = await AIToolsService.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            tier=1,
            provider=model or "auto",
        )
        answer_text = _extract_text(answer).strip() or "I could not generate a response."

        # Keep the latest extracted score facts in sync for future questions.
        latest_facts = ChatMemoryService.extract_user_facts(past_messages + [{"role": "user", "content": message}, {"role": "assistant", "content": answer_text}])
        await ChatMemoryService.save_memory_facts_to_supabase(user, latest_facts)

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
            metadata={
                "model": model,
                "context_limit": context_limit,
                **search_metadata,  # Include search metadata in message
            },
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
                "attachments": [
                    {
                        "id": item.get("id"),
                        "filename": item.get("filename"),
                        "mime_type": item.get("mime_type"),
                        "size": item.get("size"),
                    }
                    for item in (attachments or [])
                ],
            },
        }

    # ─── Async Context Retrieval for AI ────────────────────────────────────────────────────
    @staticmethod
    async def get_context_for_ai(
        session: Session,
        user: User,
        session_id: str,
        context_limit: int = 50,
    ) -> list[dict[str, str]]:
        """
        Get conversation context optimized for AI model input.
        
        This async method retrieves messages with the following strategy:
        1. Try Redis cache first (fast)
        2. If cache miss, fetch from database and restore to Redis
        3. Include conversation summary if available (for long chats)
        4. Return messages in chronological order suitable for LLM input
        
        Args:
            session: SQLModel database session
            user: Authenticated user
            session_id: Chat session ID
            context_limit: Maximum recent messages to include
        
        Returns:
            List of dicts with 'role' and 'content' keys, ready for AI model
        
        This is the primary method to use before calling the AI model.
        It provides context window management automatically.
        """
        ChatMemoryService.get_session(session, user, session_id)
        
        # Try Redis first
        redis_messages = await RedisChatMemory.get_recent_messages(
            user_id=user.id,
            conversation_id=session_id,
            limit=context_limit,
        )
        
        if redis_messages:
            logger.debug(
                "Using Redis cached context: %d messages", len(redis_messages)
            )
            return redis_messages
        
        # Redis miss - fetch from database
        logger.debug(
            "Redis cache miss; fetching from database: user=%s session=%s",
            user.id, session_id
        )
        db_messages = ChatMemoryService.list_messages(
            session, user, session_id, limit=context_limit
        )
        
        # Convert to context format
        context = _build_context_messages(db_messages)
        
        # Try to restore to Redis for next time
        await RedisChatMemory.restore_from_database(
            user_id=user.id,
            conversation_id=session_id,
            db_messages=db_messages,
        )
        
        return context

    # ─── Build Search Context for System Prompt ────────────────────────────────────────────
    @staticmethod
    def _build_search_context(search_results: dict) -> str:
        """
        Build formatted search context from web search results.
        
        Converts search results into a clear, concise system prompt section
        that the AI can use when generating its response.
        
        Args:
            search_results: Dict from SearchRouter.search()
            
        Returns:
            Formatted search context string
        """
        if not search_results or not search_results.get("results"):
            return ""
        
        results = search_results.get("results", [])
        provider = search_results.get("provider", "unknown")
        
        # Limit to top 5 results for token efficiency
        top_results = results[:5]
        
        context_lines = [
            "─" * 70,
            f"WEB SEARCH RESULTS (from {provider}):",
            "─" * 70,
        ]
        
        for idx, result in enumerate(top_results, 1):
            title = result.get("title", "")
            url = result.get("url", "")
            snippet = result.get("snippet", "")
            
            context_lines.append(f"\n[{idx}] {title}")
            if url:
                context_lines.append(f"    Source: {url}")
            if snippet:
                # Truncate long snippets
                snippet_text = snippet[:300]
                if len(snippet) > 300:
                    snippet_text += "..."
                context_lines.append(f"    {snippet_text}")
        
        context_lines.append(f"\n{'─' * 70}")
        context_lines.append(
            "Use the above web search results to inform your answer. "
            "Cite sources when referencing information from the search results."
        )
        context_lines.append("─" * 70)
        
        return "\n".join(context_lines)

    # ─── Clear Conversation Cache ─────────────────────────────────────────────────────────
    @staticmethod
    async def clear_conversation_cache(
        user: User,
        session_id: str,
    ) -> bool:
        """
        Clear Redis cache for a conversation.
        
        This is useful when explicitly deleting a conversation or syncing state.
        The database record is not affected.
        
        Args:
            user: Authenticated user
            session_id: Chat session ID
        
        Returns:
            True if successful, False otherwise
        """
        try:
            cleared = await RedisChatMemory.clear_conversation(
                user_id=user.id,
                conversation_id=session_id,
            )
            if cleared:
                logger.debug(
                    "Cleared conversation cache: user=%s session=%s",
                    user.id, session_id
                )
            return cleared
        except Exception as e:
            logger.warning("Failed to clear conversation cache: %s", e)
            return False

    # ─── Save Conversation Summary (for long chats) ────────────────────────────────────────
    @staticmethod
    async def save_conversation_summary(
        user: User,
        session_id: str,
        summary: str,
    ) -> bool:
        """
        Save a summary of the conversation to Redis.
        
        This is used for long conversations to maintain context without exceeding
        token limits. The summary is included automatically in future context retrievals.
        
        Args:
            user: Authenticated user
            session_id: Chat session ID
            summary: Compact summary text of older messages
        
        Returns:
            True if successful, False otherwise
        
        Example:
            When conversation exceeds token threshold, the service can summarize
            old messages and store the summary. Future AI calls will include this
            summary in the system message for context.
        """
        try:
            saved = await RedisChatMemory.save_summary(
                user_id=user.id,
                conversation_id=session_id,
                summary=summary,
            )
            if saved:
                logger.debug(
                    "Saved conversation summary: user=%s session=%s len=%d",
                    user.id, session_id, len(summary)
                )
            return saved
        except Exception as e:
            logger.warning("Failed to save conversation summary: %s", e)
            return False

