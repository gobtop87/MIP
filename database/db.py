"""SQLite connection for Assignments 1-3 (Pair B): companies, monthly_metrics,
scores, score_history, flag_history.

This is the *only* file that should know it's talking to SQLite. Every other
module (build_db.py, fade_score.py, app.py, ...) goes through get_conn() /
init_db() instead of opening its own connection, so swapping in the real
Supabase/Postgres database later is a matter of rewriting this one file —
callers don't change.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "mip.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(reset=False):
    """Create mip.db from schema.sql. `reset=True` drops and rebuilds it."""
    if reset and DB_PATH.exists():
        DB_PATH.unlink()
    with get_conn() as conn:
        conn.executescript(SCHEMA_PATH.read_text())
