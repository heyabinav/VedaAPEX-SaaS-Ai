"""Test intelligent router."""

import pytest
from services.intelligent_router import IntelligentRouter


@pytest.fixture
def router():
    return IntelligentRouter()


def test_categorize_space_query(router):
    """Test space query categorization."""
    category = router.categorize_query("mars rover")
    assert category == "space"


def test_categorize_scientific_query(router):
    """Test scientific query categorization."""
    category = router.categorize_query("cancer cell microscope")
    assert category == "scientific"


def test_categorize_general_query(router):
    """Test general query categorization."""
    category = router.categorize_query("nature travel city")
    assert category == "general"


def test_get_provider_priority_space(router):
    """Test provider priority for space queries."""
    priority = router.get_provider_priority("space")
    assert priority[0] in ["nasa", "wikimedia", "pexels"]


def test_route_query(router):
    """Test query routing."""
    primary, fallbacks = router.route_query("mars image")
    assert primary is not None
    assert isinstance(fallbacks, list)


def test_get_category_details(router):
    """Test category details."""
    details = router.get_category_details("cancer cell")
    assert "query" in details
    assert "category" in details
    assert "primary_provider" in details
    assert "fallback_providers" in details
