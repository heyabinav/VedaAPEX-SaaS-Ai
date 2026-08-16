import httpx
from typing import Any
from ...core.config import settings


class TavilyProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        if tier == 1 and settings.TAVILY_API_KEY:
            return settings.TAVILY_API_KEY
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
    def is_available() -> bool:
        for tier in range(1, 9):
            if TavilyProvider.get_api_key(tier):
                return True
        return False

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
                            "search_depth": "advanced",
                        },
                    )

                    if response.status_code in [401, 402, 403, 429]:
                        print(f"Tavily Tier {tier} exhausted. Switching...")
                        last_error = f"Tier {tier}: {response.text}"
                        continue

                    if response.status_code != 200:
                        raise Exception(f"Tavily API error: {response.text}")

                    payload = response.json()
                    results = payload.get("results", []) if isinstance(payload, dict) else []
                    normalized = {
                        "success": True,
                        "query": query,
                        "results": [
                            {
                                "title": item.get("title", ""),
                                "url": item.get("url", ""),
                                "snippet": item.get("content") or item.get("snippet", ""),
                                "score": item.get("score", 1.0),
                                "provider": "tavily",
                                "tier": tier,
                            }
                            for item in results
                        ],
                        "result_count": len(results),
                        "provider": "tavily",
                        "tier_used": tier,
                    }
                    return normalized
                except Exception as e:
                    last_error = str(e)
                    continue
            raise Exception(f"All Tavily tiers exhausted. Last error: {last_error}")
