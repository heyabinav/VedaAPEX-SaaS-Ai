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
from contextlib import contextmanager

from fastapi import HTTPException
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

logger = logging.getLogger("db.session")


def _create_engine(database_url: str):
    is_sqlite = database_url.startswith("sqlite")
    return create_engine(
        database_url,
        echo=os.getenv("SQL_ECHO", "false").lower() == "true",
        **(
            {"connect_args": {"check_same_thread": False}}
            if is_sqlite
            else {"pool_pre_ping": True, "pool_size": 5, "max_overflow": 10}
        ),
    )


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

engine = _create_engine(_database_url)


def _fallback_to_sqlite() -> None:
    global engine, _database_url, _is_sqlite
    fallback_url = "sqlite:///./vedaapex.db"
    logger.warning(
        "Configured database is unreachable; falling back to local SQLite at %s",
        fallback_url,
    )
    _database_url = fallback_url
    _is_sqlite = True
    engine = _create_engine(fallback_url)


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
    import app.models.mcp_connector  # noqa: F401  # Custom MCP connectors & OAuth tables
    import app.models.custom_skill  # noqa: F401  # User Custom Skills table

    # Log all registered SQLModel tables for startup diagnostics
    registered_tables = sorted(SQLModel.metadata.tables.keys())
    logger.info(
        "Registered SQLModel tables (%d): %s",
        len(registered_tables),
        ", ".join(registered_tables),
    )

    logger.info("Running SQLModel.metadata.create_all ...")
    try:
        SQLModel.metadata.create_all(engine)
    except OperationalError as exc:
        if not _database_url.startswith("sqlite"):
            logger.warning("Database initialization failed: %s", exc)
            _fallback_to_sqlite()
            SQLModel.metadata.create_all(engine)
        else:
            raise

    _ensure_missing_schema_columns()
    logger.info("All database tables created/verified successfully.")


def _ensure_missing_schema_columns() -> None:
    """Dynamically add any missing table columns from SQLModel metadata to existing databases."""
    inspector = inspect(engine)
    try:
        db_tables = set(inspector.get_table_names())
    except Exception as exc:
        logger.warning("Unable to inspect database tables for schema verification: %s", exc)
        return

    is_sqlite = engine.dialect.name == "sqlite"

    for table_name, table in SQLModel.metadata.tables.items():
        if table_name not in db_tables:
            continue

        try:
            existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
        except Exception as exc:
            logger.warning("Unable to inspect columns for table '%s': %s", table_name, exc)
            continue

        for col_name, col_obj in table.columns.items():
            if col_name not in existing_columns:
                type_str = str(col_obj.type)
                logger.info(
                    "Adding missing column to table '%s': %s (%s)",
                    table_name,
                    col_name,
                    type_str,
                )
                try:
                    with engine.begin() as conn:
                        if is_sqlite:
                            sql = f'ALTER TABLE "{table_name}" ADD COLUMN "{col_name}" {type_str}'
                        else:
                            sql = f'ALTER TABLE "{table_name}" ADD COLUMN IF NOT EXISTS "{col_name}" {type_str}'
                        conn.execute(text(sql))
                    logger.info(
                        "Successfully added column '%s' to table '%s'.",
                        col_name,
                        table_name,
                    )
                except Exception as alter_exc:
                    logger.error(
                        "Failed to add column '%s' to table '%s': %s",
                        col_name,
                        table_name,
                        alter_exc,
                    )


def _ensure_missing_user_columns() -> None:
    """Backward-compatible wrapper for schema migration."""
    _ensure_missing_schema_columns()


def _open_session():
    try:
        return Session(engine)
    except OperationalError as exc:
        if not _database_url.startswith("sqlite"):
            logger.warning("Database session creation failed, retrying with local SQLite fallback: %s", exc)
            _fallback_to_sqlite()
            try:
                return Session(engine)
            except OperationalError as fallback_exc:
                logger.exception("Failed to create database session after SQLite fallback")
                detail = "Database service unavailable. Please try again later."
                if settings.APP_ENV != "production":
                    detail = f"Database service unavailable: {fallback_exc}"
                raise HTTPException(status_code=503, detail=detail) from fallback_exc
        else:
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


def _close_session(session: Session):
    try:
        session.close()
    except Exception:
        logger.exception("Failed to close database session")


@contextmanager
def get_session_context():
    session = _open_session()
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
        _close_session(session)


def get_session():
    session = _open_session()
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
        _close_session(session)

