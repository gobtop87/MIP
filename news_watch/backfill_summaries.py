"""Regenerate Source Summary text for existing news items using Claude.

The News Feed's snippet field is normally whatever short description the
originating RSS feed / NewsAPI / SEC EDGAR search returned at fetch time —
usually 1-2 sentences. This script upgrades items with a thin snippet into a
real 4-5 sentence summary by having Claude fetch and read the actual article
at each item's URL.

Requires:
    pip install anthropic
    export ANTHROPIC_API_KEY=...   (or any credential source the SDK resolves)

Run against whichever news.db you want to backfill — for the live dashboard
that means running this on the machine/service that holds the production
database (this repo's own news/alerts data lives in a local SQLite file on
the web server, not a shared database — see README.md).

Usage:
    ./venv/bin/python -m news_watch.backfill_summaries [--company ID] [--limit N] [--dry-run]
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import anthropic

from news_watch import db

MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = """You are writing a short, factual summary of a news article for an \
investment analyst's dashboard. You will be given a headline, source, and URL, and \
sometimes an existing short snippet. Fetch the URL and read the actual article, then \
write a 4-5 sentence summary that gives a strong, standalone understanding of what the \
article is about, why it matters, and its key details, so the reader does not need to \
open the article themselves.

Base the summary strictly on the fetched content — never invent facts, figures, \
quotes, or specifics that are not present in the article. If the URL cannot be \
fetched (paywalled, broken, blocked), say so in one sentence and instead write the \
best 2-3 sentence summary you can from the headline and any existing snippet alone, \
making clear it is based on limited information.

Write in plain prose, third person, professional tone. No markdown, no headers, no \
bullet points — just the summary paragraph."""


def build_user_message(item):
    lines = [
        f"Headline: {item['headline']}",
        f"Source: {item['source_name'] or item['source']}",
        f"URL: {item['url']}",
    ]
    if item.get("snippet"):
        lines.append(f"Existing short snippet: {item['snippet']}")
    lines.append("\nFetch the URL above and write the summary.")
    return "\n".join(lines)


def summarize(client, item):
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=[{"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 1}],
        messages=[{"role": "user", "content": build_user_message(item)}],
    )

    if response.stop_reason == "refusal":
        return None

    text_blocks = [b.text for b in response.content if b.type == "text"]
    summary = " ".join(t.strip() for t in text_blocks if t.strip())
    return summary or None


def run(company_id=None, limit=None, dry_run=False, sleep_seconds=1.0):
    db.init_db()
    client = anthropic.Anthropic()

    items = db.get_items_for_summarization(company_id=company_id, limit=limit)
    if not items:
        print("Nothing to backfill — every item already has a substantial snippet.")
        return

    print(f"Found {len(items)} item(s) with a thin or missing summary.")

    updated, failed = 0, 0
    for i, item in enumerate(items, 1):
        label = item["headline"][:70]
        try:
            summary = summarize(client, item)
        except (anthropic.APIError, TypeError) as exc:
            print(f"[{i}/{len(items)}] FAILED  ({exc}): {label}")
            if i == 1:
                print(
                    "\nFirst item failed — this usually means no Anthropic "
                    "credentials are configured in this environment. Set "
                    "ANTHROPIC_API_KEY (or run `ant auth login`) and try again."
                )
                sys.exit(1)
            failed += 1
            time.sleep(sleep_seconds)
            continue

        if not summary:
            print(f"[{i}/{len(items)}] REFUSED/EMPTY: {label}")
            failed += 1
            time.sleep(sleep_seconds)
            continue

        print(f"[{i}/{len(items)}] OK ({len(summary)} chars): {label}")
        if not dry_run:
            db.update_snippet(item["id"], summary)
        updated += 1
        time.sleep(sleep_seconds)

    print(f"\nDone. Updated {updated}, failed/skipped {failed}, dry_run={dry_run}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--company", help="Only backfill items for this company id")
    parser.add_argument("--limit", type=int, help="Max number of items to process")
    parser.add_argument(
        "--dry-run", action="store_true", help="Don't write to the database"
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=1.0,
        help="Seconds to sleep between API calls (default 1.0)",
    )
    args = parser.parse_args()
    run(company_id=args.company, limit=args.limit, dry_run=args.dry_run, sleep_seconds=args.sleep)
