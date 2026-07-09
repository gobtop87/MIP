"""Populate news_watch/news.db with realistic-looking demo news items.

This sandbox can't reach live RSS/NewsAPI/SEC hosts (blocked by egress
policy), so this script exists purely to make the dashboard demoable.
It is NOT part of the real pipeline — once you run fetch_news.py somewhere
with normal internet access, real items will accumulate alongside (or
instead of) this seed data.

Usage:
    ./venv/bin/python -m news_watch.seed_demo_data
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from news_watch import db
from news_watch.config import COMPANIES

now = datetime.utcnow()

# (company_id, source, source_name, headline, matched_term, is_competitor, hours_ago)
DEMO_ITEMS = [
    ("company-a", "rss", "TechCrunch", "Stripe raises new funding round at $70B valuation", "Stripe", True, 2),
    ("company-a", "rss", "VentureBeat", "Plaid partners with three major banks on open banking", "Plaid", True, 5),
    ("company-a", "newsapi", "Reuters", "Adyen reports strong quarterly earnings", "Adyen", True, 9),
    ("company-a", "rss", "Crunchbase News", "Block Inc acquires fraud detection startup", "acquires", True, 14),
    ("company-a", "sec_edgar", "SEC EDGAR", "Square Inc filed 8-K mentioning \"Square\"", "Square", True, 20),
    ("company-a", "rss", "TechCrunch", "Payments sector sees wave of layoffs amid slowdown", "layoffs", False, 27),

    ("company-b", "rss", "VentureBeat", "OpenAI announces new foundation model with longer context", "OpenAI", True, 1),
    ("company-b", "newsapi", "The Verge", "Anthropic raises Series C at higher valuation", "Anthropic", True, 6),
    ("company-b", "rss", "TechCrunch", "Scale AI acquired by data labeling rival", "acquisition", True, 11),
    ("company-b", "rss", "Ars Technica", "Databricks reports data breach affecting enterprise customers", "data breach", True, 18),
    ("company-b", "rss", "Crunchbase News", "Hugging Face partnership brings open models to enterprise", "Hugging Face", True, 24),
    ("company-b", "newsapi", "Reuters", "GPU shortage continues to squeeze AI infra startups", "GPU", False, 30),

    ("company-c", "rss", "The Verge", "CrowdStrike discloses vulnerability in endpoint agent", "vulnerability", True, 3),
    ("company-c", "sec_edgar", "SEC EDGAR", "Palo Alto Networks Inc filed 8-K mentioning \"Palo Alto Networks\"", "Palo Alto Networks", True, 8),
    ("company-c", "rss", "TechCrunch", "SentinelOne raises new funding round", "funding round", True, 13),
    ("company-c", "newsapi", "Reuters", "Okta faces lawsuit over 2025 breach disclosure", "lawsuit", True, 19),
    ("company-c", "rss", "Ars Technica", "Ransomware group claims new victim among Fortune 500", "ransomware", False, 22),

    ("company-d", "rss", "TechCrunch", "Shopify acquires logistics startup to expand fulfillment", "Shopify", True, 4),
    ("company-d", "rss", "Crunchbase News", "ShipBob announces partnership with major retailer", "ShipBob", True, 10),
    ("company-d", "newsapi", "Reuters", "Flexport lays off staff amid freight slowdown", "layoffs", True, 16),
    ("company-d", "rss", "VentureBeat", "Faire raises new funding round for wholesale marketplace", "funding round", True, 23),
    ("company-d", "rss", "TechCrunch", "Supply chain software sees renewed investor interest", "supply chain", False, 29),

    ("company-e", "rss", "The Verge", "Teladoc reports quarterly earnings miss", "earnings", True, 2),
    ("company-e", "newsapi", "Reuters", "Ro announces layoffs amid telehealth pullback", "Ro", True, 7),
    ("company-e", "rss", "TechCrunch", "Hims & Hers faces FDA scrutiny over compounded drugs", "Hims & Hers", True, 12),
    ("company-e", "rss", "Crunchbase News", "Cerebral settles lawsuit over prescribing practices", "lawsuit", True, 17),
    ("company-e", "rss", "Ars Technica", "Telehealth clinical trial shows promising results", "clinical trial", False, 25),

    ("company-f", "rss", "TechCrunch", "Vercel raises new funding round at higher valuation", "Vercel", True, 1),
    ("company-f", "newsapi", "Reuters", "Datadog reports major outage affecting customers", "outage", True, 6),
    ("company-f", "rss", "The Verge", "GitHub acquired feature sparks developer platform debate", "GitHub", True, 15),
    ("company-f", "sec_edgar", "SEC EDGAR", "Atlassian Corp filed 8-K mentioning \"Atlassian\"", "Atlassian", True, 21),
    ("company-f", "rss", "Crunchbase News", "Developer platform startups see renewed funding round activity", "funding round", False, 28),
]


def run():
    db.init_db()
    db.upsert_companies(COMPANIES)

    inserted = 0
    for i, (company_id, source, source_name, headline, matched_term, is_competitor, hours_ago) in enumerate(DEMO_ITEMS):
        published = now - timedelta(hours=hours_ago)
        new = db.insert_news_item(
            {
                "company_id": company_id,
                "source": source,
                "source_name": source_name,
                "headline": headline,
                "url": f"https://example.com/demo-article-{i}",
                "published_at": published.strftime("%Y-%m-%d %H:%M"),
                "matched_term": matched_term,
                "is_competitor_mention": is_competitor,
                "snippet": f"Demo snippet for: {headline}",
            }
        )
        if new:
            inserted += 1

    print(f"Seeded {inserted} demo news items across {len(COMPANIES)} companies.")


if __name__ == "__main__":
    run()
