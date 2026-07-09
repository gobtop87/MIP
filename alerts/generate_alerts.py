"""Assignment 5 entry point: filter Assignment 4's news_items for relevance
and write short urgency-rated alerts. No external API — pure rules over
data already in news.db.

Usage:
    python -m alerts.generate_alerts
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alerts import db as alerts_db
from alerts.messages import build_alert_message
from alerts.relevance import is_relevant
from alerts.urgency import rate_urgency
from news_watch.config import COMPANIES


def run():
    alerts_db.init_db()
    companies_by_id = {c["id"]: c for c in COMPANIES}

    candidates = alerts_db.unalerted_news_items()
    created = 0
    skipped_irrelevant = 0

    for item in candidates:
        company = companies_by_id.get(item["company_id"])
        if not company:
            continue
        if not is_relevant(item, company):
            skipped_irrelevant += 1
            continue
        alert = {
            "news_item_id": item["id"],
            "company_id": item["company_id"],
            "urgency": rate_urgency(item),
            "message": build_alert_message(item, company),
        }
        if alerts_db.insert_alert(alert):
            created += 1

    print(f"Checked {len(candidates)} new news item(s).")
    print(f"  {created} alert(s) created, {skipped_irrelevant} filtered out as not relevant.")
    print(f"  Totals by urgency: {alerts_db.count_alerts_by_urgency()}")


if __name__ == "__main__":
    run()
