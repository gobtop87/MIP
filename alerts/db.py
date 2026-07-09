"""SQLite storage for Assignment 5, in the same news.db as Assignment 4."""

import sqlite3
from contextlib import contextmanager

from news_watch.db import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    news_item_id INTEGER NOT NULL UNIQUE REFERENCES news_items(id),
    company_id TEXT NOT NULL REFERENCES companies(id),
    urgency TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def unalerted_news_items():
    """News items that haven't been run through relevance/urgency yet."""
    with get_conn() as conn:
        cur = conn.execute(
            """
            SELECT n.id, n.company_id, n.source, n.source_name, n.headline, n.url,
                   n.published_at, n.matched_term, n.is_competitor_mention, n.snippet
            FROM news_items n
            LEFT JOIN alerts a ON a.news_item_id = n.id
            WHERE a.id IS NULL
            """
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def insert_alert(alert):
    """Insert an alert, ignoring duplicates (same news_item_id)."""
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO alerts (news_item_id, company_id, urgency, message)
            VALUES (?, ?, ?, ?)
            """,
            (alert["news_item_id"], alert["company_id"], alert["urgency"], alert["message"]),
        )
        return cur.rowcount > 0


def count_alerts_by_urgency():
    with get_conn() as conn:
        cur = conn.execute("SELECT urgency, COUNT(*) FROM alerts GROUP BY urgency")
        return dict(cur.fetchall())
