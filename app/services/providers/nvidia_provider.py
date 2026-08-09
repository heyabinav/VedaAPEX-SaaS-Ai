import httpx
from typing import Any
from ...core.config import settings


class NVIDIAProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.NVIDIA_API_KEY_TIER1,
            2: settings.NVIDIA_API_KEY_TIER2,
            3: settings.NVIDIA_API_KEY_TIER3,
            4: settings.NVIDIA_API_KEY_TIER4,
            5: settings.NVIDIA_API_KEY_TIER5,
            6: settings.NVIDIA_API_KEY_TIER6,
            7: settings.NVIDIA_API_KEY_TIER7,
            8: settings.NVIDIA_API_KEY_TIER8,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def run_model(model: str, input_data: dict, starting_tier: int) -> Any:
        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None
            default_endpoint = "https://integrate.api.nvidia.com/v1/chat/completions"

            # Auto-switch endpoint to images if that's the likely payload type
            if (
                "prompt" in input_data
                and "messages" not in input_data
                and "endpoint" not in input_data
            ):
                # If there's an image model configured, NVIDIA API catalog supports it
                default_endpoint = "https://integrate.api.nvidia.com/v1/images/generations"

            endpoint = input_data.pop("endpoint", default_endpoint)

            for tier in range(starting_tier, 9):
                api_key = NVIDIAProvider.get_api_key(tier)
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
                        print(
                            f"[NVIDIA] Tier {tier} exhausted ({response.status_code}). Switching..."
                        )
                        last_error = f"Tier {tier}: {response.text}"
                        input_data["endpoint"] = endpoint  # Restore for next loop
                        continue
                    if response.status_code != 200:
                        raise Exception(
                            f"[NVIDIA] API error (tier={tier}): {response.status_code} {response.text}"
                        )
                    return response.json()
                except Exception as e:
                    last_error = str(e)
                    print(f"[NVIDIA] Tier {tier} failed: {e}")
                    input_data["endpoint"] = endpoint  # Restore for next loop
                    continue
            raise Exception(f"[NVIDIA] All tiers exhausted. Last error: {last_error}")
