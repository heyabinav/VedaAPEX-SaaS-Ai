import asyncio
from typing import Any

import httpx

from ...core.config import settings


class GensparkProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.GENSPARK_API_KEY_TIER1,
            2: settings.GENSPARK_API_KEY_TIER2,
            3: settings.GENSPARK_API_KEY_TIER3,
            4: settings.GENSPARK_API_KEY_TIER4,
            5: settings.GENSPARK_API_KEY_TIER5,
            6: settings.GENSPARK_API_KEY_TIER6,
            7: settings.GENSPARK_API_KEY_TIER7,
            8: settings.GENSPARK_API_KEY_TIER8,
        }
        return keys.get(tier) or ""

    @staticmethod
    def _build_headers(api_key: str) -> dict[str, str]:
        header_name = settings.GENSPARK_AUTH_HEADER or "Authorization"
        auth_scheme = (settings.GENSPARK_AUTH_SCHEME or "Bearer").strip()
        header_value = f"{auth_scheme} {api_key}".strip() if auth_scheme else api_key
        return {
            header_name: header_value,
            "Content-Type": "application/json",
        }

    @staticmethod
    def _join_url(base_url: str, path: str) -> str:
        return f"{base_url.rstrip('/')}/{path.lstrip('/')}"

    @staticmethod
    def _extract_video_url(payload: Any) -> str | None:
        if isinstance(payload, str) and payload.startswith("http"):
            return payload
        if not isinstance(payload, dict):
            return None

        direct_keys = ("video_url", "url", "output_url", "download_url")
        for key in direct_keys:
            value = payload.get(key)
            if isinstance(value, str) and value.startswith("http"):
                return value

        data = payload.get("data")
        if isinstance(data, dict):
            for key in direct_keys:
                value = data.get(key)
                if isinstance(value, str) and value.startswith("http"):
                    return value

        return None

    @staticmethod
    def _extract_task_id(payload: Any) -> str | None:
        if not isinstance(payload, dict):
            return None

        candidate_keys = ("task_id", "id", "job_id", "generation_id")
        for key in candidate_keys:
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value

        data = payload.get("data")
        if isinstance(data, dict):
            for key in candidate_keys:
                value = data.get(key)
                if isinstance(value, str) and value:
                    return value

        return None

    @staticmethod
    async def generate_video(prompt: str, starting_tier: int, model: str = "auto") -> Any:
        if not settings.GENSPARK_API_BASE_URL:
            raise Exception(
                "GENSPARK_API_BASE_URL is not configured. Add the official Genspark API base URL before using provider='genspark'."
            )

        create_url = GensparkProvider._join_url(
            settings.GENSPARK_API_BASE_URL,
            settings.GENSPARK_VIDEO_CREATE_PATH,
        )

        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None

            for tier in range(starting_tier, 9):
                api_key = GensparkProvider.get_api_key(tier)
                if not api_key:
                    continue

                headers = GensparkProvider._build_headers(api_key)
                payload = {
                    "prompt": prompt,
                    "model": model,
                }

                try:
                    response = await client.post(create_url, headers=headers, json=payload)

                    if response.status_code in [401, 402, 403, 429]:
                        last_error = f"Tier {tier}: {response.text}"
                        continue

                    if response.status_code not in [200, 201, 202]:
                        raise Exception(f"Genspark API error: {response.text}")

                    result = response.json()
                    video_url = GensparkProvider._extract_video_url(result)
                    if video_url:
                        return video_url

                    task_id = GensparkProvider._extract_task_id(result)
                    if not task_id:
                        raise Exception(
                            "Genspark response did not include a direct video URL or a recognized task id."
                        )

                    status_url = GensparkProvider._join_url(
                        settings.GENSPARK_API_BASE_URL,
                        settings.GENSPARK_VIDEO_STATUS_PATH.format(task_id=task_id),
                    )

                    for _ in range(60):
                        await asyncio.sleep(5)
                        status_response = await client.get(status_url, headers=headers)

                        if status_response.status_code in [401, 402, 403, 429]:
                            raise Exception(
                                f"Genspark status polling failed: {status_response.text}"
                            )
                        if status_response.status_code != 200:
                            continue

                        status_payload = status_response.json()
                        video_url = GensparkProvider._extract_video_url(status_payload)
                        if video_url:
                            return video_url

                        status_data = status_payload.get("data", status_payload)
                        status = (
                            str(status_data.get("status", "")).lower()
                            if isinstance(status_data, dict)
                            else ""
                        )
                        if status in {"failed", "error", "cancelled"}:
                            raise Exception(f"Genspark video generation failed: {status_payload}")

                    raise Exception("Genspark video generation timed out.")
                except Exception as exc:
                    last_error = str(exc)
                    continue

            raise Exception(f"All Genspark tiers exhausted or failed. Last error: {last_error}")
