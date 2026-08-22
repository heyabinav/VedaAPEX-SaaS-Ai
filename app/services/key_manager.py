import json
import os
from datetime import datetime
from threading import Lock
from typing import Optional

from app.core.api_key_config import APIKey, KeyType


class APIKeyManager:
    def __init__(self, storage_path: str | None = None):
        self._lock = Lock()
        self._keys: list[APIKey] = []
        self._storage_path = storage_path or os.path.join(os.getcwd(), "key_usage.json")
        self._load_keys_from_env()
        self._load_usage_from_file()

    def _load_keys_from_env(self) -> None:
        self._keys = []
        self._add_keys_from_env(prefix="OPENAI", provider="openai", service="text")
        self._add_keys_from_env(prefix="OPENROUTER", provider="openrouter", service="text")
        self._add_keys_from_env(prefix="STABILITY", provider="stability", service="image")
        self._add_keys_from_env(prefix="REPLICATE", provider="replicate", service="image")
        self._add_keys_from_env(prefix="REPLICATE", provider="replicate", service="video")
        self._add_keys_from_env(prefix="FAL", provider="fal", service="image")
        self._add_keys_from_env(prefix="FAL", provider="fal", service="video")
        self._add_keys_from_env(prefix="GOOGLE", provider="google", service="all")
        self._add_keys_from_env(prefix="GITHUB", provider="github", service="all")
        self._add_env_alias("TEXT_GENERATION_API_KEY", provider="openai", service="text")
        self._add_env_alias("DOCUMENT_GENERATION_API_KEY", provider="openai", service="text")
        self._add_env_alias("VIDEO_GENERATION_API_KEY", provider="generic", service="video")
        self._add_env_alias("PPT_GENERATION_API_KEY", provider="generic", service="ppt")
        self._add_env_alias("OPENAI_API_KEY", provider="openai", service="text")
        self._add_env_alias("GEMINI_API_KEY", provider="google", service="text")
        self._add_env_alias("VISION_API_KEY", provider="google", service="text")
        self._add_env_alias("FAL_API_KEY", provider="fal", service="video")
        self._add_env_alias("REPLICATE_API_KEY", provider="replicate", service="video")
        self._add_env_alias("OPENROUTER_API_KEY", provider="openrouter", service="video")

    def _add_env_alias(self, env_name: str, provider: str, service: str) -> None:
        key_value = os.getenv(env_name)
        if not key_value:
            return
        self._keys.append(
            APIKey(
                key=key_value,
                provider=provider,
                key_type=KeyType.PERMANENT,
                service=service,
            )
        )

    def _add_keys_from_env(self, prefix: str, provider: str, service: str) -> None:
        for key_type, suffix in ((KeyType.DAILY, "DAILY"), (KeyType.MONTHLY, "MONTHLY"), (KeyType.PERMANENT, "PERMANENT")):
            index = 1
            while True:
                env_name = f"{prefix}_KEY_{suffix}_{index}"
                key_value = os.getenv(env_name)
                if not key_value:
                    break
                limit_name = f"{env_name}_LIMIT"
                limit_value = os.getenv(limit_name)
                daily_limit = int(limit_value) if limit_value and key_type == KeyType.DAILY else None
                monthly_limit = int(limit_value) if limit_value and key_type == KeyType.MONTHLY else 1 if key_type == KeyType.MONTHLY else None
                self._keys.append(
                    APIKey(
                        key=key_value,
                        provider=provider,
                        key_type=key_type,
                        service=service,
                        daily_limit=daily_limit,
                        monthly_limit=monthly_limit,
                    )
                )
                index += 1

    def get_key(self, service: str, provider: str) -> str:
        with self._lock:
            self._auto_reset_if_needed()
            daily_key = self._find_available_key(service, provider, KeyType.DAILY)
            if daily_key:
                return daily_key.key

            monthly_key = self._find_available_key(service, provider, KeyType.MONTHLY)
            if monthly_key:
                return monthly_key.key

            permanent_key = self._find_available_key(service, provider, KeyType.PERMANENT)
            if permanent_key:
                return permanent_key.key

            raise Exception(f"No available API key for {provider}/{service}")

    def _find_available_key(self, service: str, provider: str, key_type: KeyType) -> Optional[APIKey]:
        candidates = [
            key
            for key in self._keys
            if key.provider == provider
            and (key.service == service or key.service == "all")
            and key.key_type == key_type
            and not key.is_exhausted
        ]
        if key_type == KeyType.DAILY:
            return next((key for key in candidates if key.used_today < (key.daily_limit or float("inf"))), None)
        if key_type == KeyType.MONTHLY:
            monthly_candidates = [
                key for key in candidates if key.used_this_month < (key.monthly_limit or 1)
            ]
            return monthly_candidates[0] if monthly_candidates else None
        return candidates[0] if candidates else None

    def mark_used(self, api_key: str, tokens_used: int = 1) -> None:
        with self._lock:
            for key in self._keys:
                if key.key == api_key:
                    key.used_today += tokens_used
                    key.used_this_month += tokens_used
                    self._check_exhaustion(key)
                    self._save_usage_to_file()
                    break

    def mark_exhausted(self, api_key: str) -> None:
        with self._lock:
            for key in self._keys:
                if key.key == api_key:
                    key.is_exhausted = True
                    self._save_usage_to_file()
                    break

    def _check_exhaustion(self, key: APIKey) -> None:
        if key.key_type == KeyType.DAILY and key.daily_limit is not None:
            if key.used_today >= key.daily_limit:
                key.is_exhausted = True
        elif key.key_type == KeyType.MONTHLY:
            if key.used_this_month >= (key.monthly_limit or 1):
                key.is_exhausted = True

    def _auto_reset_if_needed(self) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")

        for key in self._keys:
            if key.key_type == KeyType.DAILY and key.last_reset_date != today:
                key.used_today = 0
                key.is_exhausted = False
                key.last_reset_date = today

            if key.key_type == KeyType.MONTHLY and key.last_reset_month != month:
                key.used_this_month = 0
                key.is_exhausted = False
                key.last_reset_month = month

    def _save_usage_to_file(self) -> None:
        data = {}
        for key in self._keys:
            data[key.key[-8:]] = {
                "used_today": key.used_today,
                "used_this_month": key.used_this_month,
                "is_exhausted": key.is_exhausted,
                "last_reset_date": key.last_reset_date,
                "last_reset_month": key.last_reset_month,
            }
        with open(self._storage_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)

    def _load_usage_from_file(self) -> None:
        try:
            with open(self._storage_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            for key in self._keys:
                saved = data.get(key.key[-8:])
                if saved:
                    key.used_today = saved.get("used_today", 0)
                    key.used_this_month = saved.get("used_this_month", 0)
                    key.is_exhausted = saved.get("is_exhausted", False)
                    key.last_reset_date = saved.get("last_reset_date", "")
                    key.last_reset_month = saved.get("last_reset_month", "")
        except FileNotFoundError:
            return
        except json.JSONDecodeError:
            return

    def get_status(self) -> dict:
        return {
            "daily_keys": [
                {
                    "provider": k.provider,
                    "service": k.service,
                    "used_today": k.used_today,
                    "exhausted": k.is_exhausted,
                }
                for k in self._keys
                if k.key_type == KeyType.DAILY
            ],
            "monthly_keys": [
                {
                    "provider": k.provider,
                    "service": k.service,
                    "used_this_month": k.used_this_month,
                    "exhausted": k.is_exhausted,
                }
                for k in self._keys
                if k.key_type == KeyType.MONTHLY
            ],
            "permanent_keys": [
                {
                    "provider": k.provider,
                    "service": k.service,
                    "exhausted": k.is_exhausted,
                }
                for k in self._keys
                if k.key_type == KeyType.PERMANENT
            ],
        }


key_manager = APIKeyManager()
