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

from sqlalchemy import inspect, text
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
    import app.models.api_key  # noqa: F401

    logger.info("Running SQLModel.metadata.create_all …")
    SQLModel.metadata.create_all(engine)
    _ensure_missing_schema_columns()
    logger.info("All database tables ensured.")


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


def get_session():
    with Session(engine) as session:
        yield session
