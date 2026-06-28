"""Migration script to add new subscription fields to the user table."""

from sqlmodel import text
from sqlalchemy import inspect
from app.db.session import engine


def run_migration():
    print("[Migration] Checking User table columns...")
    inspector = inspect(engine)
    try:
        columns = [col["name"] for col in inspector.get_columns("user")]
    except Exception as e:
        print(f"[Migration] Error inspecting columns (table might not exist yet): {e}")
        return

    new_cols = {
        "plan": "VARCHAR(50) DEFAULT 'free'",
        "is_pro": "BOOLEAN DEFAULT 0",
        "subscription_start": "TIMESTAMP NULL",
        "subscription_end": "TIMESTAMP NULL",
    }

    with engine.connect() as conn:
        for col_name, col_type in new_cols.items():
            if col_name not in columns:
                print(f"[Migration] Adding column {col_name}...")
                # We need to run ALTER TABLE to add the new column
                conn.execute(text(f"ALTER TABLE user ADD COLUMN {col_name} {col_type}"))
                conn.commit()
                print(f"[Migration] Column {col_name} added successfully.")
            else:
                print(f"[Migration] Column {col_name} already exists.")
    print("[Migration] Column migration check complete!\n")


if __name__ == "__main__":
    run_migration()
