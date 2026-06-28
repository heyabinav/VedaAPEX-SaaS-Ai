import httpx
from typing import Any
from ...core.config import settings


class CloudflareProvider:
    @staticmethod
    def get_api_key(tier: int) -> tuple[str, str]:
        keys = {
            1: (
                settings.CLOUDFLARE_API_KEY_TIER1,
                settings.CLOUDFLARE_ACCOUNT_ID_TIER1,
            ),
            2: (
                settings.CLOUDFLARE_API_KEY_TIER2,
                settings.CLOUDFLARE_ACCOUNT_ID_TIER2,
            ),
            3: (
                settings.CLOUDFLARE_API_KEY_TIER3,
                settings.CLOUDFLARE_ACCOUNT_ID_TIER3,
            ),
            4: (
                settings.CLOUDFLARE_API_KEY_TIER4,
                settings.CLOUDFLARE_ACCOUNT_ID_TIER4,
            ),
            5: (
                settings.CLOUDFLARE_API_KEY_TIER5,
                settings.CLOUDFLARE_ACCOUNT_ID_TIER5,
            ),
            6: (
                settings.CLOUDFLARE_API_KEY_TIER6,
                settings.CLOUDFLARE_ACCOUNT_ID_TIER6,
            ),
            7: (
                settings.CLOUDFLARE_API_KEY_TIER7,
                settings.CLOUDFLARE_ACCOUNT_ID_TIER7,
            ),
            8: (
                settings.CLOUDFLARE_API_KEY_TIER8,
                settings.CLOUDFLARE_ACCOUNT_ID_TIER8,
            ),
        }
        return keys.get(tier) or ("", "")

    @staticmethod
    async def run_model(model: str, input_data: dict, starting_tier: int) -> Any:
        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None
            for tier in range(starting_tier, 9):
                api_key, account_id = CloudflareProvider.get_api_key(tier)
                if not api_key or not account_id:
                    continue
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }

                endpoint = (
                    f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
                )

                response = await client.post(endpoint, headers=headers, json=input_data)

                if response.status_code in [401, 402, 403, 429]:
                    print(
                        f"Cloudflare Tier {tier} exhausted ({response.status_code}). Switching..."
                    )
                    last_error = f"Tier {tier}: {response.text}"
                    continue
                if response.status_code != 200:
                    raise Exception(f"Cloudflare API error: {response.text}")

                # Cloudflare sometimes returns binary image data, sometimes json
                try:
                    return response.json()
                except:
                    return response.content
            raise Exception(f"All Cloudflare tiers exhausted. Last error: {last_error}")
