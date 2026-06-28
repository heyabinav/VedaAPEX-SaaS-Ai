import httpx
import asyncio
from typing import Any
from ...core.config import settings


class TwoslidesProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.TWOSLIDES_API_KEY_TIER1,
            2: settings.TWOSLIDES_API_KEY_TIER2,
            3: settings.TWOSLIDES_API_KEY_TIER3,
            4: settings.TWOSLIDES_API_KEY_TIER4,
            5: settings.TWOSLIDES_API_KEY_TIER5,
            6: settings.TWOSLIDES_API_KEY_TIER6,
            7: settings.TWOSLIDES_API_KEY_TIER7,
            8: settings.TWOSLIDES_API_KEY_TIER8,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def generate_ppt(prompt: str, starting_tier: int = 1) -> str:
        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None
            for tier in range(starting_tier, 9):
                api_key = TwoslidesProvider.get_api_key(tier)
                if not api_key:
                    continue
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }

                # We use the generate endpoint
                payload = {
                    "prompt": prompt,
                    "mode": "async",  # Safer for larger generation times
                }

                response = await client.post(
                    "https://2slides.com/api/v1/slides/generate",
                    headers=headers,
                    json=payload,
                )

                if response.status_code in [401, 402, 403, 429]:
                    print(f"2Slides Tier {tier} exhausted ({response.status_code}). Switching...")
                    last_error = f"Tier {tier}: {response.text}"
                    continue

                if response.status_code != 200 and response.status_code != 201:
                    print(f"2Slides Tier {tier} failed ({response.status_code}). Switching...")
                    last_error = f"Tier {tier}: {response.text}"
                    continue

                data = response.json()

                # If sync mode works or URL returned immediately
                if "url" in data and data["url"]:
                    return data["url"]

                # Async flow
                job_id = data.get("jobId")
                if not job_id:
                    raise Exception(f"No jobId returned from 2Slides: {data}")

                while True:
                    await asyncio.sleep(3)
                    poll_resp = await client.get(
                        f"https://2slides.com/api/v1/jobs/{job_id}",
                        headers={"Authorization": f"Bearer {api_key}"},
                    )
                    poll_data = poll_resp.json()
                    status = poll_data.get("status")
                    if status == "success":
                        return poll_data.get("url") or poll_data.get("result", {}).get("url")
                    elif status == "failed":
                        err_msg = str(poll_data.get("error", "")).lower()
                        if "credit" in err_msg or "payment" in err_msg:
                            print(f"2Slides Tier {tier} out of credits during gen. Switching...")
                            last_error = poll_data.get("error")
                            break  # Break the while loop, continue the for loop to next tier
                        raise Exception(f"2Slides Generation failed: {poll_data.get('error')}")

            raise Exception(f"All 2Slides tiers exhausted. Last error: {last_error}")
