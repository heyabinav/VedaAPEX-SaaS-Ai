"""Database models for email verification."""

from app.utils.time import utcnow

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Integer, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import bcrypt

Base = declarative_base()


class EmailUser(Base):
    """User model for email verification system."""

    __tablename__ = "email_users"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # User Info
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)

    # Email Verification
    is_email_verified = Column(Boolean, default=False, index=True)
    email_verified_at = Column(DateTime, nullable=True)

    # Verification Token
    verification_token = Column(String, nullable=True, unique=True, index=True)
    verification_token_expires = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Security
    last_login_at = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    last_failed_login_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<EmailUser(id={self.id}, email={self.email}, verified={self.is_email_verified})>"

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def verify_password(self, password: str) -> bool:
        """Verify password against hash."""
        try:
            return bcrypt.checkpw(password.encode("utf-8"), self.hashed_password.encode("utf-8"))
        except Exception:
            return False

    def is_verification_token_valid(self) -> bool:
        """Check if verification token is still valid."""
        if not self.verification_token_expires:
            return False
        return utcnow() < self.verification_token_expires

    def to_dict(self) -> dict:
        """Convert to dictionary (excluding sensitive data)."""
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "full_name": self.full_name,
            "is_email_verified": self.is_email_verified,
            "email_verified_at": (
                self.email_verified_at.isoformat() if self.email_verified_at else None
            ),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "last_login_at": (self.last_login_at.isoformat() if self.last_login_at else None),
        }