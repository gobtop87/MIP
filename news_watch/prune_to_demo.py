"""Delete every news item that isn't part of the demo seed dataset.

Demo items are identified by their placeholder URL
(https://example.com/demo-article-N), written only by
news_watch.seed_demo_data. Everything else — real items fetched via
news_watch.fetch_news (NewsAPI/RSS/SEC EDGAR) — is deleted.

This is destructive and irreversible. Run with --dry-run first to see the
counts before anything is removed.

Usage:
    python -m news_watch.prune_to_demo [--dry-run]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from news_watch import db

DEMO_URL_PREFIX = "https://example.com/demo-article-"


def run(dry_run=False):
    db.init_db()
    with db.get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM news_items").fetchone()[0]
        demo = conn.execute(
            "SELECT COUNT(*) FROM news_items WHERE url LIKE ?",
            (DEMO_URL_PREFIX + "%",),
        ).fetchone()[0]
        non_demo = total - demo

        print(f"Total items: {total}")
        print(f"Demo items (kept): {demo}")
        print(f"Non-demo items (to delete): {non_demo}")

        if non_demo == 0:
            print("Nothing to delete.")
            return

        if dry_run:
            print("\nDry run — no changes made.")
            return

        conn.execute(
            "DELETE FROM news_items WHERE url NOT LIKE ?", (DEMO_URL_PREFIX + "%",)
        )
        print(f"\nDeleted {non_demo} non-demo item(s). {demo} demo item(s) remain.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="Show counts without deleting anything"
    )
    args = parser.parse_args()
    run(dry_run=args.dry_run)
