import httpx
from typing import Any
from ...core.config import settings


class ImagenartProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.IMAGENART_API_KEY_TIER1,
            2: settings.IMAGENART_API_KEY_TIER2,
            3: settings.IMAGENART_API_KEY_TIER3,
            4: settings.IMAGENART_API_KEY_TIER4,
            5: settings.IMAGENART_API_KEY_TIER5,
            6: settings.IMAGENART_API_KEY_TIER6,
            7: settings.IMAGENART_API_KEY_TIER7,
            8: settings.IMAGENART_API_KEY_TIER8,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def run_model(input_data: dict, starting_tier: int) -> Any:
        endpoint = "https://www.imagine.art/gen-api"

        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None
            for tier in range(starting_tier, 9):
                api_key = ImagenartProvider.get_api_key(tier)
                if not api_key:
                    continue

                # The key already includes "Bearer " based on how it was saved in .env
                # Ensure we handle it gracefully if it doesn't
                auth_header = (
                    api_key if api_key.lower().startswith("bearer") else f"Bearer {api_key}"
                )

                headers = {
                    "Authorization": auth_header,
                    "Content-Type": "application/json",
                }

                try:
                    response = await client.post(endpoint, headers=headers, json=input_data)

                    if response.status_code in [401, 402, 403, 429]:
                        print(
                            f"Imagenart Tier {tier} exhausted/failed ({response.status_code}). Switching to next tier..."
                        )
                        last_error = f"Tier {tier}: {response.text}"
                        continue

                    if response.status_code != 200:
                        raise Exception(f"Imagenart API error: {response.text}")

                    return response.json()
                except Exception as e:
                    last_error = str(e)
                    print(f"Imagenart Tier {tier} request error: {e}")
                    continue

            raise Exception(f"All Imagenart tiers exhausted. Last error: {last_error}")
