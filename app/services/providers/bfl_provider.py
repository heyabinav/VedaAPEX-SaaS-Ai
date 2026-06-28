import httpx
from typing import Any
from ...core.config import settings


class BFLProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.BFL_API_KEY_TIER1,
            2: settings.BFL_API_KEY_TIER2,
            3: settings.BFL_API_KEY_TIER3,
            4: settings.BFL_API_KEY_TIER4,
            5: settings.BFL_API_KEY_TIER5,
            6: settings.BFL_API_KEY_TIER6,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def run_model(model: str, input_data: dict, starting_tier: int) -> Any:
        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None
            for tier in range(starting_tier, 7):
                api_key = BFLProvider.get_api_key(tier)
                if not api_key:
                    continue
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                response = await client.post(
                    "https://api.bfl.ai/v1/generate",
                    headers=headers,
                    json={"model": model, "parameters": input_data},
                )
                if response.status_code in [401, 402, 403, 429]:
                    print(f"BFL.ai Tier {tier} exhausted ({response.status_code}). Switching...")
                    last_error = f"Tier {tier}: {response.text}"
                    continue
                if response.status_code != 200:
                    raise Exception(f"BFL.ai API error: {response.text}")
                return response.json()
            raise Exception(f"All BFL.ai tiers exhausted. Last error: {last_error}")
