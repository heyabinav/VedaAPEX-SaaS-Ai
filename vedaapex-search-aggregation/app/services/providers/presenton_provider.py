import httpx
import asyncio
from typing import Any
from ...core.config import settings


class PresentonProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.PRESENTON_API_KEY_TIER1,
            2: settings.PRESENTON_API_KEY_TIER2,
            3: settings.PRESENTON_API_KEY_TIER3,
            4: settings.PRESENTON_API_KEY_TIER4,
            5: settings.PRESENTON_API_KEY_TIER5,
            6: settings.PRESENTON_API_KEY_TIER6,
            7: settings.PRESENTON_API_KEY_TIER7,
            8: settings.PRESENTON_API_KEY_TIER8,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def generate_ppt(prompt: str, starting_tier: int = 1) -> str:
        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None
            for tier in range(starting_tier, 9):
                api_key = PresentonProvider.get_api_key(tier)
                if not api_key:
                    continue
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }

                payload = {"prompt": prompt}

                # Assume standard base URL for presenton
                response = await client.post(
                    "https://api.presenton.ai/v1/ppt/presentation/generate",
                    headers=headers,
                    json=payload,
                )

                if response.status_code in [401, 402, 403, 429]:
                    print(f"Presenton Tier {tier} exhausted ({response.status_code}). Switching...")
                    last_error = f"Tier {tier}: {response.text}"
                    continue

                if response.status_code != 200 and response.status_code != 201:
                    print(f"Presenton Tier {tier} failed ({response.status_code}). Switching...")
                    last_error = f"Tier {tier}: {response.text}"
                    continue

                data = response.json()

                # If URL returned immediately
                if "url" in data and data["url"]:
                    return data["url"]

                if "download_url" in data and data["download_url"]:
                    return data["download_url"]

                # Async flow check (if they use job IDs)
                job_id = data.get("job_id") or data.get("id")
                if not job_id:
                    raise Exception(f"No valid PPT URL or Job ID returned from Presenton: {data}")

                while True:
                    await asyncio.sleep(3)
                    poll_resp = await client.get(
                        f"https://api.presenton.ai/v1/ppt/presentation/{job_id}",
                        headers={"Authorization": f"Bearer {api_key}"},
                    )
                    poll_data = poll_resp.json()
                    status = poll_data.get("status")
                    if status in ["success", "completed", "done"]:
                        return (
                            poll_data.get("url")
                            or poll_data.get("download_url")
                            or poll_data.get("result", {}).get("url")
                        )
                    elif status in ["failed", "error"]:
                        err_msg = str(poll_data.get("error", "")).lower()
                        if "credit" in err_msg or "payment" in err_msg:
                            print(f"Presenton Tier {tier} out of credits during gen. Switching...")
                            last_error = poll_data.get("error")
                            break
                        raise Exception(f"Presenton Generation failed: {poll_data.get('error')}")

            raise Exception(f"All Presenton tiers exhausted. Last error: {last_error}")
