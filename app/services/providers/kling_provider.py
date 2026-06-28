import httpx
import asyncio
import json
from typing import Any, Optional
from ...core.config import settings


class KlingProvider:
    BASE_URL = "https://api.kling.ai/v1"

    @staticmethod
    def get_credentials(tier: int) -> tuple:
        """Get access and secret key for given tier"""
        credentials = {
            1: (settings.KLING_ACCESS_KEY_TIER1, settings.KLING_SECRET_KEY_TIER1),
            2: (settings.KLING_ACCESS_KEY_TIER2, settings.KLING_SECRET_KEY_TIER2),
            3: (settings.KLING_ACCESS_KEY_TIER3, settings.KLING_SECRET_KEY_TIER3),
            4: (settings.KLING_ACCESS_KEY_TIER4, settings.KLING_SECRET_KEY_TIER4),
            5: (settings.KLING_ACCESS_KEY_TIER5, settings.KLING_SECRET_KEY_TIER5),
            6: (settings.KLING_ACCESS_KEY_TIER6, settings.KLING_SECRET_KEY_TIER6),
            7: (settings.KLING_ACCESS_KEY_TIER7, settings.KLING_SECRET_KEY_TIER7),
            8: (settings.KLING_ACCESS_KEY_TIER8, settings.KLING_SECRET_KEY_TIER8),
        }
        return credentials.get(tier, (None, None))

    @staticmethod
    def get_headers(access_key: str, secret_key: str) -> dict:
        """Generate headers with authentication"""
        return {
            "Authorization": f"Bearer {access_key}",
            "Content-Type": "application/json",
            "X-Secret-Key": secret_key,
        }

    @staticmethod
    async def poll_task_status(
        client: httpx.AsyncClient,
        task_id: str,
        access_key: str,
        secret_key: str,
        max_wait: int = 600,
    ) -> Optional[dict]:
        """Poll Kling API for task completion status"""
        headers = KlingProvider.get_headers(access_key, secret_key)
        url = f"{KlingProvider.BASE_URL}/videos/task/{task_id}"

        start_time = asyncio.get_event_loop().time()
        poll_count = 0

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > max_wait:
                raise TimeoutError(f"Video generation task {task_id} timed out after {max_wait}s")

            try:
                response = await client.get(url, headers=headers, timeout=30.0)

                if response.status_code == 401:
                    raise Exception("Unauthorized - Invalid credentials")

                if response.status_code != 200:
                    raise Exception(f"Status check failed: {response.text}")

                task_data = response.json()
                status = task_data.get("data", {}).get("task_status", "")

                if status == "succeed":
                    return task_data.get("data", {})
                elif status == "failed":
                    error_msg = (
                        task_data.get("data", {})
                        .get("task_result", {})
                        .get("error", "Unknown error")
                    )
                    raise Exception(f"Generation failed: {error_msg}")
                elif status in ["submitted", "processing"]:
                    poll_count += 1
                    # Exponential backoff: 2s, 3s, 5s, 8s, 13s... max 30s
                    wait_time = min(2 ** (poll_count // 3) + 1, 30)
                    await asyncio.sleep(wait_time)
                else:
                    await asyncio.sleep(3)

            except asyncio.TimeoutError:
                await asyncio.sleep(5)
            except Exception as e:
                print(f"Error polling task {task_id}: {e}")
                await asyncio.sleep(5)

    @staticmethod
    async def generate_video(
        input_data: dict, starting_tier: int = 1, task_poll_url: Optional[str] = None
    ) -> Any:
        """
        Generate video using Kling API

        Args:
            input_data: Dict containing video generation parameters
                - prompt: str - Video description
                - mode: str - "text2video" or "image2video" (default: "text2video")
                - image_url: str (optional) - For image2video mode
                - duration: int - Video duration (5, 10 seconds)
                - aspect_ratio: str - "16:9", "9:16", "1:1" (default: "16:9")

            starting_tier: Start from this tier
            task_poll_url: Optional polling URL if task already submitted

        Returns:
            dict with video generation result
        """
        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None

            for tier in range(starting_tier, 9):
                access_key, secret_key = KlingProvider.get_credentials(tier)
                if not access_key or not secret_key:
                    print(f"Kling Tier {tier}: Credentials not configured")
                    continue

                headers = KlingProvider.get_headers(access_key, secret_key)

                try:
                    # Validate input data
                    mode = input_data.get("mode", "text2video")
                    if mode == "text2video" and "prompt" not in input_data:
                        raise ValueError("prompt required for text2video mode")
                    if mode == "image2video" and "image_url" not in input_data:
                        raise ValueError("image_url required for image2video mode")

                    # Submit video generation task
                    endpoint = f"{KlingProvider.BASE_URL}/videos/text2video"
                    if mode == "image2video":
                        endpoint = f"{KlingProvider.BASE_URL}/videos/image2video"

                    # Prepare payload based on mode
                    payload = {
                        "prompt": input_data.get("prompt", ""),
                        "model": input_data.get("model", "kling-v1"),
                        "duration": input_data.get("duration", 5),
                        "aspect_ratio": input_data.get("aspect_ratio", "16:9"),
                        "negative_prompt": input_data.get("negative_prompt", ""),
                        "cfg_scale": input_data.get("cfg_scale", 0.5),
                    }

                    if mode == "image2video":
                        payload["image_url"] = input_data["image_url"]

                    print(f"Kling Tier {tier}: Submitting video generation task...")
                    response = await client.post(endpoint, headers=headers, json=payload)

                    if response.status_code == 401:
                        print(
                            f"Kling Tier {tier} unauthorized ({response.status_code}). Switching to next tier..."
                        )
                        last_error = "Unauthorized credentials"
                        continue

                    if response.status_code == 402:
                        print(
                            f"Kling Tier {tier} insufficient credits ({response.status_code}). Switching to next tier..."
                        )
                        last_error = "Insufficient credits"
                        continue

                    if response.status_code == 429:
                        print(
                            f"Kling Tier {tier} rate limited ({response.status_code}). Switching to next tier..."
                        )
                        last_error = "Rate limited"
                        continue

                    if response.status_code not in [200, 201]:
                        print(f"Kling Tier {tier} request failed: {response.status_code}")
                        last_error = f"Tier {tier}: {response.text}"
                        continue

                    result = response.json()

                    # Check if task was successfully submitted
                    if result.get("code") != 0:
                        error_msg = result.get("message", "Unknown error")
                        print(f"Kling Tier {tier} API error: {error_msg}")
                        last_error = error_msg
                        continue

                    task_id = result.get("data", {}).get("task_id")
                    if not task_id:
                        print(f"Kling Tier {tier} no task_id in response")
                        last_error = "No task_id returned"
                        continue

                    print(f"Kling Tier {tier}: Task {task_id} submitted. Polling for completion...")

                    # Poll for task completion
                    try:
                        task_result = await KlingProvider.poll_task_status(
                            client,
                            task_id,
                            access_key,
                            secret_key,
                            max_wait=600,  # 10 minutes timeout
                        )

                        print(f"Kling Tier {tier}: Video generation completed!")
                        return {
                            "success": True,
                            "task_id": task_id,
                            "tier": tier,
                            "data": task_result,
                            "video_url": (
                                task_result.get("task_result", {}).get("output", [{}])[0].get("url")
                                if task_result
                                else None
                            ),
                        }
                    except TimeoutError as e:
                        print(f"Kling Tier {tier}: {str(e)}")
                        # Return partial result with task_id for later polling
                        return {
                            "success": False,
                            "task_id": task_id,
                            "tier": tier,
                            "status": "processing",
                            "message": "Video generation in progress. Check status using task_id.",
                        }

                except Exception as e:
                    last_error = str(e)
                    print(f"Kling Tier {tier} request error: {e}")
                    continue

            raise Exception(f"All Kling tiers exhausted. Last error: {last_error}")

    @staticmethod
    async def get_task_status(task_id: str, starting_tier: int = 1) -> Any:
        """
        Check status of a submitted video generation task

        Args:
            task_id: Task ID from previous generation request
            starting_tier: Start checking from this tier

        Returns:
            Task status information
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            for tier in range(starting_tier, 9):
                access_key, secret_key = KlingProvider.get_credentials(tier)
                if not access_key or not secret_key:
                    continue

                headers = KlingProvider.get_headers(access_key, secret_key)
                url = f"{KlingProvider.BASE_URL}/videos/task/{task_id}"

                try:
                    response = await client.get(url, headers=headers)

                    if response.status_code == 200:
                        task_data = response.json()
                        return {
                            "success": True,
                            "task_id": task_id,
                            "data": task_data.get("data", {}),
                        }
                    elif response.status_code in [401, 402, 403, 429]:
                        continue

                except Exception as e:
                    print(f"Error checking task status on tier {tier}: {e}")
                    continue

            raise Exception(f"Failed to get task status for {task_id} across all tiers")
