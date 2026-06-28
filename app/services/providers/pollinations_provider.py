import httpx
from typing import Any
from ...core.config import settings


class PollinationsProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {1: settings.POLLINATIONS_API_KEY_TIER1}
        return keys.get(tier) or ""

    @staticmethod
    async def run_model(model: str, input_data: dict, starting_tier: int) -> Any:
        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None
            for tier in range(starting_tier, 2):
                api_key = PollinationsProvider.get_api_key(tier)
                headers = {}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"

                prompt = input_data.get("prompt", "")
                # Pollinations accepts GET/POST to /prompt/{prompt}
                # We can also pass model as a query param or in JSON payload
                payload = {"prompt": prompt, "model": model, **input_data}

                response = await client.post(
                    "https://image.pollinations.ai/", headers=headers, json=payload
                )

                if response.status_code in [401, 402, 403, 429]:
                    print(
                        f"Pollinations Tier {tier} exhausted ({response.status_code}). Switching..."
                    )
                    last_error = f"Tier {tier}: {response.text}"
                    continue

                if response.status_code != 200:
                    raise Exception(f"Pollinations API error: {response.text}")

                # Usually returns direct image bytes
                return response.content

            raise Exception(f"All Pollinations tiers exhausted. Last error: {last_error}")
