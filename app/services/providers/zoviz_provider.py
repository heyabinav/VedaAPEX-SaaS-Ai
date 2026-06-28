import httpx
from typing import Any
from ...core.config import settings


class ZovizProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.ZOVIZ_API_KEY_TIER1,
            2: settings.ZOVIZ_API_KEY_TIER2,
            3: settings.ZOVIZ_API_KEY_TIER3,
            4: settings.ZOVIZ_API_KEY_TIER4,
            5: settings.ZOVIZ_API_KEY_TIER5,
            6: settings.ZOVIZ_API_KEY_TIER6,
            7: settings.ZOVIZ_API_KEY_TIER7,
            8: settings.ZOVIZ_API_KEY_TIER8,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def run_model(input_data: dict, starting_tier: int) -> Any:
        endpoint = "https://api.zoviz.com/api/v1/image-generate"

        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None
            for tier in range(starting_tier, 9):
                api_key = ZovizProvider.get_api_key(tier)
                if not api_key:
                    continue

                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }

                try:
                    response = await client.post(endpoint, headers=headers, json=input_data)

                    if response.status_code in [401, 402, 403, 429]:
                        print(f"Zoviz Tier {tier} exhausted ({response.status_code}). Switching...")
                        last_error = f"Tier {tier}: {response.text}"
                        continue

                    if response.status_code != 200:
                        raise Exception(f"Zoviz API error: {response.text}")

                    res_json = response.json()

                    # Robust extraction of image URL(s)
                    data_obj = res_json.get("data") or {}
                    if isinstance(data_obj, dict):
                        images = data_obj.get("images") or []
                        if isinstance(images, list) and images:
                            return images
                        single_url = data_obj.get("url")
                        if single_url:
                            return [single_url]

                    images = res_json.get("images")
                    if isinstance(images, list) and images:
                        return images

                    url = res_json.get("url")
                    if url:
                        return [url]

                    return res_json
                except Exception as e:
                    last_error = str(e)
                    print(f"Zoviz Tier {tier} request error: {e}")
                    continue

            raise Exception(f"All Zoviz tiers exhausted. Last error: {last_error}")
