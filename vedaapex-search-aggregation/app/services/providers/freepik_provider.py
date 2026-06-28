import httpx
from typing import Any
from ...core.config import settings


class FreepikProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.FREEPIK_API_KEY_TIER1,
            2: settings.FREEPIK_API_KEY_TIER2,
            3: settings.FREEPIK_API_KEY_TIER3,
            4: settings.FREEPIK_API_KEY_TIER4,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def run_model(input_data: dict, starting_tier: int) -> Any:
        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None
            for tier in range(starting_tier, 5):
                api_key = FreepikProvider.get_api_key(tier)
                if not api_key:
                    continue
                headers = {
                    "x-freepik-api-key": api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                }
                response = await client.post(
                    "https://api.freepik.com/v1/ai/text-to-image",
                    headers=headers,
                    json=input_data,
                )
                if response.status_code in [401, 402, 403, 429, 405]:
                    print(f"Freepik Tier {tier} exhausted ({response.status_code}). Switching...")
                    last_error = f"Tier {tier}: {response.text}"
                    continue
                if response.status_code != 200:
                    raise Exception(f"Freepik API error: {response.text}")
                return response.json()
            raise Exception(f"All Freepik tiers exhausted. Last error: {last_error}")
