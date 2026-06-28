import asyncio
from typing import Any

import httpx

from ...core.config import settings


class Tripo3DProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.TRIPO3D_API_KEY_TIER1,
            2: settings.TRIPO3D_API_KEY_TIER2,
            3: settings.TRIPO3D_API_KEY_TIER3,
            4: settings.TRIPO3D_API_KEY_TIER4,
            5: settings.TRIPO3D_API_KEY_TIER5,
            6: settings.TRIPO3D_API_KEY_TIER6,
            7: settings.TRIPO3D_API_KEY_TIER7,
            8: settings.TRIPO3D_API_KEY_TIER8,
        }
        return keys.get(tier) or ""

    @staticmethod
    def _headers(api_key: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    async def generate_model(prompt: str, starting_tier: int = 1) -> Any:
        create_url = f"{settings.TRIPO3D_API_BASE_URL.rstrip('/')}/task"

        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None

            for tier in range(starting_tier, 9):
                api_key = Tripo3DProvider.get_api_key(tier)
                if not api_key:
                    continue

                headers = Tripo3DProvider._headers(api_key)
                create_payload = {
                    "type": "text_to_model",
                    "prompt": prompt,
                    "model_version": settings.TRIPO3D_MODEL_VERSION,
                }

                try:
                    create_response = await client.post(
                        create_url, headers=headers, json=create_payload
                    )
                    if create_response.status_code in [401, 402, 403, 429]:
                        last_error = f"Tier {tier}: {create_response.text}"
                        continue
                    if create_response.status_code != 200:
                        raise Exception(f"Tripo3D create error: {create_response.text}")

                    create_result = create_response.json()
                    if create_result.get("code") != 0:
                        raise Exception(f"Tripo3D create failed: {create_result}")

                    task_id = create_result.get("data", {}).get("task_id")
                    if not task_id:
                        raise Exception(f"Tripo3D create response missing task_id: {create_result}")

                    task_result = await Tripo3DProvider._poll_task(client, headers, task_id)
                    model_url = Tripo3DProvider._extract_model_url(task_result)
                    if model_url:
                        return model_url

                    export_format = (settings.TRIPO3D_EXPORT_FORMAT or "GLB").upper()
                    export_task_id = await Tripo3DProvider._request_export(
                        client, headers, task_id, export_format
                    )
                    export_result = await Tripo3DProvider._poll_task(
                        client, headers, export_task_id
                    )
                    model_url = Tripo3DProvider._extract_model_url(export_result)
                    if model_url:
                        return model_url

                    raise Exception(
                        f"Tripo3D export completed but no downloadable model URL was found: {export_result}"
                    )
                except Exception as exc:
                    last_error = str(exc)
                    continue

            raise Exception(f"All Tripo3D tiers exhausted or failed. Last error: {last_error}")

    @staticmethod
    async def _request_export(
        client: httpx.AsyncClient,
        headers: dict[str, str],
        original_task_id: str,
        export_format: str,
    ) -> str:
        export_url = f"{settings.TRIPO3D_API_BASE_URL.rstrip('/')}/task"
        payload = {
            "type": "convert_model",
            "format": export_format,
            "original_model_task_id": original_task_id,
        }
        response = await client.post(export_url, headers=headers, json=payload)
        if response.status_code != 200:
            raise Exception(f"Tripo3D export request failed: {response.text}")

        result = response.json()
        if result.get("code") != 0:
            raise Exception(f"Tripo3D export error: {result}")

        task_id = result.get("data", {}).get("task_id")
        if not task_id:
            raise Exception(f"Tripo3D export response missing task_id: {result}")
        return task_id

    @staticmethod
    async def _poll_task(
        client: httpx.AsyncClient, headers: dict[str, str], task_id: str
    ) -> dict[str, Any]:
        task_url = f"{settings.TRIPO3D_API_BASE_URL.rstrip('/')}/task/{task_id}"

        for _ in range(90):
            response = await client.get(task_url, headers=headers)
            if response.status_code != 200:
                await asyncio.sleep(4)
                continue

            result = response.json()
            if result.get("code") != 0:
                raise Exception(f"Tripo3D task query failed: {result}")

            data = result.get("data", {})
            status = str(data.get("status", "")).lower()
            if status in {"success", "succeeded", "completed"}:
                return result
            if status in {"failed", "cancelled", "canceled"}:
                raise Exception(f"Tripo3D task failed: {result}")

            await asyncio.sleep(4)

        raise Exception(f"Tripo3D task timed out: {task_id}")

    @staticmethod
    def _extract_model_url(result: dict[str, Any]) -> str | None:
        data = result.get("data", {})

        direct_candidates = [
            data.get("model_url"),
            data.get("output_url"),
            data.get("url"),
        ]
        for candidate in direct_candidates:
            if isinstance(candidate, str) and candidate.startswith("http"):
                return candidate

        output = data.get("output")
        if isinstance(output, dict):
            for key in ("model", "glb", "gltf", "fbx", "obj", "stl", "url"):
                candidate = output.get(key)
                if isinstance(candidate, str) and candidate.startswith("http"):
                    return candidate
                if isinstance(candidate, dict):
                    nested_url = candidate.get("url")
                    if isinstance(nested_url, str) and nested_url.startswith("http"):
                        return nested_url

        if isinstance(output, list):
            for item in output:
                if isinstance(item, str) and item.startswith("http"):
                    return item
                if isinstance(item, dict):
                    nested_url = item.get("url")
                    if isinstance(nested_url, str) and nested_url.startswith("http"):
                        return nested_url

        return None
