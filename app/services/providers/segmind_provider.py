import httpx
from typing import Any
from ...core.config import settings


class SegmindProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.SEGMIND_API_KEY_TIER1,
            2: settings.SEGMIND_API_KEY_TIER2,
            3: settings.SEGMIND_API_KEY_TIER3,
            4: settings.SEGMIND_API_KEY_TIER4,
            5: settings.SEGMIND_API_KEY_TIER5,
            6: settings.SEGMIND_API_KEY_TIER6,
            7: settings.SEGMIND_API_KEY_TIER7,
            8: settings.SEGMIND_API_KEY_TIER8,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def run_model(model: str, input_data: dict, starting_tier: int) -> Any:
        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None
            for tier in range(starting_tier, 9):
                api_key = SegmindProvider.get_api_key(tier)
                if not api_key:
                    continue
                headers = {"x-api-key": api_key, "Content-Type": "application/json"}
                response = await client.post(
                    f"https://api.segmind.com/v1/{model}",
                    headers=headers,
                    json=input_data,
                )
                if response.status_code in [401, 402, 403, 429]:
                    print(f"Segmind Tier {tier} exhausted ({response.status_code}). Switching...")
                    last_error = f"Tier {tier}: {response.text}"
                    continue
                if response.status_code != 200:
                    raise Exception(f"Segmind API error: {response.text}")
                return (
                    response.content
                )  # Segmind usually returns raw image bytes or base64 json depending on request
            raise Exception(f"All Segmind tiers exhausted. Last error: {last_error}")
