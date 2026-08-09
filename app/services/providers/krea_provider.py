import httpx
from typing import Any
from ...core.config import settings


class KreaProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.KREA_API_KEY_TIER1,
            2: settings.KREA_API_KEY_TIER2,
            3: settings.KREA_API_KEY_TIER3,
            4: settings.KREA_API_KEY_TIER4,
            5: settings.KREA_API_KEY_TIER5,
            6: settings.KREA_API_KEY_TIER6,
            7: settings.KREA_API_KEY_TIER7,
            8: settings.KREA_API_KEY_TIER8,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def run_model(model: str, input_data: dict, starting_tier: int) -> Any:
        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None
            for tier in range(starting_tier, 9):
                api_key = KreaProvider.get_api_key(tier)
                if not api_key:
                    continue
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                response = await client.post(
                    "https://api.krea.ai/v1/images/generations",
                    headers=headers,
                    json={"model": model, "prompt": input_data.get("prompt", ""), **input_data},
                )
                if response.status_code in [401, 402, 403, 429]:
                    print(f"Krea.ai Tier {tier} exhausted ({response.status_code}). Switching...")
                    last_error = f"Tier {tier}: {response.text}"
                    continue
                if response.status_code != 200:
                    raise Exception(f"Krea.ai API error: {response.text}")
                return response.json()
            raise Exception(f"All Krea.ai tiers exhausted. Last error: {last_error}")
