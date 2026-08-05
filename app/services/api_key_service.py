from utils.time import utcnow

import secrets
import hashlib
from datetime import datetime
from typing import Optional, List
from sqlmodel import Session, select
from ..models.token import APIKey
from ..models.user import User


class APIKeyService:
    @staticmethod
    def generate_key_string() -> str:
        """Generate a random secure API key string."""
        return f"vc_{secrets.token_urlsafe(32)}"

    @staticmethod
    def hash_key(key: str) -> str:
        """Hash the API key for secure storage."""
        return hashlib.sha256(key.encode()).hexdigest()

    @staticmethod
    def create_api_key(session: Session, user_id: int, name: str = "Default Key") -> dict:
        """Create a new API key for a user and return the raw key."""
        raw_key = APIKeyService.generate_key_string()
        key_hash = APIKeyService.hash_key(raw_key)

        db_key = APIKey(
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            prefix=raw_key[:8],
            is_active=True,
        )
        session.add(db_key)
        session.commit()
        session.refresh(db_key)

        return {
            "id": db_key.id,
            "name": db_key.name,
            "api_key": raw_key,  # Only shown once
            "prefix": db_key.prefix,
            "created_at": db_key.created_at,
        }

    @staticmethod
    def validate_api_key(session: Session, raw_key: str) -> Optional[User]:
        """Validate a raw API key and return the associated User."""
        key_hash = APIKeyService.hash_key(raw_key)
        db_key = session.exec(
            select(APIKey).where(APIKey.key_hash == key_hash, APIKey.is_active == True)
        ).first()

        if not db_key:
            return None

        if db_key.expires_at and db_key.expires_at < utcnow():
            db_key.is_active = False
            session.add(db_key)
            session.commit()
            return None

        return db_key.user

    @staticmethod
    def revoke_api_key(session: Session, user_id: int, key_id: int) -> bool:
        """Revoke an API key."""
        db_key = session.exec(
            select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user_id)
        ).first()

        if not db_key:
            return False

        db_key.is_active = False
        session.add(db_key)
        session.commit()
        return True

    @staticmethod
    def list_api_keys(session: Session, user_id: int) -> List[APIKey]:
        """List all API keys for a user."""
        return session.exec(
            select(APIKey).where(APIKey.user_id == user_id).order_by(APIKey.created_at.desc())
        ).all()