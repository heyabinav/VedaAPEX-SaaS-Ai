import httpx
from typing import Any
from ...core.config import settings


class SuperAPIProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.SUPER_API_KEY_TIER1,
            2: settings.SUPER_API_KEY_TIER2,
            3: settings.SUPER_API_KEY_TIER3,
            4: settings.SUPER_API_KEY_TIER4,
            5: settings.SUPER_API_KEY_TIER5,
            6: settings.SUPER_API_KEY_TIER6,
            7: settings.SUPER_API_KEY_TIER7,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def run_model(endpoint: str, payload: dict, starting_tier: int = 1) -> Any:
        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None

            for tier in range(starting_tier, 8):
                api_key = SuperAPIProvider.get_api_key(tier)
                if not api_key:
                    continue

                # Standard bearer token auth for Super API
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }

                try:
                    response = await client.post(endpoint, headers=headers, json=payload)

                    if response.status_code in [401, 402, 403, 429]:
                        print(
                            f"Super API Tier {tier} exhausted ({response.status_code}). Switching..."
                        )
                        last_error = f"Tier {tier}: {response.text}"
                        continue

                    if response.status_code != 200:
                        raise Exception(f"Super API error: {response.text}")

                    return response.json()

                except Exception as e:
                    last_error = str(e)
                    print(f"Super API Tier {tier} failed: {e}")
                    continue

            raise Exception(f"All Super API tiers exhausted. Last error: {last_error}")
