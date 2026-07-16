"""Free RSS feeds — no API key required."""

import feedparser

from news_watch.config import RSS_FEEDS
from news_watch.text_utils import clean_snippet


def fetch_rss_articles():
    """Return a flat list of {source_name, headline, url, published_at, snippet}."""
    articles = []
    for source_name, feed_url in RSS_FEEDS:
        try:
            parsed = feedparser.parse(feed_url)
        except Exception as exc:
            print(f"  [rss] failed to fetch {source_name}: {exc}")
            continue

        for entry in parsed.entries:
            articles.append(
                {
                    "source_name": source_name,
                    "author": entry.get("author") or None,
                    "headline": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "published_at": entry.get("published", entry.get("updated", "")),
                    "snippet": clean_snippet(entry.get("summary", "")),
                }
            )
    return articles
