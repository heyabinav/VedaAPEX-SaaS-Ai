"""
Unit tests for helpers.
"""

import pytest
from utils.helpers import helpers


def test_generate_cache_key():
    """Test cache key generation."""
    key1 = helpers.generate_cache_key("image", "mars", 1)
    key2 = helpers.generate_cache_key("image", "mars", 1)

    # Same inputs should produce same key
    assert key1 == key2

    # Different inputs should produce different keys
    key3 = helpers.generate_cache_key("image", "mars", 2)
    assert key1 != key3


def test_get_timestamp():
    """Test timestamp generation."""
    ts = helpers.get_timestamp()
    assert isinstance(ts, str)
    assert "T" in ts  # ISO format


def test_truncate_string():
    """Test string truncation."""
    text = "This is a long string"
    truncated = helpers.truncate_string(text, max_length=10)
    assert len(truncated) <= 10
    assert truncated.endswith("...")


def test_truncate_string_short():
    """Test truncation of short string."""
    text = "Short"
    truncated = helpers.truncate_string(text, max_length=10)
    assert truncated == text
