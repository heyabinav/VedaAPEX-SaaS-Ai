import httpx
from typing import Any
from ...core.config import settings


class GetImgProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.GETIMG_API_KEY_TIER1,
            2: settings.GETIMG_API_KEY_TIER2,
            3: settings.GETIMG_API_KEY_TIER3,
            4: settings.GETIMG_API_KEY_TIER4,
            5: settings.GETIMG_API_KEY_TIER5,
            6: settings.GETIMG_API_KEY_TIER6,
            7: settings.GETIMG_API_KEY_TIER7,
            8: settings.GETIMG_API_KEY_TIER8,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def run_model(model: str, input_data: dict, starting_tier: int) -> Any:
        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None
            for tier in range(starting_tier, 9):
                api_key = GetImgProvider.get_api_key(tier)
                if not api_key:
                    continue
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                }
                endpoint_url = input_data.pop(
                    "endpoint", "https://api.getimg.ai/v1/essential/text-to-image"
                )

                payload = {"model": model, **input_data}
                response = await client.post(endpoint_url, headers=headers, json=payload)

                if response.status_code in [401, 402, 403, 429]:
                    print(f"GetImg.ai Tier {tier} exhausted ({response.status_code}). Switching...")
                    last_error = f"Tier {tier}: {response.text}"
                    input_data["endpoint"] = endpoint_url  # Restore for next loop
                    continue
                if response.status_code != 200:
                    raise Exception(f"GetImg.ai API error: {response.text}")
                return response.json()
            raise Exception(f"All GetImg.ai tiers exhausted. Last error: {last_error}")
