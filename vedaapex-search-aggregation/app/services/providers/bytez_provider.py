import httpx
from typing import Any
from ...core.config import settings


class BytezProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.BYTEZ_API_KEY_TIER1,
            2: settings.BYTEZ_API_KEY_TIER2,
            3: settings.BYTEZ_API_KEY_TIER3,
            4: settings.BYTEZ_API_KEY_TIER4,
            5: settings.BYTEZ_API_KEY_TIER5,
            6: settings.BYTEZ_API_KEY_TIER6,
            7: settings.BYTEZ_API_KEY_TIER7,
            8: settings.BYTEZ_API_KEY_TIER8,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def run_model(model: str, input_data: dict, starting_tier: int) -> Any:
        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None

            # Determine Bytez endpoint format
            # If the payload is OpenAI-style chat completions
            if "messages" in input_data:
                endpoint = input_data.pop("endpoint", "https://api.bytez.com/v1/chat/completions")
            else:
                # Custom Bytez run inference endpoint: https://api.bytez.com/models/v2/{provider}/{model}
                # If model is already fully qualified or formatted
                endpoint = input_data.pop("endpoint", f"https://api.bytez.com/models/v2/{model}")

            for tier in range(starting_tier, 9):
                api_key = BytezProvider.get_api_key(tier)
                if not api_key:
                    continue

                # Bytez authorization uses the API key directly (or Bearer, but direct key is standard)
                headers = {"Authorization": api_key, "Content-Type": "application/json"}

                payload = {"model": model, **input_data}
                try:
                    response = await client.post(endpoint, headers=headers, json=payload)
                    if response.status_code in [401, 402, 403, 429]:
                        print(f"Bytez Tier {tier} exhausted ({response.status_code}). Switching...")
                        last_error = f"Tier {tier}: {response.text}"
                        input_data["endpoint"] = endpoint  # Restore for next loop
                        continue
                    if response.status_code != 200:
                        raise Exception(f"Bytez API error: {response.text}")
                    return response.json()
                except Exception as e:
                    last_error = str(e)
                    print(f"Bytez Tier {tier} failed: {e}")
                    input_data["endpoint"] = endpoint  # Restore for next loop
                    continue
            raise Exception(f"All Bytez tiers exhausted. Last error: {last_error}")
