"""SQLite storage for Assignment 4.

Schema is written to be a straightforward port to the shared Supabase
database once Assignment 1 (Pair B) has it live: same table/column names,
just swap `sqlite3` for a `psycopg2`/`postgrest` connection.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "news.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    sector TEXT,
    competitors TEXT,  -- JSON array
    keywords TEXT,     -- JSON array
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS news_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL REFERENCES companies(id),
    source TEXT NOT NULL,        -- newsapi | sec_edgar | rss
    source_name TEXT,            -- e.g. "TechCrunch", "SEC EDGAR"
    author TEXT,                 -- byline, when the fetcher can determine one
    headline TEXT NOT NULL,
    url TEXT NOT NULL,
    published_at TEXT,
    matched_term TEXT,           -- which competitor/keyword triggered the match
    is_competitor_mention INTEGER DEFAULT 0,
    snippet TEXT,
    fetched_at TEXT DEFAULT (datetime('now')),
    UNIQUE(company_id, url)
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
        try:
            conn.execute("ALTER TABLE news_items ADD COLUMN author TEXT")
        except sqlite3.OperationalError:
            pass  # already migrated


def upsert_companies(companies):
    import json

    with get_conn() as conn:
        for c in companies:
            conn.execute(
                """
                INSERT INTO companies (id, name, sector, competitors, keywords)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    sector=excluded.sector,
                    competitors=excluded.competitors,
                    keywords=excluded.keywords
                """,
                (
                    c["id"],
                    c["name"],
                    c["sector"],
                    json.dumps(c["competitors"]),
                    json.dumps(c["keywords"]),
                ),
            )


def insert_news_item(item):
    """Insert a news item, ignoring duplicates (same company_id + url)."""
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO news_items
                (company_id, source, source_name, author, headline, url, published_at,
                 matched_term, is_competitor_mention, snippet)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["company_id"],
                item["source"],
                item.get("source_name"),
                item.get("author"),
                item["headline"],
                item["url"],
                item.get("published_at"),
                item.get("matched_term"),
                int(item.get("is_competitor_mention", False)),
                item.get("snippet"),
            ),
        )
        return cur.rowcount > 0  # True if newly inserted


def count_items_today():
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT COUNT(*) FROM news_items WHERE date(fetched_at) = date('now')"
        )
        return cur.fetchone()[0]
