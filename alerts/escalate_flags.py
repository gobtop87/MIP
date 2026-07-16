"""Assignment 6 entry point: escalate a company to 'risk' when it has a
recent, unhandled high-urgency alert, even if its financials alone
wouldn't put it there. Run after alerts.generate_alerts:

    python -m alerts.escalate_flags

Bridges the two databases the same way app.py already does: an alert's
company_id is a news_watch.config.COMPANIES string id (e.g. "nexahealth");
that maps to a name ("NexaHealth"), which is looked up in database/mip.db's
companies table (a separate, auto-generated integer id) to get the row this
script actually writes a flag change against.
"""
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alerts import db as alerts_db
from database.db import get_conn as get_mip_conn
from news_watch.config import COMPANIES

COMPANIES_BY_ID = {c["id"]: c for c in COMPANIES}

# =============================================================================
# PROVISIONAL — no spec exists yet for how long a high-urgency alert should
# count as "recent" before it's ignored. Chosen to match fade_score.py's own
# 30-day grace period, so the two escalation paths (stale financials, live
# alert) treat "recent" the same way. Replace once a real policy exists.
# =============================================================================
RECENT_ALERT_WINDOW_DAYS = 30


def run(as_of_date=None):
    alerts_db.init_db()  # ensures applied_to_flag exists even if generate_alerts hasn't run yet

    as_of_date = as_of_date or date.today()
    since = datetime.combine(as_of_date - timedelta(days=RECENT_ALERT_WINDOW_DAYS), datetime.min.time())
    since_iso = since.strftime("%Y-%m-%d %H:%M:%S")

    candidates = alerts_db.unescalated_high_urgency_alerts(since_iso)
    escalated = 0
    skipped_unmapped = 0

    for alert in candidates:
        company = COMPANIES_BY_ID.get(alert["company_id"])
        if not company:
            skipped_unmapped += 1
            continue

        with get_mip_conn() as conn:
            row = conn.execute(
                "SELECT id, flag FROM companies WHERE name = ?", (company["name"],)
            ).fetchone()
            if not row:
                skipped_unmapped += 1
                continue  # company hasn't been seeded into mip.db yet
            company_row_id, old_flag = row

            if old_flag != "risk":
                reason = f"Flagged as risk: {alert['message']}"
                conn.execute(
                    "UPDATE companies SET flag = 'risk', flag_reason = ? WHERE id = ?",
                    (reason, company_row_id),
                )
                conn.execute(
                    """INSERT INTO flag_history (company_id, old_flag, new_flag, reason, as_of_date)
                       VALUES (?, ?, 'risk', ?, ?)""",
                    (company_row_id, old_flag, reason, as_of_date.isoformat()),
                )
                escalated += 1

        alerts_db.mark_alert_applied(alert["id"])

    print(
        f"Checked {len(candidates)} recent high-urgency alert(s) from the last "
        f"{RECENT_ALERT_WINDOW_DAYS} days."
    )
    print(f"  {escalated} company/companies escalated to risk.")
    if skipped_unmapped:
        print(f"  {skipped_unmapped} alert(s) skipped (company not yet in database/mip.db).")


if __name__ == "__main__":
    run()
