"""Unified Web Search Router - Intelligent provider orchestration.

Manages web search requests with smart provider selection, quota exhaustion
handling, and graceful fallback to lower-priority providers.

Provider hierarchy:
1. Serper (Google-style results, good for general searches)
2. Tavily (Research-focused, semantic search)
3. Python fallback (DuckDuckGo via ddgs library)
"""

import logging
from typing import Any, Dict, Optional

from app.services.search_decision_engine import SearchDecisionEngine, SearchRequestType
from app.services.providers.serper_provider import SerperProvider
from app.services.providers.tavily_provider import TavilyProvider
from app.services.providers.python_search_provider import PythonSearchProvider

logger = logging.getLogger("services.search_router")


class SearchRouter:
    """Intelligent web search router with fallback management."""
    
    @staticmethod
    async def search(
        query: str,
        request_type: Optional[SearchRequestType] = None,
        num_results: int = 10,
    ) -> Optional[Dict[str, Any]]:
        """
        Perform intelligent web search with automatic fallback.
        
        Determines the best provider based on request type and availability.
        Implements quota exhaustion handling with automatic fallback chain.
        
        Args:
            query: Search query
            request_type: Classification of search type (auto-detected if None)
            num_results: Number of results to return
            
        Returns:
            Normalized search results dict, or None if all providers fail
            
        Provider selection logic:
        - RESEARCH queries: Try Tavily first (semantic), then Serper, then Python
        - Other queries: Try Serper first (fast), then Tavily, then Python
        - Always fallback to Python provider if API-based providers unavailable
        """
        if not query or not query.strip():
            logger.warning("Empty search query provided")
            return None
        
        # Auto-classify if not provided
        if request_type is None:
            request_type = SearchDecisionEngine.classify_request(query)
        
        logger.info(
            "Search router: query='%s' type=%s",
            query[:80],
            request_type,
        )
        
        # Determine provider order based on request type
        provider_order = SearchRouter._get_provider_order(request_type)
        
        logger.debug("Provider order for %s: %s", request_type, provider_order)
        
        # Try providers in order
        for provider_name in provider_order:
            try:
                if provider_name == "serper":
                    if SerperProvider.is_available():
                        result = await SerperProvider.search(query, num_results=num_results)
                        if result and result.get("result_count", 0) > 0:
                            logger.info("Search succeeded with Serper: %d results", result.get("result_count", 0))
                            return result
                        logger.debug("Serper returned no results, trying next provider")
                
                elif provider_name == "tavily":
                    if TavilyProvider.is_available():
                        result = await TavilyProvider.search(query)
                        if result and result.get("results"):
                            logger.info("Search succeeded with Tavily: %d results", len(result.get("results", [])))
                            return result
                        logger.debug("Tavily returned no results, trying next provider")
                
                elif provider_name == "python":
                    if PythonSearchProvider.is_available():
                        result = await PythonSearchProvider.search(query, num_results=num_results)
                        if result and result.get("result_count", 0) > 0:
                            logger.info("Search succeeded with Python fallback: %d results", result.get("result_count", 0))
                            return result
                        logger.debug("Python fallback returned no results")
            
            except Exception as e:
                logger.warning(
                    "Provider %s failed for query '%s': %s",
                    provider_name,
                    query[:50],
                    str(e)[:100],
                )
                continue
        
        logger.error("All search providers failed for query: %s", query[:80])
        return None
    
    @staticmethod
    async def search_with_decision(
        query: str,
        num_results: int = 10,
        force_search: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Perform search only if necessary based on query classification.
        
        This is the main entry point for AI agents. It prevents unnecessary
        API calls by checking if the query actually needs web search.
        
        Args:
            query: User's question/message
            num_results: Number of results to return if search is needed
            force_search: Force search even if not classified as needing it
            
        Returns:
            Normalized search results, or None if search not needed/failed
        """
        request_type = SearchDecisionEngine.classify_request(query)
        should_search = SearchDecisionEngine.should_search(query)
        reason = SearchDecisionEngine.get_search_reason(query)
        
        logger.debug(
            "Search decision for '%s': should_search=%s type=%s reason=%s",
            query[:80],
            should_search,
            request_type,
            reason,
        )
        
        # Check if search is needed
        if not should_search and not force_search:
            logger.debug("Search not needed per decision engine: %s", reason)
            return None
        
        # Perform search
        return await SearchRouter.search(
            query=query,
            request_type=request_type,
            num_results=num_results,
        )
    
    @staticmethod
    def _get_provider_order(request_type: SearchRequestType) -> list:
        """
        Determine optimal provider order for request type.
        
        RESEARCH queries benefit from Tavily's semantic search.
        Other queries are faster with Serper's Google-style results.
        Python fallback is always last-resort.
        
        Args:
            request_type: Classification of search type
            
        Returns:
            List of provider names in order of preference
        """
        # Research queries benefit from semantic search
        if request_type in [SearchRequestType.RESEARCH, SearchRequestType.FACT_CHECK]:
            return ["tavily", "serper", "python"]
        
        # News/current queries benefit from Serper's fresh index
        if request_type in [SearchRequestType.NEWS, SearchRequestType.CURRENT]:
            return ["serper", "tavily", "python"]
        
        # Everything else: Serper (fast) -> Tavily (semantic) -> Python (fallback)
        return ["serper", "tavily", "python"]
    
    @staticmethod
    def get_search_status() -> Dict[str, Any]:
        """
        Get status of available search providers.
        
        Returns:
            Dict with availability status of each provider
        """
        return {
            "serper": SerperProvider.is_available(),
            "tavily": TavilyProvider.is_available(),
            "python_fallback": PythonSearchProvider.is_available(),
            "any_available": (
                SerperProvider.is_available()
                or TavilyProvider.is_available()
                or PythonSearchProvider.is_available()
            ),
        }
