"""
Helper utilities.
"""

import hashlib
from datetime import datetime


class Helpers:
    """Helper utilities."""

    @staticmethod
    def generate_cache_key(prefix: str, query: str, page: int = 1) -> str:
        """Generate cache key."""
        key_str = f"{prefix}:{query}:{page}"
        return hashlib.md5(key_str.encode()).hexdigest()

    @staticmethod
    def get_timestamp() -> str:
        """Get ISO timestamp."""
        return datetime.utcnow().isoformat()

    @staticmethod
    def truncate_string(text: str, max_length: int = 100) -> str:
        """Truncate string."""
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."


helpers = Helpers()
