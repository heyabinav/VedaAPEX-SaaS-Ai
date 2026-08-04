"""
Standalone CLI migration script.
Inspects existing database schema and automatically alters tables to add missing columns defined in SQLModel models.
"""

import os
import sys

# Add root directory to python path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.db.session import engine, init_db, _ensure_missing_schema_columns


def run_migration():
    print("Starting database schema initialization and migration...")
    init_db()
    _ensure_missing_schema_columns()
    print("Database schema migration complete.")


if __name__ == "__main__":
    run_migration()
