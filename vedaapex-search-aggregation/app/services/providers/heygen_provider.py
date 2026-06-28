import httpx
import asyncio
from typing import Any
from ...core.config import settings


class HeyGenProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.HEYGEN_API_KEY_TIER1,
            2: settings.HEYGEN_API_KEY_TIER2,
            3: settings.HEYGEN_API_KEY_TIER3,
            4: settings.HEYGEN_API_KEY_TIER4,
            5: settings.HEYGEN_API_KEY_TIER5,
            6: settings.HEYGEN_API_KEY_TIER6,
            7: settings.HEYGEN_API_KEY_TIER7,
            8: settings.HEYGEN_API_KEY_TIER8,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def run_model(input_data: dict, starting_tier: int) -> Any:
        endpoint = "https://api.heygen.com/v2/video/generate"

        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None
            for tier in range(starting_tier, 9):
                api_key = HeyGenProvider.get_api_key(tier)
                if not api_key:
                    continue

                headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}

                try:
                    response = await client.post(endpoint, headers=headers, json=input_data)

                    if response.status_code in [401, 402, 403, 429]:
                        print(
                            f"HeyGen Tier {tier} exhausted/failed ({response.status_code}). Switching to next tier..."
                        )
                        last_error = f"Tier {tier}: {response.text}"
                        continue

                    if response.status_code != 200:
                        raise Exception(f"HeyGen API error: {response.text}")

                    result = response.json()

                    data = result.get("data")
                    if not data or "video_id" not in data:
                        raise Exception(f"Invalid HeyGen response: {result}")

                    video_id = data["video_id"]
                    print(f"HeyGen video generation initiated (ID: {video_id}). Polling status...")

                    # Poll for status
                    status_endpoint = (
                        f"https://api.heygen.com/v1/video_status.get?video_id={video_id}"
                    )

                    # Poll up to 60 times (5 seconds interval = 5 minutes max)
                    for _ in range(60):
                        await asyncio.sleep(5)
                        status_response = await client.get(status_endpoint, headers=headers)
                        if status_response.status_code != 200:
                            print(f"Status check failed: {status_response.text}")
                            continue

                        res_json = status_response.json()
                        status_data = res_json.get("data", {})
                        # If data is nested or direct
                        if not status_data:
                            # Try getting from root
                            status_data = res_json

                        status = status_data.get("status")

                        if status == "completed" or status_data.get("video_url"):
                            video_url = status_data.get("video_url")
                            return video_url
                        elif status == "failed":
                            raise Exception(
                                f"HeyGen video generation failed: {status_data.get('error') or status_data}"
                            )

                    raise Exception("HeyGen video generation timed out.")
                except Exception as e:
                    last_error = str(e)
                    print(f"HeyGen Tier {tier} request error: {e}")
                    continue

            raise Exception(f"All HeyGen tiers exhausted. Last error: {last_error}")
