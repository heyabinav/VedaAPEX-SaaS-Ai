"""Ranking system for search results."""

import logging
from typing import List, Dict
import hashlib

logger = logging.getLogger(__name__)


class RankingSystem:
    """Rank and score search results."""

    def __init__(self):
        """Initialize ranking system."""
        self.provider_scores = {
            "nasa": 3,
            "wikimedia": 2,
            "pexels": 1,
        }

    def score_result(self, result: Dict, provider: str, position: int) -> Dict:
        """
        Score a single result.

        Args:
            result: Search result dict
            provider: Provider name
            position: Position in results (0-based)

        Returns: Result with score
        """
        provider_score = self.provider_scores.get(provider, 0)
        position_score = max(0, 10 - position)  # Higher for earlier positions

        total_score = provider_score * 100 + position_score
        result["_score"] = total_score

        return result

    def rank_results(self, results: List[Dict], provider_scores: Dict = None) -> List[Dict]:
        """
        Rank results by provider and position.

        Args:
            results: List of search results
            provider_scores: Optional custom provider scores

        Returns: Ranked results sorted by score (descending)
        """
        if provider_scores:
            self.provider_scores.update(provider_scores)

        # Score each result
        scored = []
        for i, result in enumerate(results):
            provider = result.get("provider", "unknown")
            scored_result = self.score_result(result.copy(), provider, i)
            scored.append(scored_result)

        # Sort by score (descending)
        ranked = sorted(scored, key=lambda x: -x["_score"])

        # Remove score field
        for result in ranked:
            del result["_score"]

        logger.debug(f"Ranked {len(results)} results")
        return ranked

    def deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """
        Remove duplicate results by title hash.

        Args:
            results: List of results

        Returns: Deduplicated results
        """
        seen_hashes = set()
        deduplicated = []

        for result in results:
            title = result.get("title", "")
            title_hash = hashlib.md5(title.encode()).hexdigest()

            if title_hash not in seen_hashes:
                seen_hashes.add(title_hash)
                deduplicated.append(result)
            else:
                logger.debug(f"Removed duplicate: {title}")

        logger.debug(f"Deduplicated {len(results)} → {len(deduplicated)}")
        return deduplicated

    def merge_and_rank(
        self,
        provider_results: Dict[str, List[Dict]],
        max_results: int = 50,
    ) -> List[Dict]:
        """
        Merge results from multiple providers and rank.

        Args:
            provider_results: Dict of {provider: [results]}
            max_results: Maximum results to return

        Returns: Merged and ranked results
        """
        all_results = []

        # Flatten provider results
        for provider, results in provider_results.items():
            for result in results:
                result["provider"] = provider
                all_results.append(result)

        # Deduplicate
        all_results = self.deduplicate_results(all_results)

        # Rank
        ranked = self.rank_results(all_results)

        # Truncate
        final = ranked[:max_results]

        logger.info(
            f"Merged from {len(provider_results)} providers: "
            f"{len(all_results)} total → {len(final)} final"
        )

        return final


ranking_system = RankingSystem()
