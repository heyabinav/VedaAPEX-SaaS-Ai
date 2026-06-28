import httpx
import asyncio
import base64
from typing import Any
from ...core.config import settings


class DIDProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.DID_API_KEY_TIER1,
            2: settings.DID_API_KEY_TIER2,
            3: settings.DID_API_KEY_TIER3,
            4: settings.DID_API_KEY_TIER4,
            5: settings.DID_API_KEY_TIER5,
            6: settings.DID_API_KEY_TIER6,
            7: settings.DID_API_KEY_TIER7,
            8: settings.DID_API_KEY_TIER8,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def run_model(input_data: dict, starting_tier: int) -> Any:
        endpoint = "https://api.d-id.com/talks"

        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None
            for tier in range(starting_tier, 9):
                api_key = DIDProvider.get_api_key(tier)
                if not api_key:
                    continue

                # Basic Auth encoding
                auth_bytes = api_key.encode("utf-8")
                auth_b64 = base64.b64encode(auth_bytes).decode("utf-8")

                headers = {
                    "Authorization": f"Basic {auth_b64}",
                    "Content-Type": "application/json",
                }

                try:
                    response = await client.post(endpoint, headers=headers, json=input_data)

                    if response.status_code in [401, 402, 403, 429]:
                        print(
                            f"D-ID Tier {tier} exhausted/failed ({response.status_code}). Switching to next tier..."
                        )
                        last_error = f"Tier {tier}: {response.text}"
                        continue

                    if response.status_code not in [200, 201]:
                        raise Exception(f"D-ID API error: {response.text}")

                    result = response.json()
                    talk_id = result.get("id")
                    if not talk_id:
                        raise Exception(f"Invalid D-ID response: {result}")

                    print(f"D-ID video generation initiated (ID: {talk_id}). Polling status...")

                    # Poll for status
                    status_endpoint = f"https://api.d-id.com/talks/{talk_id}"

                    # Poll up to 60 times (5 seconds interval = 5 minutes max)
                    for _ in range(60):
                        await asyncio.sleep(5)
                        status_response = await client.get(status_endpoint, headers=headers)
                        if status_response.status_code != 200:
                            print(f"Status check failed: {status_response.text}")
                            continue

                        res_json = status_response.json()
                        status = res_json.get("status")

                        if status == "done":
                            video_url = res_json.get("result_url")
                            return video_url
                        elif status == "error":
                            raise Exception(
                                f"D-ID video generation failed: {res_json.get('error') or res_json}"
                            )

                    raise Exception("D-ID video generation timed out.")
                except Exception as e:
                    last_error = str(e)
                    print(f"D-ID Tier {tier} request error: {e}")
                    continue

            raise Exception(f"All D-ID tiers exhausted. Last error: {last_error}")
