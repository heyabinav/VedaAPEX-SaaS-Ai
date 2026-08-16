"""Python Fallback Search Provider - DuckDuckGo based web search.

Provides web search results using the ddgs library as a fallback
when API-based providers (Serper/Tavily) are unavailable.
Uses DuckDuckGo's public search interface.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("services.providers.python_search_provider")


class PythonSearchProvider:
    """Python-based web search provider using DuckDuckGo."""
    
    @staticmethod
    def is_available() -> bool:
        """Check if Python search provider is available."""
        try:
            import duckduckgo_search
            return True
        except ImportError:
            logger.debug("duckduckgo_search library not installed")
            return False
    
    @staticmethod
    async def search(
        query: str,
        num_results: int = 10,
    ) -> Dict[str, Any]:
        """
        Perform web search using DuckDuckGo via ddgs library.
        
        Args:
            query: Search query
            num_results: Number of results to return
            
        Returns:
            Dict with normalized search results
            
        Raises:
            ImportError: If ddgs library not available
            Exception: If search fails
        """
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            raise ImportError(
                "duckduckgo_search library not installed. "
                "Install with: pip install duckduckgo-search"
            )
        
        try:
            logger.debug("Python fallback search: %s (limit=%d)", query, num_results)
            
            ddgs = DDGS()
            results = []
            
            # Perform search
            search_results = ddgs.text(query, max_results=num_results)
            
            if not search_results:
                logger.debug("Python fallback search returned no results for: %s", query)
                return PythonSearchProvider._normalize_empty(query)
            
            # Normalize results
            for idx, item in enumerate(search_results):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("href", ""),
                    "snippet": item.get("body", ""),
                    "position": idx + 1,
                    "provider": "python_ddgs",
                })
            
            logger.debug(
                "Python fallback search success: %d results for '%s'",
                len(results),
                query,
            )
            
            return {
                "success": True,
                "query": query,
                "results": results,
                "result_count": len(results),
                "provider": "python_ddgs",
                "fallback": True,
            }
            
        except Exception as e:
            logger.error("Python fallback search failed: %s", str(e), exc_info=True)
            raise Exception(f"Python search provider error: {str(e)}")
    
    @staticmethod
    def _normalize_empty(query: str) -> Dict[str, Any]:
        """Return empty result structure."""
        return {
            "success": True,
            "query": query,
            "results": [],
            "result_count": 0,
            "provider": "python_ddgs",
            "fallback": True,
        }
