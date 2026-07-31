"""Small helper for encrypting connector secrets at rest."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from typing import Any

from cryptography.fernet import Fernet


def _build_cipher() -> Fernet:
    raw_key = os.getenv("OAUTH_TOKEN_ENCRYPTION_KEY") or os.getenv("FERNET_KEY")
    if not raw_key:
        raw_key = Fernet.generate_key().decode("utf-8")
        os.environ["OAUTH_TOKEN_ENCRYPTION_KEY"] = raw_key

    try:
        return Fernet(raw_key.encode("utf-8"))
    except ValueError:
        derived_key = base64.urlsafe_b64encode(
            hashlib.sha256(raw_key.encode("utf-8")).digest()
        ).decode("utf-8")
        os.environ["OAUTH_TOKEN_ENCRYPTION_KEY"] = derived_key
        return Fernet(derived_key.encode("utf-8"))


_cipher = _build_cipher()


def encrypt_text(value: str) -> str:
    if not value:
        return ""
    return _cipher.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_text(value: str) -> str:
    if not value:
        return ""
    return _cipher.decrypt(value.encode("utf-8")).decode("utf-8")


def encrypt_json(value: dict[str, Any]) -> str:
    return encrypt_text(json.dumps(value, separators=(",", ":"), ensure_ascii=True))


def decrypt_json(value: str) -> dict[str, Any]:
    if not value:
        return {}
    raw = decrypt_text(value)
    return json.loads(raw) if raw else {}


def mask_secret(value: str | None, visible_tail: int = 4) -> str | None:
    if not value:
        return None
    if len(value) <= visible_tail:
        return "*" * len(value)
    return f"{'*' * max(0, len(value) - visible_tail)}{value[-visible_tail:]}"
