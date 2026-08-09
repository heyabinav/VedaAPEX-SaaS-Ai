import httpx
from typing import Any
from ...core.config import settings


class TemplarProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.TEMPLAR_API_KEY_TIER1,
            2: settings.TEMPLAR_API_KEY_TIER2,
            3: settings.TEMPLAR_API_KEY_TIER3,
            4: settings.TEMPLAR_API_KEY_TIER4,
            5: settings.TEMPLAR_API_KEY_TIER5,
            6: settings.TEMPLAR_API_KEY_TIER6,
            7: settings.TEMPLAR_API_KEY_TIER7,
            8: settings.TEMPLAR_API_KEY_TIER8,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def run_model(endpoint_path: str, payload: dict, starting_tier: int = 1) -> Any:
        base_url = "https://templar.odysii.in/api"

        async with httpx.AsyncClient(timeout=60.0) as client:
            last_error = None
            for tier in range(starting_tier, 9):
                api_key = TemplarProvider.get_api_key(tier)
                if not api_key:
                    continue

                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }

                try:
                    # Endpoint path could be /generate, /template, etc.
                    response = await client.post(
                        f"{base_url}/{endpoint_path.lstrip('/')}",
                        headers=headers,
                        json=payload,
                    )

                    if response.status_code in [401, 402, 403, 429]:
                        print(f"Templar Tier {tier} exhausted. Switching...")
                        last_error = f"Tier {tier}: {response.text}"
                        continue

                    if response.status_code not in [200, 201]:
                        raise Exception(f"Templar API error: {response.text}")

                    return response.json()
                except Exception as e:
                    last_error = str(e)
                    continue
            raise Exception(f"All Templar tiers exhausted. Last error: {last_error}")
