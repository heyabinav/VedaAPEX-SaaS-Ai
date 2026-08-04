"""
Database session management.

Key fixes:
- Uses settings from core.config instead of independent os.getenv (single source of truth)
- Fixes Render's postgres:// -> postgresql:// scheme issue
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
    ``postgres://`` which is no longer supported by SQLAlchemy >=1.4.
    We transparently rewrite it to ``postgresql://``.
    Supabase URLs also get ``sslmode=require`` appended when missing.
    """
    url = settings.DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
        logger.info("Rewrote DATABASE_URL scheme from postgres:// -> postgresql://")
    if ".supabase.co" in url and "sslmode=" not in url:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}sslmode=require"
        logger.info("Added sslmode=require for Supabase database connection")
    return url


_database_url = _get_database_url()

# Use pool_pre_ping for PostgreSQL to avoid stale-connection errors on Render.
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
    """Create all tables - imports every model module first so SQLModel sees them."""
    # Force import of ALL model modules so their SQLModel subclasses
    # are registered in SQLModel.metadata before create_all runs.
    import app.models.user  # noqa: F401
    import app.models.token  # noqa: F401
    import app.models.task  # noqa: F401
    import app.models.user_oauth_tokens  # noqa: F401
    import app.models.asset  # noqa: F401  # New: AI asset metadata, usage logs, error logs
    import app.models.search_history  # noqa: F401  # Saved search history entries
    import app.models.search_history_result  # noqa: F401  # Stored search result payloads
    import app.models.managed_connector  # noqa: F401  # Managed MCP connector registry
    import app.models.chat_session  # noqa: F401  # Chat sessions for memory-aware assistant
    import app.models.chat_message  # noqa: F401  # Chat messages for memory-aware assistant

    # Log all registered SQLModel tables for startup diagnostics
    registered_tables = sorted(SQLModel.metadata.tables.keys())
    logger.info(
        "Registered SQLModel tables (%d): %s",
        len(registered_tables),
        ", ".join(registered_tables),
    )

    logger.info("Running SQLModel.metadata.create_all ...")
    SQLModel.metadata.create_all(engine)
    logger.info("All database tables created/verified successfully.")


def get_session():
    try:
        session = Session(engine)
    except OperationalError as exc:
        logger.exception("Failed to create database session due to operational error")
        detail = "Database service unavailable. Please try again later."
        if settings.APP_ENV != "production":
            detail = f"Database service unavailable: {exc}"
        raise HTTPException(status_code=503, detail=detail) from exc
    except SQLAlchemyError as exc:
        logger.exception("Database error while opening session", exc_info=True)
        detail = "Database error occurred. Please contact support."
        if settings.APP_ENV != "production":
            detail = f"Database error occurred: {exc}"
        raise HTTPException(status_code=503, detail=detail) from exc

    try:
        yield session
    except OperationalError as exc:
        logger.exception("Database operational error during request handling")
        detail = "Database service unavailable. Please try again later."
        if settings.APP_ENV != "production":
            detail = f"Database service unavailable: {exc}"
        raise HTTPException(status_code=503, detail=detail) from exc
    except SQLAlchemyError as exc:
        logger.exception("Database error during request handling", exc_info=True)
        detail = "Database error occurred. Please contact support."
        if settings.APP_ENV != "production":
            detail = f"Database error occurred: {exc}"
        raise HTTPException(status_code=503, detail=detail) from exc
    finally:
        session.close()

