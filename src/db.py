import os
import psycopg

DEFAULT_URL = "postgresql://iris_user:iris_password@localhost:5432/iris_pilot"

def get_connection(url: str | None = None):
    conn_url = url or os.environ.get("DATABASE_URL", DEFAULT_URL)
    return psycopg.connect(conn_url, autocommit=True)