import httpx
from typing import Any
from ...core.config import settings


class DeepAIProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.DEEPAI_API_KEY_TIER1,
            2: settings.DEEPAI_API_KEY_TIER2,
            3: settings.DEEPAI_API_KEY_TIER3,
            4: settings.DEEPAI_API_KEY_TIER4,
            5: settings.DEEPAI_API_KEY_TIER5,
            6: settings.DEEPAI_API_KEY_TIER6,
            7: settings.DEEPAI_API_KEY_TIER7,
            8: settings.DEEPAI_API_KEY_TIER8,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def run_model(input_data: dict, starting_tier: int) -> Any:
        endpoint = "https://api.deepai.org/api/text2img"

        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None
            for tier in range(starting_tier, 9):
                api_key = DeepAIProvider.get_api_key(tier)
                if not api_key:
                    continue

                headers = {"api-key": api_key}

                try:
                    # DeepAI API expects form-data (POST with data=...)
                    response = await client.post(endpoint, headers=headers, data=input_data)

                    if response.status_code in [401, 402, 403, 429]:
                        print(
                            f"DeepAI Tier {tier} exhausted ({response.status_code}). Switching..."
                        )
                        last_error = f"Tier {tier}: {response.text}"
                        continue

                    if response.status_code != 200:
                        raise Exception(f"DeepAI API error: {response.text}")

                    return response.json()
                except Exception as e:
                    last_error = str(e)
                    print(f"DeepAI Tier {tier} request error: {e}")
                    continue

            raise Exception(f"All DeepAI tiers exhausted. Last error: {last_error}")
