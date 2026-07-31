import asyncio
import json
from typing import Any

import httpx

from ...core.config import settings


class TripoSRProvider:
    @staticmethod
    def _space_base_url() -> str:
        return (settings.TRIPOSR_SPACE_URL or "https://stabilityai-triposr.hf.space").rstrip("/")

    @staticmethod
    def _headers() -> dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/plain, */*",
        }

    @staticmethod
    async def generate_model(prompt: str | None = None, starting_tier: int = 1, image_url: str | None = None) -> Any:
        del starting_tier
        space_url = TripoSRProvider._space_base_url()
        input_value = image_url or prompt or ""
        payload = {
            "data": [input_value],
            "fn_index": 0,
            "session_hash": "triposr-backend",
        }

        async with httpx.AsyncClient(timeout=180.0) as client:
            last_error = None
            for endpoint in [
                f"{space_url}/gradio_api/call/predict",
                f"{space_url}/run/predict",
                f"{space_url}/api/predict",
            ]:
                try:
                    response = await client.post(endpoint, headers=TripoSRProvider._headers(), json=payload)
                    if response.status_code in {401, 403, 404, 405, 429}:
                        continue

                    if response.status_code >= 500:
                        continue

                    content_type = response.headers.get("content-type", "")
                    if "application/json" in content_type:
                        result = response.json()
                    else:
                        text = response.text.strip()
                        if not text:
                            raise Exception(f"TripoSR returned an empty response from {endpoint}")
                        try:
                            result = json.loads(text)
                        except Exception:
                            raise Exception(
                                f"TripoSR returned a non-JSON response from {endpoint}: {text[:500]}"
                            )

                    if isinstance(result, dict):
                        data = result.get("data") or result.get("output") or []
                        if isinstance(data, list):
                            for item in data:
                                if isinstance(item, str) and item.startswith("http"):
                                    return item
                                if isinstance(item, dict):
                                    for key in ("url", "model_url", "output_url", "download_url"):
                                        candidate = item.get(key)
                                        if isinstance(candidate, str) and candidate.startswith("http"):
                                            return candidate
                        if isinstance(result.get("url"), str) and result["url"].startswith("http"):
                            return result["url"]

                    raise Exception(f"TripoSR did not return a downloadable model URL: {result}")
                except Exception as exc:
                    last_error = str(exc)
                    await asyncio.sleep(1)

            raise Exception(f"TripoSR generation failed. Last error: {last_error}")
