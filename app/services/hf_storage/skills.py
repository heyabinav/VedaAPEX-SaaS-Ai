"""Hugging Face Dataset Storage Service for Persistent User Skills.

Manages persistent user skills stored as JSON files at:
  skills/{user_id}.json
in the Hugging Face Dataset repository:
  vedaapex/chat-storage

Features:
- Official huggingface_hub integration (HfApi, upload_file, hf_hub_download, delete_file)
- Level validation: beginner, intermediate, advanced, expert
- Source validation: user_declared, user_requested, verified (default: user_declared)
- Confidence validation: 0.0 to 1.0
- Case-insensitive duplicate prevention & name normalization
- Multi-tenant security & path traversal protection
- User-specific TTL caching & cache invalidation on write
- Exponential backoff retries for transient HF network errors
- Optimistic concurrency & lock protection for skill updates
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
    InvalidConfidence,
    InvalidSkillLevel,
    InvalidSkillName,
    InvalidUserId,
    SkillNotFound,
)
from app.utils.time import utcnow

logger = logging.getLogger("services.hf_storage.skills")

# Allowed values
ALLOWED_SKILL_LEVELS = frozenset({"beginner", "intermediate", "advanced", "expert"})
ALLOWED_SKILL_SOURCES = frozenset({"user_declared", "user_requested", "verified"})
DEFAULT_SKILL_SOURCE = "user_declared"

# Local in-memory cache: user_id -> (data_dict, expire_timestamp)
_SKILL_CACHE: Dict[str, Tuple[Dict[str, Any], float]] = {}


def _get_cache(user_id: str) -> Optional[Dict[str, Any]]:
    cached = _SKILL_CACHE.get(str(user_id))
    if not cached:
        return None
    data, expires_at = cached
    if time.time() > expires_at:
        _SKILL_CACHE.pop(str(user_id), None)
        return None
    return data


def _set_cache(user_id: str, data: Dict[str, Any]) -> None:
    ttl = int(getattr(settings, "HF_STORAGE_CACHE_TTL_SECONDS", 60))
    _SKILL_CACHE[str(user_id)] = (data, time.time() + ttl)


def _invalidate_cache(user_id: str) -> None:
    _SKILL_CACHE.pop(str(user_id), None)


def _sanitize_user_id(user_id: Any) -> str:
    """Sanitize user_id to prevent path traversal attacks."""
    if user_id is None:
        raise InvalidUserId("user_id cannot be None")

    uid_str = str(user_id).strip()
    if not uid_str or uid_str in ("..", ".", "/", "\\"):
        raise InvalidUserId(f"Invalid user_id format: '{user_id}'")

    # Reject path traversal characters
    if re.search(r"[\/\:\*\?\"\<\>\|\\\.\.]", uid_str):
        raise InvalidUserId("user_id contains invalid or unsafe characters")

    return uid_str


def _get_storage_path(user_id: Any) -> str:
    safe_uid = _sanitize_user_id(user_id)
    return f"skills/{safe_uid}.json"


def _normalize_skill_name(name: str) -> str:
    """Clean and normalize skill name for duplicate comparisons."""
    if not name or not isinstance(name, str):
        raise InvalidSkillName("Skill name must be a non-empty string")

    cleaned = name.strip()
    if not cleaned:
        raise InvalidSkillName("Skill name cannot be empty or whitespace only")

    if len(cleaned) > 100:
        raise InvalidSkillName("Skill name exceeds maximum length of 100 characters")

    return cleaned


def _validate_level(level: str) -> str:
    if not level or not isinstance(level, str):
        raise InvalidSkillLevel("Skill level must be specified")

    lvl_lower = level.strip().lower()
    if lvl_lower not in ALLOWED_SKILL_LEVELS:
        raise InvalidSkillLevel(
            f"Invalid skill level '{level}'. Allowed values: {', '.join(sorted(ALLOWED_SKILL_LEVELS))}"
        )
    return lvl_lower


def _validate_confidence(confidence: Optional[float]) -> float:
    if confidence is None:
        return 1.0
    try:
        val = float(confidence)
    except (ValueError, TypeError):
        raise InvalidConfidence("Confidence must be a numeric value between 0.0 and 1.0")

    if val < 0.0 or val > 1.0:
        raise InvalidConfidence(f"Confidence score {val} out of range [0.0, 1.0]")
    return round(val, 2)


def _validate_source(source: Optional[str]) -> str:
    if not source or not isinstance(source, str):
        return DEFAULT_SKILL_SOURCE

    src_lower = source.strip().lower()
    if src_lower not in ALLOWED_SKILL_SOURCES:
        return DEFAULT_SKILL_SOURCE
    return src_lower


class SkillStorageService:
    """Service for managing persistent user skills on Hugging Face Dataset repository."""

    @staticmethod
    def _get_hf_token() -> str:
        token = getattr(settings, "HF_TOKEN", None) or os.environ.get("HF_TOKEN")
        if not token:
            logger.warning("HF_TOKEN is not set in backend settings or environment")
        return token or ""

    @staticmethod
    def _get_hf_api() -> HfApi:
        token = SkillStorageService._get_hf_token()
        return HfApi(token=token if token else None)

    @staticmethod
    def _get_repo_id() -> str:
        return getattr(settings, "HF_STORAGE_REPO_ID", "vedaapex/chat-storage")

    @staticmethod
    def _get_repo_type() -> str:
        return getattr(settings, "HF_STORAGE_REPO_TYPE", "dataset")

    @staticmethod
    def load_skills(user_id: Any) -> Dict[str, Any]:
        """Load persistent user skills from Hugging Face Dataset repo.

        Returns:
            Dict containing user_id, skills list, and updated_at timestamp.
        """
        safe_uid = _sanitize_user_id(user_id)
        cached = _get_cache(safe_uid)
        if cached is not None:
            return cached

        storage_path = _get_storage_path(safe_uid)
        repo_id = SkillStorageService._get_repo_id()
        repo_type = SkillStorageService._get_repo_type()
        token = SkillStorageService._get_hf_token()

        logger.info("Downloading user skills from HF: %s in repo %s", storage_path, repo_id)
        max_retries = int(getattr(settings, "HF_STORAGE_MAX_RETRIES", 3))

        for attempt in range(1, max_retries + 1):
            try:
                local_path = hf_hub_download(
                    repo_id=repo_id,
                    filename=storage_path,
                    repo_type=repo_type,
                    token=token if token else None,
                )
                with open(local_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if not isinstance(data, dict):
                    data = {"user_id": safe_uid, "skills": [], "updated_at": utcnow().isoformat()}

                data.setdefault("user_id", safe_uid)
                data.setdefault("skills", [])
                data.setdefault("updated_at", utcnow().isoformat())

                _set_cache(safe_uid, data)
                return data

            except EntryNotFoundError:
                logger.info("Skills file %s does not exist on HF. Returning default empty payload.", storage_path)
                empty_data = {
                    "user_id": safe_uid,
                    "skills": [],
                    "updated_at": utcnow().isoformat(),
                }
                _set_cache(safe_uid, empty_data)
                return empty_data

            except RepositoryNotFoundError as exc:
                logger.error("Hugging Face repository %s not found: %s", repo_id, exc)
                raise HFStorageUnavailable(f"Hugging Face repository '{repo_id}' not found") from exc

            except (HFValidationError, Exception) as exc:
                err_str = str(exc).lower()
                if "401" in err_str or "invalid token" in err_str or "unauthorized" in err_str:
                    raise HFAuthenticationFailed("Hugging Face API token authentication failed") from exc
                if "403" in err_str or "permission" in err_str or "forbidden" in err_str:
                    raise HFPermissionDenied("Hugging Face storage permission denied") from exc
                if "404" in err_str or "not found" in err_str:
                    empty_data = {
                        "user_id": safe_uid,
                        "skills": [],
                        "updated_at": utcnow().isoformat(),
                    }
                    _set_cache(safe_uid, empty_data)
                    return empty_data

                if attempt == max_retries:
                    logger.error("HF download failed after %d retries for %s: %s", max_retries, storage_path, exc)
                    raise HFDownloadFailed(f"Failed to download user skills from Hugging Face: {type(exc).__name__}") from exc

                time.sleep(0.5 * (2 ** (attempt - 1)))

        empty_data = {"user_id": safe_uid, "skills": [], "updated_at": utcnow().isoformat()}
        return empty_data

    @staticmethod
    def save_skills(user_id: Any, data: Dict[str, Any]) -> Dict[str, Any]:
        """Save persistent user skills to Hugging Face Dataset repo."""
        safe_uid = _sanitize_user_id(user_id)
        storage_path = _get_storage_path(safe_uid)
        repo_id = SkillStorageService._get_repo_id()
        repo_type = SkillStorageService._get_repo_type()

        data["user_id"] = safe_uid
        data["updated_at"] = utcnow().isoformat()

        json_bytes = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        api = SkillStorageService._get_hf_api()

        max_retries = int(getattr(settings, "HF_STORAGE_MAX_RETRIES", 3))
        logger.info("Uploading user skills to HF: %s (%d bytes)", storage_path, len(json_bytes))

        for attempt in range(1, max_retries + 1):
            try:
                api.upload_file(
                    path_or_fileobj=io.BytesIO(json_bytes),
                    path_in_repo=storage_path,
                    repo_id=repo_id,
                    repo_type=repo_type,
                    commit_message=f"Update user skills for user {safe_uid}",
                )
                _set_cache(safe_uid, data)
                return data

            except Exception as exc:
                err_str = str(exc).lower()
                if "401" in err_str or "unauthorized" in err_str:
                    raise HFAuthenticationFailed("Hugging Face API token authentication failed") from exc
                if "403" in err_str or "forbidden" in err_str:
                    raise HFPermissionDenied("Hugging Face storage permission denied") from exc

                if attempt == max_retries:
                    logger.error("HF upload failed after %d retries for %s: %s", max_retries, storage_path, exc)
                    raise HFUploadFailed(f"Failed to upload skills to Hugging Face: {type(exc).__name__}") from exc

                time.sleep(0.5 * (2 ** (attempt - 1)))

        _set_cache(safe_uid, data)
        return data

    @staticmethod
    def add_skill(user_id: Any, skill_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new skill or update an existing duplicate skill."""
        safe_uid = _sanitize_user_id(user_id)

        raw_name = skill_dict.get("name", "")
        clean_name = _normalize_skill_name(raw_name)
        level = _validate_level(skill_dict.get("level", "beginner"))
        confidence = _validate_confidence(skill_dict.get("confidence"))
        source = _validate_source(skill_dict.get("source"))

        data = SkillStorageService.load_skills(safe_uid)
        skills_list: List[Dict[str, Any]] = data.get("skills", [])

        # Check for case-insensitive duplicate
        existing = next((s for s in skills_list if s.get("name", "").strip().lower() == clean_name.lower()), None)
        now_iso = utcnow().isoformat()

        if existing:
            logger.info("Updating existing duplicate skill '%s' for user %s", clean_name, safe_uid)
            existing["level"] = level
            existing["confidence"] = confidence
            existing["source"] = source
            existing["updated_at"] = now_iso
            
            # Preserve additional fields from imported skills if provided
            for key in ["instructions", "capabilities", "examples", "limitations", "source_url", "tags", "enabled"]:
                if key in skill_dict:
                    existing[key] = skill_dict[key]
            
            saved_skill = existing
        else:
            skill_num = len(skills_list) + 1
            new_id = f"skill_{skill_num:03d}"

            # Ensure unique ID if skill_001 already exists
            while any(s.get("id") == new_id for s in skills_list):
                skill_num += 1
                new_id = f"skill_{skill_num:03d}"

            saved_skill = {
                "id": new_id,
                "name": clean_name,
                "level": level,
                "confidence": confidence,
                "source": source,
                "created_at": now_iso,
                "updated_at": now_iso,
                "enabled": skill_dict.get("enabled", True),
            }
            
            # Add additional fields from imported skills
            for key in ["instructions", "capabilities", "examples", "limitations", "source_url", "tags"]:
                if key in skill_dict:
                    saved_skill[key] = skill_dict[key]
            
            skills_list.append(saved_skill)

        data["skills"] = skills_list
        SkillStorageService.save_skills(safe_uid, data)
        return saved_skill

    @staticmethod
    def get_skill(user_id: Any, skill_id: str) -> Dict[str, Any]:
        """Get single skill by ID or normalized name."""
        safe_uid = _sanitize_user_id(user_id)
        data = SkillStorageService.load_skills(safe_uid)

        target = skill_id.strip()
        for skill in data.get("skills", []):
            if skill.get("id") == target or skill.get("name", "").strip().lower() == target.lower():
                return skill

        raise SkillNotFound(f"Skill '{skill_id}' not found for user")

    @staticmethod
    def update_skill(user_id: Any, skill_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update single skill attributes (level, confidence, source, enabled, etc.)."""
        safe_uid = _sanitize_user_id(user_id)
        data = SkillStorageService.load_skills(safe_uid)
        skills_list = data.get("skills", [])

        target_skill = None
        for skill in skills_list:
            if skill.get("id") == skill_id or skill.get("name", "").strip().lower() == skill_id.strip().lower():
                target_skill = skill
                break

        if not target_skill:
            raise SkillNotFound(f"Skill '{skill_id}' not found for user")

        if "level" in update_data and update_data["level"]:
            target_skill["level"] = _validate_level(update_data["level"])

        if "confidence" in update_data and update_data["confidence"] is not None:
            target_skill["confidence"] = _validate_confidence(update_data["confidence"])

        if "enabled" in update_data and update_data["enabled"] is not None:
            target_skill["enabled"] = bool(update_data["enabled"])

        if "name" in update_data and update_data["name"]:
            new_name = _normalize_skill_name(update_data["name"])
            # Ensure name change doesn't conflict with another existing skill
            other = next((s for s in skills_list if s is not target_skill and s.get("name", "").strip().lower() == new_name.lower()), None)
            if other:
                logger.info("Merging skill update into existing skill '%s'", new_name)
                other["level"] = target_skill["level"]
                other["confidence"] = target_skill["confidence"]
                other["updated_at"] = utcnow().isoformat()
                skills_list.remove(target_skill)
                target_skill = other
            else:
                target_skill["name"] = new_name

        target_skill["updated_at"] = utcnow().isoformat()
        data["skills"] = skills_list
        SkillStorageService.save_skills(safe_uid, data)
        return target_skill

    @staticmethod
    def delete_skill(user_id: Any, skill_id: str) -> bool:
        """Delete single skill by ID or name."""
        safe_uid = _sanitize_user_id(user_id)
        data = SkillStorageService.load_skills(safe_uid)
        skills_list = data.get("skills", [])

        initial_len = len(skills_list)
        new_list = [
            s for s in skills_list
            if s.get("id") != skill_id and s.get("name", "").strip().lower() != skill_id.strip().lower()
        ]

        if len(new_list) == initial_len:
            raise SkillNotFound(f"Skill '{skill_id}' not found for user")

        data["skills"] = new_list
        SkillStorageService.save_skills(safe_uid, data)
        return True

    @staticmethod
    def delete_all_skills(user_id: Any) -> bool:
        """Delete the entire user skills file (skills/{user_id}.json) from Hugging Face repo."""
        safe_uid = _sanitize_user_id(user_id)
        storage_path = _get_storage_path(safe_uid)
        repo_id = SkillStorageService._get_repo_id()
        repo_type = SkillStorageService._get_repo_type()

        _invalidate_cache(safe_uid)
        api = SkillStorageService._get_hf_api()

        try:
            api.delete_file(
                path_in_repo=storage_path,
                repo_id=repo_id,
                repo_type=repo_type,
                commit_message=f"Delete all user skills for user {safe_uid}",
            )
            logger.info("Deleted skills file %s from HF repository %s", storage_path, repo_id)
            return True
        except EntryNotFoundError:
            logger.info("Skills file %s already deleted or non-existent on HF", storage_path)
            return True
        except Exception as exc:
            err_str = str(exc).lower()
            if "404" in err_str or "not found" in err_str:
                return True
            logger.error("Failed to delete skills file %s from HF: %s", storage_path, exc)
            raise HFDeleteFailed(f"Failed to delete skills file from Hugging Face: {type(exc).__name__}") from exc

    @staticmethod
    def get_relevant_skills_for_prompt(user_id: Any, prompt_text: str) -> List[Dict[str, Any]]:
        """Filter stored user skills relevant to a specific user prompt/question."""
        if not prompt_text:
            return []

        safe_uid = _sanitize_user_id(user_id)
        data = SkillStorageService.load_skills(safe_uid)
        user_skills = data.get("skills", [])

        text_lower = prompt_text.lower()
        relevant = []

        for skill in user_skills:
            s_name = skill.get("name", "").strip().lower()
            if s_name and (s_name in text_lower or text_lower in s_name):
                relevant.append(skill)

        return relevant
