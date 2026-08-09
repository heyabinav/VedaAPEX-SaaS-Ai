import httpx
from typing import Any
from ...core.config import settings


class PixverseProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.PIXVERSE_API_KEY_TIER1,
            2: settings.PIXVERSE_API_KEY_TIER2,
            3: settings.PIXVERSE_API_KEY_TIER3,
            4: settings.PIXVERSE_API_KEY_TIER4,
            5: settings.PIXVERSE_API_KEY_TIER5,
            6: settings.PIXVERSE_API_KEY_TIER6,
            7: settings.PIXVERSE_API_KEY_TIER7,
            8: settings.PIXVERSE_API_KEY_TIER8,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def run_model(input_data: dict, starting_tier: int) -> Any:
        # Example Pixverse API integration
        # Replace the endpoint with the actual Pixverse API endpoint if necessary
        endpoint = "https://api.pixverse.ai/v1/generate"  # Updated public-facing endpoint fallback

        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None
            for tier in range(starting_tier, 9):
                api_key = PixverseProvider.get_api_key(tier)
                if not api_key:
                    continue

                # Pixverse might use 'Bearer <token>' or 'Key <token>'
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }

                try:
                    response = await client.post(endpoint, headers=headers, json=input_data)

                    if response.status_code in [401, 402, 403, 429]:
                        print(
                            f"Pixverse Tier {tier} exhausted/failed ({response.status_code}). Switching to next tier..."
                        )
                        last_error = f"Tier {tier}: {response.text}"
                        continue

                    if response.status_code != 200:
                        raise Exception(f"Pixverse API error: {response.text}")

                    result = response.json()

                    # You might need to implement a polling mechanism here if Pixverse is fully async
                    # returning a task_id to check later.

                    # Assuming synchronous or providing the response to be handled by frontend
                    return result
                except Exception as e:
                    last_error = str(e)
                    print(f"Pixverse Tier {tier} request error: {e}")
                    continue

            raise Exception(f"All Pixverse tiers exhausted. Last error: {last_error}")
