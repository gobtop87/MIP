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
    ("nexahealth", "rss", "TechCrunch", "Teladoc reports quarterly earnings miss", "Teladoc", True, 2),
    ("nexahealth", "newsapi", "Reuters", "Hims & Hers faces FDA scrutiny over compounded drugs", "Hims & Hers", True, 7),
    ("nexahealth", "rss", "TechCrunch", "Cerebral settles lawsuit over prescribing practices", "lawsuit", True, 12),
    ("nexahealth", "rss", "Crunchbase News", "Amwell announces new funding round", "Amwell", True, 17),
    ("nexahealth", "rss", "Ars Technica", "Telehealth clinical trial shows promising results", "clinical trial", False, 25),

    ("gridlock", "rss", "The Verge", "CrowdStrike discloses vulnerability in endpoint agent", "vulnerability", True, 3),
    ("gridlock", "sec_edgar", "SEC EDGAR", "Palo Alto Networks Inc filed 8-K mentioning \"Palo Alto Networks\"", "Palo Alto Networks", True, 8),
    ("gridlock", "rss", "TechCrunch", "SentinelOne raises new funding round", "funding round", True, 13),
    ("gridlock", "newsapi", "Reuters", "Okta faces lawsuit over 2025 breach disclosure", "lawsuit", True, 19),
    ("gridlock", "rss", "Ars Technica", "Ransomware group claims new victim among Fortune 500", "ransomware", False, 22),

    ("pathwise", "rss", "VentureBeat", "OpenAI announces new foundation model with longer context", "OpenAI", True, 1),
    ("pathwise", "newsapi", "The Verge", "Anthropic raises Series C at higher valuation", "Anthropic", True, 6),
    ("pathwise", "rss", "TechCrunch", "Scale AI acquired by data labeling rival", "acquisition", True, 11),
    ("pathwise", "rss", "Ars Technica", "Databricks reports data breach affecting enterprise customers", "data breach", True, 18),
    ("pathwise", "rss", "Crunchbase News", "Hugging Face partnership brings open models to enterprise", "Hugging Face", True, 24),
    ("pathwise", "newsapi", "Reuters", "GPU shortage continues to squeeze AI infra startups", "GPU", False, 30),

    ("solarvault", "rss", "TechCrunch", "Sunrun reports strong quarterly installs", "Sunrun", True, 4),
    ("solarvault", "rss", "Crunchbase News", "Tesla Energy announces new battery storage partnership", "Tesla Energy", True, 10),
    ("solarvault", "newsapi", "Reuters", "SunPower lays off staff amid sector slowdown", "layoffs", True, 16),
    ("solarvault", "rss", "VentureBeat", "Enphase Energy raises new funding round", "funding round", True, 23),
    ("solarvault", "rss", "TechCrunch", "Solar sector sees renewed investor interest", "solar", False, 29),

    ("cognify", "rss", "TechCrunch", "Tempus acquires clinical data startup", "Tempus", True, 5),
    ("cognify", "newsapi", "Reuters", "Komodo Health announces new funding round", "Komodo Health", True, 14),
    ("cognify", "rss", "Crunchbase News", "Innovaccer discloses data breach affecting customers", "data breach", True, 20),
    ("cognify", "rss", "The Verge", "Butterfly Network reports diagnostics platform outage", "diagnostics", True, 26),

    ("vaultnet", "rss", "TechCrunch", "Zscaler raises new funding round at higher valuation", "Zscaler", True, 1),
    ("vaultnet", "newsapi", "Reuters", "Cloudflare reports major outage affecting customers", "Cloudflare", True, 6),
    ("vaultnet", "rss", "The Verge", "Fortinet acquires zero trust startup", "acquires", True, 15),
    ("vaultnet", "sec_edgar", "SEC EDGAR", "Rapid7 Inc filed 8-K mentioning \"Rapid7\"", "Rapid7", True, 21),
    ("vaultnet", "rss", "Crunchbase News", "Zero trust security sees renewed funding round activity", "zero trust", False, 28),
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
