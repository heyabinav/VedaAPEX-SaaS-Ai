"""
Redis-backed conversation memory layer for VedaApex.

This module provides efficient caching and retrieval of conversation history
using Redis, with graceful fallback to the database.

Key features:
- Store and retrieve chat messages from Redis
- Automatic context window management
- Conversation summarization for long chats
- User isolation (scoped by user_id)
- TTL-based auto-cleanup
- Deduplication support
- Graceful fallback to database
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Optional

from redis.asyncio import Redis

from app.core.config import settings
from app.models.chat_message import ChatMessage
from app.services.redis_client import RedisClient

logger = logging.getLogger("services.redis_chat_memory")


class RedisChatMemory:
    """
    Redis-backed conversation memory manager.
    
    Stores messages per conversation with user isolation.
    Provides efficient context retrieval and automatic summarization.
    """

    # Redis key patterns
    @staticmethod
    def _make_messages_key(user_id: int, conversation_id: str) -> str:
        """Redis key for storing messages: chat:{user_id}:{conversation_id}:messages"""
        return f"chat:{user_id}:{conversation_id}:messages"

    @staticmethod
    def _make_summary_key(user_id: int, conversation_id: str) -> str:
        """Redis key for storing summary: chat:{user_id}:{conversation_id}:summary"""
        return f"chat:{user_id}:{conversation_id}:summary"

    @staticmethod
    def _make_conversation_index_key(user_id: int) -> str:
        """Redis key for indexing user's conversations: chat:{user_id}:conversations"""
        return f"chat:{user_id}:conversations"

    @staticmethod
    def _make_metadata_key(user_id: int, conversation_id: str) -> str:
        """Redis key for conversation metadata: chat:{user_id}:{conversation_id}:metadata"""
        return f"chat:{user_id}:{conversation_id}:metadata"

    # ─── Save Messages ─────────────────────────────────────────────────────────────────────
    @classmethod
    async def save_message(
        cls,
        user_id: int,
        conversation_id: str,
        role: str,
        content: str,
        message_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> bool:
        """
        Save a message to Redis cache.
        
        Args:
            user_id: The authenticated user's ID
            conversation_id: Unique conversation identifier
            role: Message role ('user', 'assistant', 'system')
            content: Message content
            message_id: Optional message ID for tracking
            request_id: Optional request ID for idempotency/deduplication
        
        Returns:
            True if saved successfully, False otherwise
        
        The message is stored as JSON in a Redis list for chronological order.
        TTL is applied to auto-clean old conversations.
        """
        redis = await RedisClient.get()
        if not redis:
            logger.debug("Redis unavailable; skipping message save to cache")
            return False

        try:
            messages_key = cls._make_messages_key(user_id, conversation_id)
            
            # Build message object
            message_obj = {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
                "message_id": message_id,
                "request_id": request_id,
            }
            
            # Check for duplication (idempotency)
            if request_id:
                # Simple check: if last message has same request_id, skip
                existing = await redis.lrange(messages_key, -1, -1)
                if existing:
                    try:
                        last_msg = json.loads(existing[0])
                        if last_msg.get("request_id") == request_id:
                            logger.debug(
                                "Skipping duplicate message (request_id=%s)", request_id
                            )
                            return True
                    except (json.JSONDecodeError, KeyError):
                        pass
            
            # Append message to list (preserves chronological order)
            await redis.rpush(messages_key, json.dumps(message_obj))
            
            # Set TTL on the key
            await redis.expire(messages_key, settings.REDIS_CHAT_TTL)
            
            # Also store in conversation index
            index_key = cls._make_conversation_index_key(user_id)
            await redis.sadd(index_key, conversation_id)
            await redis.expire(index_key, settings.REDIS_CHAT_TTL)
            
            logger.debug(
                "Saved message to Redis: user=%s conversation=%s role=%s",
                user_id, conversation_id, role
            )
            return True

        except Exception as e:
            logger.warning(
                "Failed to save message to Redis cache: %s (will continue without cache)", e
            )
            return False

    # ─── Retrieve Messages ─────────────────────────────────────────────────────────────────
    @classmethod
    async def get_messages(
        cls,
        user_id: int,
        conversation_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Retrieve all cached messages for a conversation.
        
        Args:
            user_id: The authenticated user's ID
            conversation_id: Unique conversation identifier
            limit: Maximum number of messages to return
        
        Returns:
            List of message dicts in chronological order, or empty list if not found
        
        User isolation is enforced at the key level.
        """
        redis = await RedisClient.get()
        if not redis:
            logger.debug("Redis unavailable; returning empty message list")
            return []

        try:
            messages_key = cls._make_messages_key(user_id, conversation_id)
            
            # Get messages from Redis list
            raw_messages = await redis.lrange(messages_key, -limit, -1)
            
            messages = []
            for raw_msg in raw_messages:
                try:
                    msg = json.loads(raw_msg)
                    messages.append(msg)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse cached message JSON")
                    continue
            
            logger.debug(
                "Retrieved %d cached messages: user=%s conversation=%s",
                len(messages), user_id, conversation_id
            )
            return messages

        except Exception as e:
            logger.warning("Failed to retrieve messages from Redis: %s", e)
            return []

    # ─── Get Recent Messages (for AI context) ──────────────────────────────────────────────
    @classmethod
    async def get_recent_messages(
        cls,
        user_id: int,
        conversation_id: str,
        limit: int = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve recent messages for AI context.
        
        This is the key function used before sending context to the AI model.
        Returns recent messages + summary of older messages if available.
        
        Args:
            user_id: The authenticated user's ID
            conversation_id: Unique conversation identifier
            limit: Maximum recent messages (defaults to REDIS_CHAT_CONTEXT_LIMIT)
        
        Returns:
            List of messages suitable for AI model input, in chronological order
        
        Strategy:
        - Get the N most recent messages (where N = limit or REDIS_CHAT_CONTEXT_LIMIT)
        - If a summary exists, prepend it as a system message
        - This keeps token count reasonable while maintaining context
        """
        if limit is None:
            limit = settings.REDIS_CHAT_CONTEXT_LIMIT

        redis = await RedisClient.get()
        if not redis:
            logger.debug("Redis unavailable; returning empty recent messages list")
            return []

        try:
            messages_key = cls._make_messages_key(user_id, conversation_id)
            
            # Get N most recent messages
            raw_messages = await redis.lrange(messages_key, -limit, -1)
            
            messages = []
            for raw_msg in raw_messages:
                try:
                    msg = json.loads(raw_msg)
                    messages.append(msg)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse cached message JSON")
                    continue
            
            # If we have a summary, prepend it for context
            summary = await cls.get_summary(user_id, conversation_id)
            if summary:
                messages.insert(0, {
                    "role": "system",
                    "content": f"[Previous conversation summary]\n{summary['content']}",
                    "timestamp": summary.get("timestamp"),
                })
            
            logger.debug(
                "Retrieved %d recent messages (limit=%d): user=%s conversation=%s",
                len(messages), limit, user_id, conversation_id
            )
            return messages

        except Exception as e:
            logger.warning("Failed to retrieve recent messages from Redis: %s", e)
            return []

    # ─── Save Conversation Summary ──────────────────────────────────────────────────────────
    @classmethod
    async def save_summary(
        cls,
        user_id: int,
        conversation_id: str,
        summary: str,
    ) -> bool:
        """
        Save a conversation summary for long conversations.
        
        Args:
            user_id: The authenticated user's ID
            conversation_id: Unique conversation identifier
            summary: Compact summary of older messages
        
        Returns:
            True if saved successfully, False otherwise
        
        The summary is stored with TTL matching the regular messages.
        Summaries are included when retrieving recent messages to provide
        background context without exceeding token limits.
        """
        redis = await RedisClient.get()
        if not redis:
            logger.debug("Redis unavailable; skipping summary save")
            return False

        try:
            summary_key = cls._make_summary_key(user_id, conversation_id)
            
            summary_obj = {
                "content": summary,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            await redis.set(
                summary_key,
                json.dumps(summary_obj),
                ex=settings.REDIS_CHAT_TTL
            )
            
            logger.debug(
                "Saved conversation summary: user=%s conversation=%s length=%d",
                user_id, conversation_id, len(summary)
            )
            return True

        except Exception as e:
            logger.warning("Failed to save summary to Redis: %s", e)
            return False

    # ─── Retrieve Conversation Summary ─────────────────────────────────────────────────────
    @classmethod
    async def get_summary(
        cls,
        user_id: int,
        conversation_id: str,
    ) -> Optional[dict[str, Any]]:
        """
        Retrieve conversation summary if available.
        
        Returns:
            Summary dict with 'content' and 'timestamp', or None if not found
        """
        redis = await RedisClient.get()
        if not redis:
            return None

        try:
            summary_key = cls._make_summary_key(user_id, conversation_id)
            raw_summary = await redis.get(summary_key)
            
            if raw_summary:
                return json.loads(raw_summary)

        except Exception as e:
            logger.warning("Failed to retrieve summary from Redis: %s", e)

        return None

    # ─── Clear/Delete Conversation ────────────────────────────────────────────────────────
    @classmethod
    async def clear_conversation(
        cls,
        user_id: int,
        conversation_id: str,
    ) -> bool:
        """
        Clear all cached data for a conversation.
        
        Args:
            user_id: The authenticated user's ID
            conversation_id: Unique conversation identifier
        
        Returns:
            True if successful, False otherwise
        
        This removes:
        - All messages
        - Summary
        - Metadata
        
        The conversation is also removed from the user's conversation index.
        """
        redis = await RedisClient.get()
        if not redis:
            logger.debug("Redis unavailable; skipping conversation clear")
            return False

        try:
            messages_key = cls._make_messages_key(user_id, conversation_id)
            summary_key = cls._make_summary_key(user_id, conversation_id)
            metadata_key = cls._make_metadata_key(user_id, conversation_id)
            index_key = cls._make_conversation_index_key(user_id)
            
            # Delete all keys
            await redis.delete(messages_key, summary_key, metadata_key)
            
            # Remove from conversation index
            await redis.srem(index_key, conversation_id)
            
            logger.debug(
                "Cleared conversation from Redis cache: user=%s conversation=%s",
                user_id, conversation_id
            )
            return True

        except Exception as e:
            logger.warning("Failed to clear conversation from Redis: %s", e)
            return False

    # ─── Check if Conversation Exists ──────────────────────────────────────────────────────
    @classmethod
    async def conversation_exists(
        cls,
        user_id: int,
        conversation_id: str,
    ) -> bool:
        """
        Check if a conversation exists in Redis cache.
        
        Args:
            user_id: The authenticated user's ID
            conversation_id: Unique conversation identifier
        
        Returns:
            True if the conversation has cached messages, False otherwise
        """
        redis = await RedisClient.get()
        if not redis:
            return False

        try:
            messages_key = cls._make_messages_key(user_id, conversation_id)
            count = await redis.llen(messages_key)
            return count > 0

        except Exception as e:
            logger.warning("Failed to check conversation existence in Redis: %s", e)
            return False

    # ─── Get User Conversations ──────────────────────────────────────────────────────────
    @classmethod
    async def get_user_conversations(
        cls,
        user_id: int,
    ) -> set[str]:
        """
        Get all conversation IDs for a user.
        
        Useful for listing conversations or cleanup.
        """
        redis = await RedisClient.get()
        if not redis:
            return set()

        try:
            index_key = cls._make_conversation_index_key(user_id)
            conversations = await redis.smembers(index_key)
            return conversations

        except Exception as e:
            logger.warning("Failed to retrieve user conversations from Redis: %s", e)
            return set()

    # ─── Restore from Database ────────────────────────────────────────────────────────────
    @classmethod
    async def restore_from_database(
        cls,
        user_id: int,
        conversation_id: str,
        db_messages: list[ChatMessage],
    ) -> bool:
        """
        Restore conversation messages from database into Redis cache.
        
        This is called when Redis cache miss occurs and we fetch from the database.
        It repopulates the Redis cache for future fast access.
        
        Args:
            user_id: The authenticated user's ID
            conversation_id: Unique conversation identifier
            db_messages: List of ChatMessage objects from the database
        
        Returns:
            True if restoration successful, False otherwise
        """
        redis = await RedisClient.get()
        if not redis:
            logger.debug("Redis unavailable; skipping restoration")
            return False

        try:
            for msg in db_messages:
                await cls.save_message(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    role=msg.role,
                    content=msg.content,
                    message_id=msg.id,
                )
            
            logger.debug(
                "Restored %d messages from database to Redis cache: user=%s conversation=%s",
                len(db_messages), user_id, conversation_id
            )
            return True

        except Exception as e:
            logger.warning("Failed to restore conversation from database to Redis: %s", e)
            return False

    # ─── Health Check ──────────────────────────────────────────────────────────────────────
    @classmethod
    async def health_check(cls) -> dict[str, Any]:
        """
        Health check for Redis chat memory.
        
        Returns status info for monitoring.
        """
        redis = await RedisClient.get()
        if not redis:
            return {"status": "redis_unavailable"}

        try:
            info = await redis.info()
            return {
                "status": "healthy",
                "redis_available": True,
                "memory_used_mb": round(info.get("used_memory", 0) / 1024 / 1024, 2),
                "connected_clients": info.get("connected_clients", 0),
            }
        except Exception as e:
            logger.warning("Health check failed: %s", e)
            return {"status": "error", "error": str(e)}
