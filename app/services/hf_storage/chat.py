"""Hugging Face Dataset Storage Service for Persistent Chat History.

Manages persistent user chat history stored as JSON files at:
  chats/{user_id}.json
in the Hugging Face Dataset repository:
  vedaapex/chat-storage

Features:
- Uses official huggingface_hub integration (HfApi, upload_file, hf_hub_download, delete_file)
- Multi-tenant security & path traversal protection
- User-specific TTL caching & cache invalidation on write
- Exponential backoff retries for transient HF network errors
- Automatic synchronization with ChatMemoryService
"""

from __future__ import annotations

import io
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.utils import EntryNotFoundError, HFValidationError, RepositoryNotFoundError

from app.core.config import settings
from app.core.exceptions import (
    HFAuthenticationFailed,
    HFDeleteFailed,
    HFDownloadFailed,
    HFPermissionDenied,
    HFStorageUnavailable,
    HFUploadFailed,
    InvalidUserId,
)
from app.utils.time import utcnow

logger = logging.getLogger("services.hf_storage.chat")

# Local in-memory cache: user_id -> (data_dict, expire_timestamp)
_CHAT_CACHE: Dict[str, Tuple[Dict[str, Any], float]] = {}


def _get_cache(user_id: str) -> Optional[Dict[str, Any]]:
    cached = _CHAT_CACHE.get(str(user_id))
    if not cached:
        return None
    data, expires_at = cached
    if time.time() > expires_at:
        _CHAT_CACHE.pop(str(user_id), None)
        return None
    return data


def _set_cache(user_id: str, data: Dict[str, Any]) -> None:
    ttl = int(getattr(settings, "HF_STORAGE_CACHE_TTL_SECONDS", 60))
    _CHAT_CACHE[str(user_id)] = (data, time.time() + ttl)


def _invalidate_cache(user_id: str) -> None:
    _CHAT_CACHE.pop(str(user_id), None)


def _sanitize_user_id(user_id: Any) -> str:
    """Sanitize user_id to prevent path traversal attacks."""
    if user_id is None:
        raise InvalidUserId("user_id cannot be None")

    uid_str = str(user_id).strip()
    if not uid_str or uid_str in ("..", ".", "/", "\\"):
        raise InvalidUserId(f"Invalid user_id format: '{user_id}'")

    if re.search(r"[\/\:\*\?\"\<\>\|\\\.\.]", uid_str):
        raise InvalidUserId("user_id contains invalid or unsafe characters")

    return uid_str


def _get_chat_storage_path(user_id: Any) -> str:
    safe_uid = _sanitize_user_id(user_id)
    return f"chats/{safe_uid}.json"


class HFChatStorageService:
    """Service for managing persistent user chat history on Hugging Face Dataset repository."""

    @staticmethod
    def _get_hf_token() -> str:
        token = getattr(settings, "HF_TOKEN", None) or os.environ.get("HF_TOKEN")
        if not token:
            logger.warning("HF_TOKEN is not set in backend settings or environment")
        return token or ""

    @staticmethod
    def _get_hf_api() -> HfApi:
        token = HFChatStorageService._get_hf_token()
        return HfApi(token=token if token else None)

    @staticmethod
    def _get_repo_id() -> str:
        return getattr(settings, "HF_STORAGE_REPO_ID", "vedaapex/chat-storage")

    @staticmethod
    def load_chats(user_id: Any) -> Dict[str, Any]:
        """Load all chat sessions and messages for a user from HF Dataset storage."""
        safe_uid = _sanitize_user_id(user_id)

        cached = _get_cache(safe_uid)
        if cached is not None:
            return cached

        repo_id = HFChatStorageService._get_repo_id()
        path_in_repo = _get_chat_storage_path(safe_uid)
        token = HFChatStorageService._get_hf_token()

        try:
            downloaded_path = hf_hub_download(
                repo_id=repo_id,
                filename=path_in_repo,
                repo_type="dataset",
                token=token if token else None,
            )
            with open(downloaded_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                data = {"user_id": safe_uid, "sessions": [], "updated_at": utcnow().isoformat()}

            _set_cache(safe_uid, data)
            return data

        except (EntryNotFoundError, FileNotFoundError):
            empty_data = {"user_id": safe_uid, "sessions": [], "updated_at": utcnow().isoformat()}
            _set_cache(safe_uid, empty_data)
            return empty_data

        except RepositoryNotFoundError as exc:
            logger.error("HF Repository not found: %s", repo_id)
            raise HFStorageUnavailable(f"Dataset repository '{repo_id}' not found") from exc

        except Exception as exc:
            err_str = str(exc).lower()
            if "401" in err_str or "invalid token" in err_str or "unauthorized" in err_str:
                raise HFAuthenticationFailed("Invalid Hugging Face API token") from exc
            if "403" in err_str or "forbidden" in err_str:
                raise HFPermissionDenied("Permission denied accessing Hugging Face repository") from exc

            logger.error("Failed to download chats file for user %s: %s", safe_uid, exc)
            empty_data = {"user_id": safe_uid, "sessions": [], "updated_at": utcnow().isoformat()}
            _set_cache(safe_uid, empty_data)
            return empty_data

    @staticmethod
    def save_chats(user_id: Any, chat_data: Dict[str, Any]) -> None:
        """Save all chat sessions for a user to HF Dataset storage."""
        safe_uid = _sanitize_user_id(user_id)
        repo_id = HFChatStorageService._get_repo_id()
        path_in_repo = _get_chat_storage_path(safe_uid)
        token = HFChatStorageService._get_hf_token()

        chat_data["user_id"] = safe_uid
        chat_data["updated_at"] = utcnow().isoformat()

        json_bytes = json.dumps(chat_data, indent=2, ensure_ascii=False).encode("utf-8")
        file_obj = io.BytesIO(json_bytes)

        api = HFChatStorageService._get_hf_api()

        max_retries = int(getattr(settings, "HF_STORAGE_MAX_RETRIES", 3))
        backoff = 1.0

        for attempt in range(1, max_retries + 1):
            try:
                file_obj.seek(0)
                api.upload_file(
                    path_or_fileobj=file_obj,
                    path_in_repo=path_in_repo,
                    repo_id=repo_id,
                    repo_type="dataset",
                    commit_message=f"Update chat history for user_{safe_uid}",
                )
                _set_cache(safe_uid, chat_data)
                return
            except Exception as exc:
                err_str = str(exc).lower()
                if "401" in err_str or "unauthorized" in err_str:
                    raise HFAuthenticationFailed("Hugging Face token invalid or expired") from exc
                if "403" in err_str or "forbidden" in err_str:
                    raise HFPermissionDenied("Permission denied uploading chat file") from exc

                logger.warning(
                    "HF upload attempt %d/%d failed for user %s: %s",
                    attempt,
                    max_retries,
                    safe_uid,
                    exc,
                )
                if attempt == max_retries:
                    raise HFUploadFailed(f"Failed to save chats to HF storage after {max_retries} attempts: {exc}") from exc
                time.sleep(backoff)
                backoff *= 2.0

    @staticmethod
    def sync_session(
        user_id: Any,
        session_id: str,
        title: str,
        messages: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Add or update a chat session with its messages in HF Dataset storage."""
        safe_uid = _sanitize_user_id(user_id)
        data = HFChatStorageService.load_chats(safe_uid)

        sessions = data.get("sessions", [])

        existing_session = None
        for s in sessions:
            if s.get("id") == session_id:
                existing_session = s
                break

        now_str = utcnow().isoformat()

        if existing_session:
            existing_session["title"] = title
            existing_session["messages"] = messages
            existing_session["updated_at"] = now_str
        else:
            sessions.append({
                "id": session_id,
                "title": title,
                "created_at": now_str,
                "updated_at": now_str,
                "messages": messages,
            })

        data["sessions"] = sessions
        HFChatStorageService.save_chats(safe_uid, data)
        return data

    @staticmethod
    def delete_session(user_id: Any, session_id: str) -> bool:
        """Delete a single chat session for a user from HF storage."""
        safe_uid = _sanitize_user_id(user_id)
        data = HFChatStorageService.load_chats(safe_uid)

        sessions = data.get("sessions", [])
        initial_count = len(sessions)

        filtered = [s for s in sessions if s.get("id") != session_id]

        if len(filtered) == initial_count:
            return False

        data["sessions"] = filtered
        HFChatStorageService.save_chats(safe_uid, data)
        return True

    @staticmethod
    def delete_all_chats(user_id: Any) -> bool:
        """Delete user's chats file completely from HF Dataset repository."""
        safe_uid = _sanitize_user_id(user_id)
        repo_id = HFChatStorageService._get_repo_id()
        path_in_repo = _get_chat_storage_path(safe_uid)

        _invalidate_cache(safe_uid)
        api = HFChatStorageService._get_hf_api()

        try:
            api.delete_file(
                path_in_repo=path_in_repo,
                repo_id=repo_id,
                repo_type="dataset",
                commit_message=f"Delete chat history for user_{safe_uid}",
            )
            return True
        except EntryNotFoundError:
            return True
        except Exception as exc:
            logger.error("Failed to delete chats file for user %s from HF: %s", safe_uid, exc)
            raise HFDeleteFailed(f"Failed to delete chats file: {exc}") from exc
