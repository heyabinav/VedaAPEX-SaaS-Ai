import httpx
from typing import Any
from ...core.config import settings


class MistralProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.MISTRAL_API_KEY_TIER1,
            2: settings.MISTRAL_API_KEY_TIER2,
            3: settings.MISTRAL_API_KEY_TIER3,
            4: settings.MISTRAL_API_KEY_TIER4,
            5: settings.MISTRAL_API_KEY_TIER5,
            6: settings.MISTRAL_API_KEY_TIER6,
            7: settings.MISTRAL_API_KEY_TIER7,
            8: settings.MISTRAL_API_KEY_TIER8,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def run_model(model: str, input_data: dict, starting_tier: int) -> Any:
        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None
            endpoint = input_data.pop("endpoint", "https://api.mistral.ai/v1/chat/completions")

            for tier in range(starting_tier, 9):
                api_key = MistralProvider.get_api_key(tier)
                if not api_key:
                    continue

                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }

                payload = {"model": model or "mistral-small-latest", **input_data}
                try:
                    response = await client.post(endpoint, headers=headers, json=payload)
                    if response.status_code in [401, 402, 403, 429]:
                        print(f"Mistral Tier {tier} exhausted ({response.status_code}). Switching...")
                        last_error = f"Tier {tier}: {response.text}"
                        input_data["endpoint"] = endpoint
                        continue
                    if response.status_code != 200:
                        raise Exception(f"Mistral API error ({response.status_code}): {response.text}")
                    return response.json()
                except Exception as e:
                    last_error = str(e)
                    print(f"Mistral Tier {tier} failed: {e}")
                    input_data["endpoint"] = endpoint
                    continue
            raise Exception(f"All Mistral tiers exhausted. Last error: {last_error}")
