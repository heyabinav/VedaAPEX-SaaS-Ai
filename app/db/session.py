"""
Database session management.

Key fixes:
- Uses settings from core.config instead of independent os.getenv (single source of truth)
- Fixes Render's postgres:// → postgresql:// scheme issue
- Adds pool_pre_ping for PostgreSQL resilience
- Imports ALL models before create_all so every table is registered
- Disables echo in production to avoid log spam
"""

import logging
import os

from fastapi import HTTPException
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

logger = logging.getLogger("db.session")


def _get_database_url() -> str:
    """
    Return a corrected DATABASE_URL suitable for SQLAlchemy.

    Render (and some other PaaS) provide DATABASE_URL with the scheme
    ``postgres://`` which is no longer supported by SQLAlchemy ≥1.4.
    We transparently rewrite it to ``postgresql://``.
    """
    url = settings.DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
        logger.info("Rewrote DATABASE_URL scheme from postgres:// → postgresql://")
    return url


_database_url = _get_database_url()

# Use pool_pre_ping for PostgreSQL to avoid stale‑connection errors on Render.
_is_sqlite = _database_url.startswith("sqlite")

engine = create_engine(
    _database_url,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",  # off by default
    **(
        {"connect_args": {"check_same_thread": False}}
        if _is_sqlite
        else {"pool_pre_ping": True, "pool_size": 5, "max_overflow": 10}
    ),
)


def init_db():
    """Create all tables — imports every model module first so SQLModel sees them."""
    # Force import of ALL model modules so their SQLModel subclasses
    # are registered in SQLModel.metadata *before* create_all runs.
    import app.models.user  # noqa: F401
    import app.models.token  # noqa: F401
    import app.models.task  # noqa: F401
    import app.models.user_oauth_tokens  # noqa: F401
    import app.models.asset  # noqa: F401  # New: AI asset metadata, usage logs, error logs
    import app.models.managed_connector  # noqa: F401  # Managed MCP connector registry

    # Log all registered SQLModel tables for startup diagnostics
    registered_tables = sorted(SQLModel.metadata.tables.keys())
    logger.info(
        "Registered SQLModel tables (%d): %s",
        len(registered_tables),
        ", ".join(registered_tables),
    )

    logger.info("Running SQLModel.metadata.create_all …")
    SQLModel.metadata.create_all(engine)
    logger.info("All database tables created/verified successfully.")


def get_session():
    try:
        session = Session(engine)
    except OperationalError as exc:
        logger.exception("Failed to create database session due to operational error")
        raise HTTPException(
            status_code=503,
            detail="Database service unavailable. Please try again later.",
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception("Database error while opening session", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="Database error occurred. Please contact support.",
        ) from exc

    try:
        yield session
    except OperationalError as exc:
        logger.exception("Database operational error during request handling")
        raise HTTPException(
            status_code=503,
            detail="Database service unavailable. Please try again later.",
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception("Database error during request handling", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="Database error occurred. Please contact support.",
        ) from exc
    finally:
        session.close()



