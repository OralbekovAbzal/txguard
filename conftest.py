import pytest
from main import r, conn

def clear_db() -> None:
    with conn.cursor() as cur:
        cur.execute("TRUNCATE transactions")
        conn.commit()

@pytest.fixture
def clean_storage():
    r.flushdb()
    clear_db()
    yield
    r.flushdb()
    clear_db()