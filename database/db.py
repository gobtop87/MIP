"""Database connection for Assignments 1-3 (Pair B): companies, monthly_metrics,
scores, score_history, flag_history.

Defaults to a local SQLite file (mip.db) for local development (./run.sh) --
zero config needed. Set the DATABASE_URL environment variable to a Postgres
connection string (Supabase's "Connection string" from Project Settings ->
Database) to point this at the real shared database instead. Every other
module goes through get_conn()/init_db() here rather than opening its own
connection, so this is the only file that needs to know which backend is
active.

The Postgres path wraps psycopg2 so it exposes the same conn.execute(sql,
params) -> cursor-with-fetchone/fetchall interface sqlite3 does, translating
'?' placeholders to '%s'. Callers that need a newly-inserted row's id use
`... RETURNING id` (supported by both SQLite 3.35+ and Postgres) instead of
sqlite3's .lastrowid, since psycopg2 doesn't have an equivalent.
"""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "mip.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# Set in production (e.g. Render's environment variables) to a Supabase/
# Postgres connection string. Unset for local dev, which uses SQLite instead.
DATABASE_URL = os.environ.get("DATABASE_URL")


class _PGCursor:
    """Makes a psycopg2 cursor usable like a sqlite3 Cursor: execute()
    returns something with fetchone()/fetchall(), and '?' placeholders work."""

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql, params=()):
        self._cursor.execute(sql.replace("?", "%s"), params)
        return self

    def executescript(self, sql):
        self._cursor.execute(sql)
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()


class _PGConnection:
    """Makes a psycopg2 connection usable like a sqlite3 Connection: calls
    go straight through conn.execute(...) instead of conn.cursor().execute(...)."""

    def __init__(self, pg_conn):
        self._pg_conn = pg_conn
        self._cursor = _PGCursor(pg_conn.cursor())

    def execute(self, sql, params=()):
        return self._cursor.execute(sql, params)

    def executescript(self, sql):
        return self._cursor.executescript(sql)

    def commit(self):
        self._pg_conn.commit()

    def close(self):
        self._pg_conn.close()


@contextmanager
def get_conn():
    if DATABASE_URL:
        import psycopg2

        conn = _PGConnection(psycopg2.connect(DATABASE_URL))
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def init_db(reset=False):
    """
    SQLite: create mip.db from schema.sql. `reset=True` drops and rebuilds it.

    Postgres: never auto-creates or drops anything -- the real database's
    schema is set up once by hand (paste database/schema_supabase.sql into
    the Supabase SQL editor; see database/README.md). This just checks the
    tables are actually there, so a missing schema fails with a clear error
    instead of a confusing one deeper in the app.
    """
    if DATABASE_URL:
        with get_conn() as conn:
            conn.execute("SELECT 1 FROM companies LIMIT 1")
        return

    if reset and DB_PATH.exists():
        DB_PATH.unlink()
    with get_conn() as conn:
        conn.executescript(SCHEMA_PATH.read_text())
