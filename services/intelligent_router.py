"""Intelligent router for automatic provider selection."""

import logging
from typing import List, Tuple
from config import config

logger = logging.getLogger(__name__)


class IntelligentRouter:
    """Route queries to appropriate providers based on content."""

    def __init__(self):
        """Initialize router."""
        self.space_keywords = set(kw.lower() for kw in config.SPACE_KEYWORDS)
        self.scientific_keywords = set(kw.lower() for kw in config.SCIENTIFIC_KEYWORDS)
        self.general_keywords = set(kw.lower() for kw in config.GENERAL_KEYWORDS)

    def categorize_query(self, query: str) -> str:
        """
        Categorize query into space, scientific, or general.

        Returns: "space", "scientific", or "general"
        """
        query_lower = query.lower()

        # Check space keywords first (highest priority)
        if any(kw in query_lower for kw in self.space_keywords):
            logger.debug(f"Query '{query}' categorized as SPACE")
            return "space"

        # Check scientific keywords second
        if any(kw in query_lower for kw in self.scientific_keywords):
            logger.debug(f"Query '{query}' categorized as SCIENTIFIC")
            return "scientific"

        # Default to general
        logger.debug(f"Query '{query}' categorized as GENERAL")
        return "general"

    def get_provider_priority(self, category: str) -> List[str]:
        """
        Get provider priority based on query category.

        Returns: Ordered list of provider names
        """
        enabled_providers = self._get_enabled_providers()

        if category == "space":
            priority = ["nasa", "wikimedia", "pexels"]
        elif category == "scientific":
            priority = ["wikimedia", "nasa", "pexels"]
        else:  # general
            priority = ["pexels", "wikimedia", "nasa"]

        # Filter to only enabled providers
        priority = [p for p in priority if p in enabled_providers]

        logger.debug(f"Provider priority for '{category}': {priority}")
        return priority

    def _get_enabled_providers(self) -> List[str]:
        """Get list of enabled providers."""
        enabled = []
        if config.ENABLE_PEXELS:
            enabled.append("pexels")
        if config.ENABLE_WIKIMEDIA:
            enabled.append("wikimedia")
        if config.ENABLE_NASA:
            enabled.append("nasa")
        return enabled

    def route_query(self, query: str) -> Tuple[str, List[str]]:
        """
        Route query to providers.

        Returns: (primary_provider, fallback_providers)
        """
        category = self.categorize_query(query)
        providers = self.get_provider_priority(category)

        if not providers:
            raise ValueError("No providers enabled")

        primary = providers[0]
        fallbacks = providers[1:]

        logger.info(f"Route query '{query}': primary={primary}, fallbacks={fallbacks}")

        return primary, fallbacks

    def get_category_details(self, query: str) -> dict:
        """Get detailed categorization information."""
        category = self.categorize_query(query)
        primary, fallbacks = self.route_query(query)

        return {
            "query": query,
            "category": category,
            "primary_provider": primary,
            "fallback_providers": fallbacks,
        }


router = IntelligentRouter()
