import httpx
from typing import Any
from ...core.config import settings


class TogetherProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.TOGETHER_API_KEY_TIER1,
            2: settings.TOGETHER_API_KEY_TIER2,
            3: settings.TOGETHER_API_KEY_TIER3,
            4: settings.TOGETHER_API_KEY_TIER4,
            5: settings.TOGETHER_API_KEY_TIER5,
            6: settings.TOGETHER_API_KEY_TIER6,
            7: settings.TOGETHER_API_KEY_TIER7,
            8: settings.TOGETHER_API_KEY_TIER8,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def run_model(model: str, input_data: dict, starting_tier: int) -> Any:
        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None
            for tier in range(starting_tier, 9):
                api_key = TogetherProvider.get_api_key(tier)
                if not api_key:
                    continue
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                endpoint = input_data.pop(
                    "endpoint", "https://api.together.xyz/v1/images/generations"
                )

                payload = {"model": model, **input_data}
                response = await client.post(endpoint, headers=headers, json=payload)

                if response.status_code in [401, 402, 403, 429]:
                    print(
                        f"Together AI Tier {tier} exhausted ({response.status_code}). Switching..."
                    )
                    last_error = f"Tier {tier}: {response.text}"
                    input_data["endpoint"] = endpoint  # Restore for next loop
                    continue
                if response.status_code != 200:
                    raise Exception(f"Together AI API error: {response.text}")
                return response.json()
            raise Exception(f"All Together AI tiers exhausted. Last error: {last_error}")
