"""DB access layer. DATABASE_URL이 있으면 PostgreSQL(배포용, 예: Neon 무료 DB),
없으면 로컬 SQLite 파일을 씁니다. 라우터 코드는 두 경우 모두 `?` 자리표시자와
row["컬럼"] 접근을 그대로 사용합니다."""
import os
import sqlite3
import pathlib
import datetime

DATABASE_URL = os.environ.get("DATABASE_URL")

DB_PATH = pathlib.Path(__file__).resolve().parent.parent / "data" / "app.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    nickname TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS places (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    description TEXT,
    photo_path TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS place_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    place_id INTEGER NOT NULL REFERENCES places(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    place_id INTEGER NOT NULL REFERENCES places(id),
    created_at TEXT NOT NULL,
    UNIQUE(user_id, place_id)
);

CREATE TABLE IF NOT EXISTS inquiries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    email_sent INTEGER NOT NULL DEFAULT 0
);
"""


class _PgConn:
    """Wraps a psycopg connection so callers can keep sqlite-style `?` placeholders."""

    def __init__(self):
        import psycopg
        from psycopg.rows import dict_row
        self._conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)

    def execute(self, sql, params=()):
        return self._conn.execute(sql.replace("?", "%s"), params)

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


def get_conn():
    if DATABASE_URL:
        return _PgConn()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    if DATABASE_URL:
        schema = (SCHEMA.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
                  .replace(" REAL ", " DOUBLE PRECISION "))
        for stmt in schema.split(";"):
            if stmt.strip():
                conn.execute(stmt)
    else:
        conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def now() -> str:
    return datetime.datetime.utcnow().isoformat(timespec="seconds")
