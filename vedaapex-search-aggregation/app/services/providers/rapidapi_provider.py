import httpx
from typing import Any
from ...core.config import settings


class RapidAPIProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.RAPIDAPI_API_KEY_TIER1,
            2: settings.RAPIDAPI_API_KEY_TIER2,
            3: settings.RAPIDAPI_API_KEY_TIER3,
            4: settings.RAPIDAPI_API_KEY_TIER4,
            5: settings.RAPIDAPI_API_KEY_TIER5,
            6: settings.RAPIDAPI_API_KEY_TIER6,
            7: settings.RAPIDAPI_API_KEY_TIER7,
            8: settings.RAPIDAPI_API_KEY_TIER8,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def run_model(model: str, input_data: dict, starting_tier: int) -> Any:
        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None

            # RapidAPI calls must specify the target endpoint and host in input_data
            endpoint = input_data.pop("endpoint", "")
            host = input_data.pop("host", "")
            method = input_data.pop("method", "POST").upper()

            if not endpoint:
                raise Exception(
                    "RapidAPI calls require 'endpoint' to be specified in request parameters"
                )

            for tier in range(starting_tier, 9):
                api_key = RapidAPIProvider.get_api_key(tier)
                if not api_key:
                    continue

                headers = {
                    "X-RapidAPI-Key": api_key,
                    "X-RapidAPI-Host": host,
                    "Content-Type": "application/json",
                }

                try:
                    if method == "GET":
                        response = await client.get(endpoint, headers=headers, params=input_data)
                    else:
                        response = await client.post(endpoint, headers=headers, json=input_data)

                    if response.status_code in [401, 402, 403, 429]:
                        print(
                            f"RapidAPI Tier {tier} exhausted ({response.status_code}). Switching..."
                        )
                        last_error = f"Tier {tier}: {response.text}"
                        continue
                    if response.status_code != 200:
                        raise Exception(f"RapidAPI error: {response.text}")
                    return response.json()
                except Exception as e:
                    last_error = str(e)
                    print(f"RapidAPI Tier {tier} failed: {e}")
                    continue
            raise Exception(f"All RapidAPI tiers exhausted. Last error: {last_error}")
