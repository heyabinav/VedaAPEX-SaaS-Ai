import httpx
from typing import Any
from ...core.config import settings
from ..key_manager import key_manager


class FalProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.FAL_API_KEY_TIER1,
            2: settings.FAL_API_KEY_TIER2,
            3: settings.FAL_API_KEY_TIER3,
            4: settings.FAL_API_KEY_TIER4,
            5: settings.FAL_API_KEY_TIER5,
            6: settings.FAL_API_KEY_TIER6,
            7: settings.FAL_API_KEY_TIER7,
            8: settings.FAL_API_KEY_TIER8,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def run_model(model: str, input_data: dict, starting_tier: int) -> Any:
        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None
            for tier in range(starting_tier, 9):
                api_key = FalProvider.get_api_key(tier) or key_manager.get_key(service="image", provider="fal")
                if not api_key:
                    continue
                headers = {
                    "Authorization": f"Key {api_key}",
                    "Content-Type": "application/json",
                }
                response = await client.post(
                    f"https://fal.run/v1/models/{model}:generate",
                    headers=headers,
                    json=input_data,
                )

                if response.status_code in [401, 402, 403, 429]:
                    print(
                        f"Fal Tier {tier} exhausted/failed ({response.status_code}). Switching to next tier..."
                    )
                    last_error = f"Tier {tier}: {response.text}"
                    continue
                if response.status_code != 200:
                    raise Exception(f"Fal API error: {response.text}")
                return response.json()
            raise Exception(f"All Fal tiers exhausted. Last error: {last_error}")
