import httpx
from typing import Any
from ...core.config import settings


class OllamaProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.OLLAMA_API_KEY_TIER1,
            2: settings.OLLAMA_API_KEY_TIER2,
            3: settings.OLLAMA_API_KEY_TIER3,
            4: settings.OLLAMA_API_KEY_TIER4,
            5: settings.OLLAMA_API_KEY_TIER5,
            6: settings.OLLAMA_API_KEY_TIER6,
            7: settings.OLLAMA_API_KEY_TIER7,
            8: settings.OLLAMA_API_KEY_TIER8,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def run_model(model: str, input_data: dict, starting_tier: int) -> Any:
        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None
            base_url = settings.OLLAMA_API_BASE or "http://localhost:11434/v1"
            endpoint = input_data.pop("endpoint", f"{base_url}/chat/completions")

            for tier in range(starting_tier, 9):
                api_key = OllamaProvider.get_api_key(tier)
                # Keep calling even if API key is not set, as local Ollama might not require auth
                headers = {"Content-Type": "application/json"}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"

                payload = {"model": model, **input_data}
                try:
                    response = await client.post(endpoint, headers=headers, json=payload)
                    if response.status_code in [401, 402, 403, 429]:
                        print(
                            f"Ollama Tier {tier} exhausted ({response.status_code}). Switching..."
                        )
                        last_error = f"Tier {tier}: {response.text}"
                        continue
                    if response.status_code != 200:
                        raise Exception(f"Ollama API error: {response.text}")
                    return response.json()
                except Exception as e:
                    last_error = str(e)
                    print(f"Ollama Tier {tier} failed: {e}")
                    continue
            raise Exception(f"All Ollama tiers exhausted. Last error: {last_error}")
