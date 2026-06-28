import httpx
from typing import Any, Optional, Tuple
from ...core.config import settings


class LogoDevProvider:
    @staticmethod
    def get_api_key(tier: int) -> Tuple[Optional[str], Optional[str]]:
        publishers = {
            1: settings.LOGODEV_PUBLISHER_KEY_TIER1,
            2: settings.LOGODEV_PUBLISHER_KEY_TIER2,
            3: settings.LOGODEV_PUBLISHER_KEY_TIER3,
            4: settings.LOGODEV_PUBLISHER_KEY_TIER4,
            5: settings.LOGODEV_PUBLISHER_KEY_TIER5,
            6: settings.LOGODEV_PUBLISHER_KEY_TIER6,
            7: settings.LOGODEV_PUBLISHER_KEY_TIER7,
            8: settings.LOGODEV_PUBLISHER_KEY_TIER8,
        }
        secrets = {
            1: settings.LOGODEV_SECRET_KEY_TIER1,
            2: settings.LOGODEV_SECRET_KEY_TIER2,
            3: settings.LOGODEV_SECRET_KEY_TIER3,
            4: settings.LOGODEV_SECRET_KEY_TIER4,
            5: settings.LOGODEV_SECRET_KEY_TIER5,
            6: settings.LOGODEV_SECRET_KEY_TIER6,
            7: settings.LOGODEV_SECRET_KEY_TIER7,
            8: settings.LOGODEV_SECRET_KEY_TIER8,
        }
        return publishers.get(tier), secrets.get(tier)

    @staticmethod
    async def generate_logo(brand_name: str, niche: str, starting_tier: int = 1) -> Any:
        # Note: Logo.dev usually provides a direct URL for a domain,
        # but if the user wants to generate a new logo based on a name,
        # we might be using their logo generation or search API.
        # Assuming the user wants to use logo.dev's API for logo generation/retrieval.

        async with httpx.AsyncClient(timeout=60.0) as client:
            last_error = None

            for tier in range(starting_tier, 9):
                pub_key, sec_key = LogoDevProvider.get_api_key(tier)
                if not pub_key or not sec_key:
                    continue

                # Placeholder for actual logo.dev API endpoint and logic
                # Logo.dev often uses pk_ and sk_ in different ways (query params or headers)
                # Here we assume a search or generation endpoint
                url = f"https://api.logo.dev/search?q={brand_name} {niche}"
                headers = {
                    "Authorization": f"Bearer {sec_key}",
                    "X-Publisher-Key": pub_key,
                }

                try:
                    response = await client.get(url, headers=headers)

                    if response.status_code in [401, 402, 403, 429]:
                        print(
                            f"Logo.dev Tier {tier} exhausted ({response.status_code}). Switching..."
                        )
                        last_error = f"Tier {tier}: {response.text}"
                        continue

                    if response.status_code != 200:
                        raise Exception(f"Logo.dev API error: {response.text}")

                    return response.json()

                except Exception as e:
                    last_error = str(e)
                    print(f"Logo.dev Tier {tier} failed: {e}")
                    continue

            raise Exception(f"All Logo.dev tiers exhausted. Last error: {last_error}")
