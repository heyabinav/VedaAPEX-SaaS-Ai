import httpx
from typing import Any
from ...core.config import settings


class TavilyProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.TAVILY_API_KEY_TIER1,
            2: settings.TAVILY_API_KEY_TIER2,
            3: settings.TAVILY_API_KEY_TIER3,
            4: settings.TAVILY_API_KEY_TIER4,
            5: settings.TAVILY_API_KEY_TIER5,
            6: settings.TAVILY_API_KEY_TIER6,
            7: settings.TAVILY_API_KEY_TIER7,
            8: settings.TAVILY_API_KEY_TIER8,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def search(query: str, starting_tier: int = 1) -> Any:
        async with httpx.AsyncClient(timeout=30.0) as client:
            last_error = None
            for tier in range(starting_tier, 9):
                api_key = TavilyProvider.get_api_key(tier)
                if not api_key:
                    continue

                try:
                    response = await client.post(
                        "https://api.tavily.com/search",
                        json={
                            "api_key": api_key,
                            "query": query,
                            "search_depth": "smart",
                        },
                    )

                    if response.status_code in [401, 402, 403, 429]:
                        print(f"Tavily Tier {tier} exhausted. Switching...")
                        last_error = f"Tier {tier}: {response.text}"
                        continue

                    if response.status_code != 200:
                        raise Exception(f"Tavily API error: {response.text}")

                    return response.json()
                except Exception as e:
                    last_error = str(e)
                    continue
            raise Exception(f"All Tavily tiers exhausted. Last error: {last_error}")
