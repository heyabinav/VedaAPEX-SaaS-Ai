"""Serper Search Provider - Google-style web search results.

Provides real-time web search results using the Serper API.
Includes tier-based key rotation and quota exhaustion handling.
"""

import httpx
import logging
from typing import Any, Optional, Dict, List

from app.core.config import settings

logger = logging.getLogger("services.providers.serper_provider")


class SerperProvider:
    """Serper web search provider."""
    
    SERPER_API_URL = "https://google.serper.dev/search"
    
    @staticmethod
    def get_api_key(tier: int = 1) -> str:
        """Get Serper API key for specified tier."""
        if tier == 1 and settings.SERPER_API_KEY:
            return settings.SERPER_API_KEY
        keys = {
            1: settings.SERPER_API_KEY_TIER1,
            2: settings.SERPER_API_KEY_TIER2,
            3: settings.SERPER_API_KEY_TIER3,
            4: settings.SERPER_API_KEY_TIER4,
            5: settings.SERPER_API_KEY_TIER5,
            6: settings.SERPER_API_KEY_TIER6,
            7: settings.SERPER_API_KEY_TIER7,
            8: settings.SERPER_API_KEY_TIER8,
        }
        return keys.get(tier) or ""
    
    @staticmethod
    def is_available() -> bool:
        """Check if Serper API is configured."""
        for tier in range(1, 9):
            if SerperProvider.get_api_key(tier):
                return True
        return False
    
    @staticmethod
    async def search(
        query: str,
        starting_tier: int = 1,
        num_results: int = 10,
    ) -> Dict[str, Any]:
        """
        Perform web search using Serper API.
        
        Args:
            query: Search query
            starting_tier: Starting tier for key rotation
            num_results: Number of results to return
            
        Returns:
            Dict with normalized search results
            
        Raises:
            Exception: If all tiers exhausted or API error
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            last_error = None
            
            for tier in range(starting_tier, 9):
                api_key = SerperProvider.get_api_key(tier)
                if not api_key:
                    continue
                
                try:
                    headers = {
                        "X-API-KEY": api_key,
                        "Content-Type": "application/json",
                    }
                    
                    payload = {
                        "q": query,
                        "num": num_results,
                        "gl": "us",  # Global location
                        "hl": "en",  # English language
                    }
                    
                    response = await client.post(
                        SerperProvider.SERPER_API_URL,
                        json=payload,
                        headers=headers,
                    )
                    
                    # Check for quota/rate limit errors
                    if response.status_code in [401, 402, 403, 429]:
                        logger.warning(
                            "Serper tier %d exhausted/rate-limited: %s",
                            tier,
                            response.status_code,
                        )
                        last_error = f"Tier {tier}: HTTP {response.status_code}"
                        continue
                    
                    if response.status_code != 200:
                        error_text = response.text[:200]
                        logger.warning(
                            "Serper tier %d error: HTTP %s - %s",
                            tier,
                            response.status_code,
                            error_text,
                        )
                        last_error = f"Tier {tier}: {error_text}"
                        continue
                    
                    data = response.json()
                    logger.debug(
                        "Serper tier %d success for query: %s",
                        tier,
                        query,
                    )
                    
                    return SerperProvider._normalize_results(data, tier)
                    
                except httpx.TimeoutException as e:
                    logger.warning("Serper tier %d timeout: %s", tier, str(e))
                    last_error = f"Tier {tier}: Timeout"
                    continue
                    
                except Exception as e:
                    logger.warning("Serper tier %d exception: %s", tier, str(e))
                    last_error = str(e)
                    continue
            
            # All tiers exhausted
            error_msg = f"All Serper tiers exhausted. Last error: {last_error}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    @staticmethod
    def _normalize_results(data: Dict[str, Any], tier: int) -> Dict[str, Any]:
        """Normalize Serper API response to standard format."""
        results = []
        
        # Extract organic search results
        for item in data.get("organic", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "position": item.get("position", 0),
                "provider": "serper",
                "tier": tier,
            })
        
        # Extract answer box if present (high-priority result)
        answer_box = data.get("answerBox", {})
        if answer_box:
            results.insert(0, {
                "title": answer_box.get("title", "Answer"),
                "url": answer_box.get("source", ""),
                "snippet": answer_box.get("answer", answer_box.get("snippet", "")),
                "position": 0,
                "is_answer_box": True,
                "provider": "serper",
                "tier": tier,
            })
        
        # Extract knowledge graph if present (high-priority result)
        knowledge_graph = data.get("knowledgeGraph", {})
        if knowledge_graph:
            results.insert(0, {
                "title": knowledge_graph.get("title", "Knowledge"),
                "url": knowledge_graph.get("website", ""),
                "snippet": knowledge_graph.get("description", ""),
                "position": 0,
                "is_knowledge_graph": True,
                "provider": "serper",
                "tier": tier,
            })
        
        return {
            "success": True,
            "query": data.get("searchParameters", {}).get("q", ""),
            "results": results,
            "result_count": len(results),
            "provider": "serper",
            "tier_used": tier,
        }
