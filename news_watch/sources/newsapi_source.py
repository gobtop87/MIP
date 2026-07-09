"""NewsAPI.org integration. Skips gracefully if NEWSAPI_KEY isn't set —
sign up for a free key at https://newsapi.org/register and add it to .env."""

import os

import requests

NEWSAPI_URL = "https://newsapi.org/v2/everything"


def fetch_newsapi_articles(query, page_size=10):
    api_key = os.environ.get("NEWSAPI_KEY")
    if not api_key:
        return []

    try:
        resp = requests.get(
            NEWSAPI_URL,
            params={
                "q": query,
                "sortBy": "publishedAt",
                "pageSize": page_size,
                "language": "en",
                "apiKey": api_key,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        print(f"  [newsapi] failed to search '{query}': {exc}")
        return []

    articles = []
    for a in data.get("articles", []):
        articles.append(
            {
                "source_name": a.get("source", {}).get("name", "NewsAPI"),
                "headline": a.get("title", ""),
                "url": a.get("url", ""),
                "published_at": a.get("publishedAt", ""),
                "snippet": a.get("description", "") or "",
            }
        )
    return articles
