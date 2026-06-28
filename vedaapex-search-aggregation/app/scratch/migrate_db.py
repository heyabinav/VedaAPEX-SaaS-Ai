import os
import sys
from sqlmodel import create_engine, SQLModel, Session, text

# Add root directory to path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, root_dir)

# Import all models to register them in SQLModel metadata
import app.models.user
import app.models.token
import app.models.task

from app.db.session import engine, init_db
import sqlalchemy


def migrate():
    # Make sure tables exist
    init_db()

    # Inspect actual tables and columns in database
    inspector = sqlalchemy.inspect(engine)
    db_tables = inspector.get_table_names()
    print("Database tables:", db_tables)

    # Compare with SQLModel metadata
    with Session(engine) as session:
        for table_name, table in SQLModel.metadata.tables.items():
            if table_name not in db_tables:
                print(
                    f"Table {table_name} does not exist in DB, it should have been created by init_db."
                )
                continue

            db_columns = {col["name"]: col for col in inspector.get_columns(table_name)}

            for col_name, col_obj in table.columns.items():
                if col_name not in db_columns:
                    print(f"Missing column: {table_name}.{col_name} (type: {col_obj.type})")
                    # Build ALTER TABLE SQL statement
                    # Convert sqlalchemy type to string
                    type_str = str(col_obj.type)
                    # Handle specific types or constraints if necessary, VARCHAR is generic enough
                    sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {type_str}"
                    print(f"Executing: {sql}")
                    try:
                        session.exec(text(sql))
                        session.commit()
                        print("Migration succeeded.")
                    except Exception as e:
                        print("Migration failed:", e)


if __name__ == "__main__":
    migrate()
