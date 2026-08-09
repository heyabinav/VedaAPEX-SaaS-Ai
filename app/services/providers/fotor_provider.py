import httpx
import asyncio
from typing import Any
from ...core.config import settings


class FotorProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.FOTOR_API_KEY_TIER1,
            2: settings.FOTOR_API_KEY_TIER2,
            3: settings.FOTOR_API_KEY_TIER3,
            4: settings.FOTOR_API_KEY_TIER4,
            5: settings.FOTOR_API_KEY_TIER5,
            6: settings.FOTOR_API_KEY_TIER6,
            7: settings.FOTOR_API_KEY_TIER7,
            8: settings.FOTOR_API_KEY_TIER8,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def run_model(input_data: dict, starting_tier: int) -> Any:
        submit_endpoint = "https://api-b.fotor.com/v1/aiart/generate"

        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None
            for tier in range(starting_tier, 9):
                api_key = FotorProvider.get_api_key(tier)
                if not api_key:
                    continue

                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }

                try:
                    # Submit the task to Fotor
                    response = await client.post(submit_endpoint, headers=headers, json=input_data)

                    if response.status_code in [401, 402, 403, 429]:
                        print(f"Fotor Tier {tier} exhausted ({response.status_code}). Switching...")
                        last_error = f"Tier {tier}: {response.text}"
                        continue

                    if response.status_code != 200:
                        raise Exception(f"Fotor API error: {response.text}")

                    res_json = response.json()
                    data = res_json.get("data") or {}
                    task_id = data.get("taskId") or data.get("task_id")
                    if not task_id:
                        raise Exception(f"Fotor response missing task ID: {res_json}")

                    # Poll for task completion
                    status_endpoint = f"https://api-b.fotor.com/v1/aiart/tasks/{task_id}"
                    max_attempts = 45  # Poll for up to 90 seconds
                    completed = False
                    result_url = None

                    for attempt in range(max_attempts):
                        await asyncio.sleep(2)
                        status_response = await client.get(status_endpoint, headers=headers)

                        if status_response.status_code != 200:
                            print(
                                f"Fotor status poll failed (HTTP {status_response.status_code}), retrying..."
                            )
                            continue

                        status_data = status_response.json()
                        inner_data = status_data.get("data") or {}
                        status_val = inner_data.get("status")

                        # status: 1 = completed, 0 = pending/processing
                        if status_val == 1:
                            result_url = inner_data.get("resultUrl")
                            if not result_url:
                                # Fallback check for avatar/list results
                                avatar_result = inner_data.get("avatarResult")
                                if (
                                    avatar_result
                                    and isinstance(avatar_result, list)
                                    and len(avatar_result) > 0
                                ):
                                    images = avatar_result[0].get("images")
                                    if images and isinstance(images, list) and len(images) > 0:
                                        result_url = images[0].get("url")

                            if result_url:
                                completed = True
                                break
                            else:
                                raise Exception(
                                    f"Fotor task completed but no output URL found: {status_data}"
                                )
                        elif status_val == 0:
                            # Still processing
                            continue
                        else:
                            # Failed/canceled or other error status
                            msg = (
                                status_data.get("msg")
                                or status_data.get("message")
                                or f"status {status_val}"
                            )
                            raise Exception(f"Fotor task failed: {msg}")

                    if not completed:
                        raise Exception(
                            f"Fotor task timed out after polling for {max_attempts * 2} seconds"
                        )

                    return [result_url]

                except Exception as e:
                    last_error = str(e)
                    print(f"Fotor Tier {tier} request error: {e}")
                    continue

            raise Exception(f"All Fotor tiers exhausted. Last error: {last_error}")
