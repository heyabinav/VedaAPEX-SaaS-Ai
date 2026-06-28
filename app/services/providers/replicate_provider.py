import httpx
import asyncio
from typing import Any
from ...core.config import settings


class ReplicateProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.REPLICATE_API_KEY_TIER1,
            2: settings.REPLICATE_API_KEY_TIER2,
            3: settings.REPLICATE_API_KEY_TIER3,
            4: settings.REPLICATE_API_KEY_TIER4,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def run_model(owner: str, name: str, input_data: dict, starting_tier: int) -> Any:
        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None
            for tier in range(starting_tier, 5):
                api_key = ReplicateProvider.get_api_key(tier)
                if not api_key:
                    continue
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "Prefer": "wait",
                }
                response = await client.post(
                    f"https://api.replicate.com/v1/models/{owner}/{name}/predictions",
                    headers=headers,
                    json={"input": input_data},
                )

                if response.status_code in [401, 402, 403, 429]:
                    print(f"Replicate Tier {tier} exhausted ({response.status_code}). Switching...")
                    last_error = f"Tier {tier}: {response.text}"
                    continue
                if response.status_code != 201:
                    raise Exception(f"Replicate API error: {response.text}")

                prediction = response.json()
                while prediction["status"] not in ["succeeded", "failed", "canceled"]:
                    await asyncio.sleep(2)
                    poll_resp = await client.get(
                        prediction["urls"]["get"],
                        headers={"Authorization": f"Bearer {api_key}"},
                    )
                    prediction = poll_resp.json()

                if prediction["status"] == "failed":
                    err_msg = str(prediction.get("error", "")).lower()
                    if "credit" in err_msg or "payment" in err_msg or "unauthorized" in err_msg:
                        print(f"Replicate Tier {tier} out of credits during gen. Switching...")
                        last_error = prediction.get("error")
                        continue
                    raise Exception(f"Generation failed: {prediction.get('error')}")
                return prediction["output"]
            raise Exception(f"All Replicate tiers exhausted. Last error: {last_error}")
