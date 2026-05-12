import os
from contextlib import contextmanager
from typing import Generator

import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv()

_pool: pool.ThreadedConnectionPool | None = None


def _build_pool() -> pool.ThreadedConnectionPool:
    return pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=10,
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def _get_pool() -> pool.ThreadedConnectionPool:
    global _pool
    if _pool is None or _pool.closed:
        _pool = _build_pool()
    return _pool


@contextmanager
def get_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    p = _get_pool()
    conn = p.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        p.putconn(conn)
