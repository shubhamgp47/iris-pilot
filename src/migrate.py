# src/migrate.py
from pathlib import Path
from src.db import get_connection

MIGRATIONS = [
    "001_create_schemas.sql",
    "002_create_staging.sql",
    "003_create_core.sql"
]

def run_migrations():
    migrations_dir = Path(__file__).parent.parent / "migrations"
    with get_connection() as conn:
        for sql_file in MIGRATIONS:
            path = migrations_dir / sql_file
            print(f"Applying migration: {sql_file}")
            sql = path.read_text(encoding="utf-8")
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
    print("All migrations applied successfully.")

if __name__ == "__main__":
    run_migrations()