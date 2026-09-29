import pytest
from src.db import get_connection

@pytest.fixture
def db_conn():
    conn = get_connection()
    yield conn
    conn.close()

@pytest.fixture
def db_cursor(db_conn):
    with db_conn.cursor() as cur:
        yield cur