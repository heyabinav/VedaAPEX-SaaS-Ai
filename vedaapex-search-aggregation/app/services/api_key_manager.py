"""API Key generation and validation utilities."""

import secrets
import bcrypt
from typing import Tuple


class APIKeyManager:
    """Manager for generating, hashing, and validating API keys."""

    PREFIX = "vedaapex_"
    KEY_LENGTH = 32  # 32 bytes = 256 bits of entropy

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new API key.

        Returns:
            Raw API key (with prefix). Example: vedaapex_abc123def456...
            Only return this once to user — never store raw key in DB!
        """
        raw_key = secrets.token_urlsafe(APIKeyManager.KEY_LENGTH)
        return f"{APIKeyManager.PREFIX}{raw_key}"

    @staticmethod
    def get_prefix(raw_key: str) -> str:
        """
        Extract the prefix from a raw API key for fast lookup.

        Args:
            raw_key: Full API key (e.g., "vedaapex_abc123def456...")

        Returns:
            Prefix for database lookup (first 20 chars, e.g., "vedaapex_abc123de")
        """
        return raw_key[:20]

    @staticmethod
    def hash_key(raw_key: str) -> str:
        """
        Hash an API key for secure storage.

        Args:
            raw_key: Raw API key

        Returns:
            Bcrypt hash of the key (for storage in DB)
        """
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(raw_key.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_key(raw_key: str, key_hash: str) -> bool:
        """
        Verify a raw API key against its hash.

        Args:
            raw_key: Raw API key to verify
            key_hash: Bcrypt hash from database

        Returns:
            True if valid, False otherwise
        """
        try:
            return bcrypt.checkpw(raw_key.encode("utf-8"), key_hash.encode("utf-8"))
        except Exception:
            return False

    @staticmethod
    def generate_and_hash() -> Tuple[str, str, str]:
        """
        Generate a new API key, hash it, and extract prefix (for creation flow).

        Returns:
            Tuple of (raw_key, key_hash, prefix)
            - raw_key: Return this to user (only once!)
            - key_hash: Store this in database
            - prefix: Store this in database for lookup
        """
        raw_key = APIKeyManager.generate_key()
        key_hash = APIKeyManager.hash_key(raw_key)
        prefix = APIKeyManager.get_prefix(raw_key)
        return raw_key, key_hash, prefix


# Example usage:
if __name__ == "__main__":
    # Generate a new key
    raw_key, key_hash, prefix = APIKeyManager.generate_and_hash()

    print(f"Raw Key (give to user once): {raw_key}")
    print(f"Hash (store in DB):         {key_hash}")
    print(f"Prefix (store in DB):       {prefix}")
    print()

    # Later, when validating an API key from a request:
    candidate_key = raw_key  # This comes from request header
    is_valid = APIKeyManager.verify_key(candidate_key, key_hash)
    print(f"Verification result: {is_valid}")
