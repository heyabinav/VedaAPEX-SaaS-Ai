"""
Unit tests for validators.
"""

import pytest
from utils.validators import validators
from utils.exceptions import ValidationError


def test_validate_query_valid():
    """Test valid query validation."""
    result = validators.validate_query("mars rover")
    assert result == "mars rover"


def test_validate_query_too_short():
    """Test query too short."""
    with pytest.raises(ValidationError):
        validators.validate_query("a")


def test_validate_query_too_long():
    """Test query too long."""
    long_query = "a" * 300
    with pytest.raises(ValidationError):
        validators.validate_query(long_query)


def test_validate_query_invalid_chars():
    """Test query with invalid characters."""
    with pytest.raises(ValidationError):
        validators.validate_query("query@!#$")


def test_validate_pagination_valid():
    """Test valid pagination."""
    page, page_size = validators.validate_pagination(1, 20)
    assert page == 1
    assert page_size == 20


def test_validate_pagination_invalid_page():
    """Test invalid page number."""
    with pytest.raises(ValidationError):
        validators.validate_pagination(0, 20)


def test_validate_pagination_page_size_too_large():
    """Test page size too large."""
    with pytest.raises(ValidationError):
        validators.validate_pagination(1, 200)
