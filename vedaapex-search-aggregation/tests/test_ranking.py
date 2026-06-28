"""Test ranking system."""

import pytest
from utils.ranking import RankingSystem


@pytest.fixture
def ranking():
    return RankingSystem()


def test_deduplicate_results(ranking):
    """Test deduplication."""
    results = [
        {"title": "Result 1", "url": "http://1.com"},
        {"title": "Result 1", "url": "http://2.com"},
        {"title": "Result 2", "url": "http://3.com"},
    ]
    deduplicated = ranking.deduplicate_results(results)
    assert len(deduplicated) == 2


def test_rank_results(ranking):
    """Test ranking."""
    results = [
        {"title": "A", "provider": "pexels"},
        {"title": "B", "provider": "nasa"},
        {"title": "C", "provider": "wikimedia"},
    ]
    ranked = ranking.rank_results(results)
    assert len(ranked) == 3
    # NASA should be first (score 3)
    assert ranked[0]["provider"] == "nasa"


def test_merge_and_rank(ranking):
    """Test merge and rank."""
    provider_results = {
        "nasa": [{"title": "Mars"}],
        "pexels": [{"title": "Nature"}],
    }
    merged = ranking.merge_and_rank(provider_results, max_results=10)
    assert len(merged) == 2
