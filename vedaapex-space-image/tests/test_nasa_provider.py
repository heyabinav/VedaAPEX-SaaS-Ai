"""
Unit tests for NASA provider.
"""

import pytest
import asyncio
from providers.nasa_provider import NASAProvider
from utils.exceptions import ProviderError


@pytest.fixture
def nasa_provider():
    """Create NASA provider instance."""
    return NASAProvider()


@pytest.mark.asyncio
async def test_search_images(nasa_provider):
    """Test image search."""
    try:
        result = await nasa_provider.search_images("mars", page=1)
        assert "collection" in result
        assert "items" in result["collection"]
    except ProviderError as e:
        pytest.skip(f"NASA API unavailable: {e}")


@pytest.mark.asyncio
async def test_search_videos(nasa_provider):
    """Test video search."""
    try:
        result = await nasa_provider.search_videos("apollo", page=1)
        assert "collection" in result
        assert "items" in result["collection"]
    except ProviderError as e:
        pytest.skip(f"NASA API unavailable: {e}")


@pytest.mark.asyncio
async def test_timeout_handling(nasa_provider):
    """Test timeout handling."""
    nasa_provider.timeout = 0.001  # Very short timeout
    with pytest.raises(ProviderError):
        await nasa_provider.search_images("mars")


def test_headers(nasa_provider):
    """Test request headers."""
    headers = nasa_provider._get_headers()
    assert "User-Agent" in headers
    assert "Accept" in headers


def test_params(nasa_provider):
    """Test request parameters."""
    params = nasa_provider._get_params("mars", media_type="image", page=1)
    assert params["q"] == "mars"
    assert params["media_type"] == "image"
    assert "api_key" in params
