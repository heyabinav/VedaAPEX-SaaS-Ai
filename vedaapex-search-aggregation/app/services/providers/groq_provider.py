import httpx
from typing import Any
from ...core.config import settings


class GroqProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.GROQ_API_KEY_TIER1,
            2: settings.GROQ_API_KEY_TIER2,
            3: settings.GROQ_API_KEY_TIER3,
            4: settings.GROQ_API_KEY_TIER4,
            5: settings.GROQ_API_KEY_TIER5,
            6: settings.GROQ_API_KEY_TIER6,
            7: settings.GROQ_API_KEY_TIER7,
            8: settings.GROQ_API_KEY_TIER8,
            9: settings.GROQ_API_KEY_TIER9,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def run_model(model: str, input_data: dict, starting_tier: int) -> Any:
        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None
            endpoint = input_data.pop("endpoint", "https://api.groq.com/openai/v1/chat/completions")

            for tier in range(starting_tier, 10):
                api_key = GroqProvider.get_api_key(tier)
                if not api_key:
                    continue

                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }

                payload = {"model": model, **input_data}
                try:
                    response = await client.post(endpoint, headers=headers, json=payload)
                    if response.status_code in [401, 402, 403, 429]:
                        print(f"Groq Tier {tier} exhausted ({response.status_code}). Switching...")
                        last_error = f"Tier {tier}: {response.text}"
                        input_data["endpoint"] = endpoint  # Restore for next loop
                        continue
                    if response.status_code != 200:
                        raise Exception(f"Groq API error: {response.text}")
                    return response.json()
                except Exception as e:
                    last_error = str(e)
                    print(f"Groq Tier {tier} failed: {e}")
                    input_data["endpoint"] = endpoint  # Restore for next loop
                    continue
            raise Exception(f"All Groq tiers exhausted. Last error: {last_error}")
