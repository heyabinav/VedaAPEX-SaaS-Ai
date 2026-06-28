import httpx
from typing import Any
from app.core.config import settings


class MeshyProvider:
    """
    Connector for Meshy AI 3D Model Generation.
    Endpoint: https://api.meshy.ai/v2/text-to-3d
    """

    @staticmethod
    def get_api_key() -> str:
        return settings.MESHY_API_KEY or ""

    @staticmethod
    async def generate_3d(
        prompt: str, negative_prompt: str = "low quality", art_style: str = "realistic"
    ) -> Any:
        api_key = MeshyProvider.get_api_key()
        if not api_key:
            raise Exception("Meshy API Key not configured.")

        url = "https://api.meshy.ai/v2/text-to-3d"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "mode": "preview",
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "art_style": art_style,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=60.0)

            if response.status_code != 200:
                raise Exception(f"Meshy API Error: {response.text}")

            return response.json()

    @staticmethod
    async def edit_model(model_url: str, prompt: str, tier: int = 1) -> Any:
        """Max/Ultra: Refine or edit an existing 3D model."""
        api_key = MeshyProvider.get_api_key()
        if not api_key:
            raise Exception("Meshy API Key not configured.")

        # Meshy V2 Refine endpoint
        url = "https://api.meshy.ai/v2/text-to-3d/refine"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "prompt": prompt,
            "preview_task_id": model_url,  # Assuming model_url is the task_id or we pass it correctly
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=60.0)
            if response.status_code != 200:
                raise Exception(f"Meshy 3D Edit Error: {response.text}")
            return response.json()
