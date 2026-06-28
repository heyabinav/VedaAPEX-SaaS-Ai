"""
Unit tests for provider manager.
"""

import pytest
from services.provider_manager import ProviderManager


@pytest.fixture
def provider_manager():
    """Create provider manager instance."""
    return ProviderManager()


def test_categorize_query_space(provider_manager):
    """Test space query categorization."""
    category = provider_manager._categorize_query("mars rover")
    assert category == "space"


def test_categorize_query_scientific(provider_manager):
    """Test scientific query categorization."""
    category = provider_manager._categorize_query("cancer cell microscope")
    assert category == "scientific"


def test_categorize_query_general(provider_manager):
    """Test general query categorization."""
    category = provider_manager._categorize_query("nature travel city")
    assert category == "general"


def test_get_provider_priority_space(provider_manager):
    """Test provider priority for space queries."""
    priority = provider_manager._get_provider_priority("mars")
    # NASA should be first for space queries
    assert priority[0] == "nasa"


def test_deduplicate_results(provider_manager):
    """Test result deduplication."""
    results = [
        {"title": "Result 1", "url": "http://example.com/1"},
        {"title": "Result 1", "url": "http://example.com/2"},
        {"title": "Result 2", "url": "http://example.com/3"},
    ]

    deduplicated = provider_manager._deduplicate_results(results)
    assert len(deduplicated) == 2
