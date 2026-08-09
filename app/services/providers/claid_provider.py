import httpx
from typing import Any
from ...core.config import settings


class ClaidProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.CLAID_API_KEY_TIER1,
            2: settings.CLAID_API_KEY_TIER2,
            3: settings.CLAID_API_KEY_TIER3,
            4: settings.CLAID_API_KEY_TIER4,
            5: settings.CLAID_API_KEY_TIER5,
            6: settings.CLAID_API_KEY_TIER6,
            7: settings.CLAID_API_KEY_TIER7,
            8: settings.CLAID_API_KEY_TIER8,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def run_model(endpoint_path: str, payload: dict, starting_tier: int = 1) -> Any:
        base_url = "https://api.claid.ai/v1"

        async with httpx.AsyncClient(timeout=60.0) as client:
            last_error = None
            for tier in range(starting_tier, 9):
                api_key = ClaidProvider.get_api_key(tier)
                if not api_key:
                    continue

                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }

                try:
                    url = f"{base_url}/{endpoint_path.lstrip('/')}"
                    response = await client.post(url, headers=headers, json=payload)

                    if response.status_code in [401, 402, 403, 429]:
                        print(f"Claid Tier {tier} exhausted. Switching...")
                        last_error = f"Tier {tier}: {response.text}"
                        continue

                    if response.status_code not in [200, 201]:
                        raise Exception(f"Claid API error: {response.text}")

                    return response.json()
                except Exception as e:
                    last_error = str(e)
                    continue
            raise Exception(f"All Claid tiers exhausted. Last error: {last_error}")
