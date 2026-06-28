import httpx
from typing import Any
from ...core.config import settings


class HuggingFaceProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.HUGGINGFACE_API_KEY_TIER1,
            2: settings.HUGGINGFACE_API_KEY_TIER2,
            3: settings.HUGGINGFACE_API_KEY_TIER3,
            4: settings.HUGGINGFACE_API_KEY_TIER4,
            5: settings.HUGGINGFACE_API_KEY_TIER5,
            6: settings.HUGGINGFACE_API_KEY_TIER6,
            7: settings.HUGGINGFACE_API_KEY_TIER7,
            8: settings.HUGGINGFACE_API_KEY_TIER8,
            9: settings.HUGGINGFACE_API_KEY_TIER9,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def run_model(model: str, input_data: dict, starting_tier: int = 1) -> Any:
        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None

            # Determine Hugging Face endpoint
            # Hugging Face supports OpenAI-compatible chat completions for some models
            if "messages" in input_data:
                endpoint = input_data.pop(
                    "endpoint",
                    f"https://api-inference.huggingface.co/models/{model}/v1/chat/completions",
                )
            else:
                endpoint = input_data.pop(
                    "endpoint", f"https://api-inference.huggingface.co/models/{model}"
                )

            for tier in range(starting_tier, 10):
                api_key = HuggingFaceProvider.get_api_key(tier)
                if not api_key:
                    continue

                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }

                try:
                    response = await client.post(endpoint, headers=headers, json=input_data)

                    if response.status_code in [401, 402, 403, 429]:
                        print(
                            f"Hugging Face Tier {tier} exhausted ({response.status_code}). Switching..."
                        )
                        last_error = f"Tier {tier}: {response.text}"
                        continue

                    if response.status_code == 503:
                        print(
                            f"Hugging Face Model {model} is loading (503). Retrying with next tier..."
                        )
                        last_error = f"Tier {tier}: {response.text}"
                        continue

                    if response.status_code != 200:
                        raise Exception(f"Hugging Face API error: {response.text}")

                    # Return JSON or raw content based on content-type
                    if "application/json" in response.headers.get("content-type", ""):
                        return response.json()
                    return response.content

                except Exception as e:
                    last_error = str(e)
                    print(f"Hugging Face Tier {tier} failed: {e}")
                    continue

            raise Exception(f"All Hugging Face tiers exhausted. Last error: {last_error}")
