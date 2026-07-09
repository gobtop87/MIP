"""Assignment 4 entry point: pull news about portfolio companies and their
competitors from NewsAPI, SEC EDGAR, and RSS feeds, and save matches to the
database.

Usage:
    python -m news_watch.fetch_news
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from news_watch import db
from news_watch.config import COMPANIES, DAILY_ITEM_TARGET
from news_watch.sources.newsapi_source import fetch_newsapi_articles
from news_watch.sources.rss_source import fetch_rss_articles
from news_watch.sources.sec_edgar_source import fetch_sec_filings


def match_terms(text, terms):
    """Return the first term (competitor or keyword) found in text, or None.

    Uses word-boundary matching so short names like "Ro" don't match inside
    unrelated words like "round".
    """
    if not text:
        return None
    for term in terms:
        pattern = r"\b" + re.escape(term) + r"\b"
        if re.search(pattern, text, re.IGNORECASE):
            return term
    return None


def run():
    db.init_db()
    db.upsert_companies(COMPANIES)

    inserted = 0
    by_source = {"rss": 0, "sec_edgar": 0, "newsapi": 0}

    print("Fetching RSS feeds...")
    rss_articles = fetch_rss_articles()
    print(f"  pulled {len(rss_articles)} raw articles")

    for company in COMPANIES:
        competitors = company["competitors"]
        keywords = company["keywords"]
        all_terms = competitors + keywords

        # --- RSS: match already-fetched articles against this company ---
        for article in rss_articles:
            haystack = f"{article['headline']} {article['snippet']}"
            matched = match_terms(haystack, all_terms)
            if not matched:
                continue
            is_competitor = matched in competitors
            new = db.insert_news_item(
                {
                    "company_id": company["id"],
                    "source": "rss",
                    "source_name": article["source_name"],
                    "headline": article["headline"],
                    "url": article["url"],
                    "published_at": article["published_at"],
                    "matched_term": matched,
                    "is_competitor_mention": is_competitor,
                    "snippet": article["snippet"][:500],
                }
            )
            if new:
                inserted += 1
                by_source["rss"] += 1

        # --- SEC EDGAR: search filings for each competitor (real filers only) ---
        for competitor in competitors:
            filings = fetch_sec_filings(competitor, limit=2)
            for filing in filings:
                new = db.insert_news_item(
                    {
                        "company_id": company["id"],
                        "source": "sec_edgar",
                        "source_name": filing["source_name"],
                        "headline": filing["headline"],
                        "url": filing["url"],
                        "published_at": filing["published_at"],
                        "matched_term": competitor,
                        "is_competitor_mention": True,
                        "snippet": filing["snippet"],
                    }
                )
                if new:
                    inserted += 1
                    by_source["sec_edgar"] += 1

        # --- NewsAPI: query competitors + sector keyword, skipped if no key ---
        if os.environ.get("NEWSAPI_KEY"):
            query = " OR ".join(f'"{c}"' for c in competitors)
            articles = fetch_newsapi_articles(query)
            for article in articles:
                haystack = f"{article['headline']} {article['snippet']}"
                matched = match_terms(haystack, all_terms) or competitors[0]
                is_competitor = matched in competitors
                new = db.insert_news_item(
                    {
                        "company_id": company["id"],
                        "source": "newsapi",
                        "source_name": article["source_name"],
                        "headline": article["headline"],
                        "url": article["url"],
                        "published_at": article["published_at"],
                        "matched_term": matched,
                        "is_competitor_mention": is_competitor,
                        "snippet": article["snippet"][:500],
                    }
                )
                if new:
                    inserted += 1
                    by_source["newsapi"] += 1

    total_today = db.count_items_today()
    low, high = DAILY_ITEM_TARGET
    print(f"\nInserted {inserted} new items this run ({total_today} total today).")
    print(f"  by source: {by_source}")
    if total_today < low:
        print(f"  Below target range ({low}-{high}/day) — consider adding more RSS feeds or keywords.")
    elif total_today > high:
        print(f"  Above target range ({low}-{high}/day) — consider tightening the keyword list.")
    else:
        print(f"  Within target range ({low}-{high}/day). ")


if __name__ == "__main__":
    run()
