"""Helper utilities."""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class Helpers:
    """Helper utilities."""

    @staticmethod
    def get_timestamp() -> str:
        """Get ISO 8601 timestamp."""
        return datetime.utcnow().isoformat()

    @staticmethod
    def truncate_string(text: str, max_length: int = 100) -> str:
        """Truncate string to max length."""
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."

    @staticmethod
    def extract_metadata(provider_name: str, result: Dict) -> Dict:
        """Extract metadata from provider result."""
        # Normalize common fields
        metadata = {
            "title": result.get("title", ""),
            "description": result.get("description", ""),
            "provider": provider_name,
            "source_url": result.get("source_url", ""),
        }
        return metadata


helpers = Helpers()
