"""
Daily score-fading job.

Meant to run once a day (see scheduling note at the bottom of this file).
For every company it looks at the real score in `scores` (computed from
their most recent monthly_metrics report) and how long it's been since that
report, applies the fade schedule, and writes today's faded score/flag to
`score_history` as a 'fade' row.

The real `scores` row is never touched, and the fade is recomputed from
scratch every run (base score + days-since-report), so:
  - running this twice on the same day is a no-op (same inputs -> same
    output -> the UNIQUE(company_id, as_of_date, source) constraint just
    replaces the row instead of double-penalizing)
  - a company that files a fresh report immediately fades back to its full
    score, because fade is never written back onto the base score.

Run: python3 database/fade_score.py
"""

import os
import sqlite3
from datetime import date, datetime

from health_score import flag_from_score

DB_PATH = os.path.join(os.path.dirname(__file__), "mip.db")

# =============================================================================
# PROVISIONAL — replace with the real fade schedule from the instructions doc
# once one exists. No such spec was found in this repo as of this writing.
# =============================================================================
PROVISIONAL_FADE_SCHEDULE = {
    "grace_period_days": 30,   # no penalty within this many days of the report
    "penalty_per_week": 5,     # points subtracted per full week past the grace period
    "min_score": 0,            # score floor
}


def calculate_faded_score(base_score, report_date, as_of_date, schedule=PROVISIONAL_FADE_SCHEDULE):
    """
    Apply the fade schedule to `base_score` given how long it's been since
    `report_date`, as of `as_of_date`. Pure function of its inputs — no
    hidden state — so it's safe to call repeatedly for the same day.
    """
    days_since_report = (as_of_date - report_date).days
    grace_period = schedule["grace_period_days"]

    if days_since_report <= grace_period:
        return base_score

    weeks_overdue = (days_since_report - grace_period) // 7
    penalty = weeks_overdue * schedule["penalty_per_week"]

    return max(base_score - penalty, schedule["min_score"])


def run_fade_job(conn, as_of_date=None):
    as_of_date = as_of_date or date.today()

    rows = conn.execute(
        """SELECT s.company_id, s.metric_id, s.score, mm.report_date
           FROM scores s
           JOIN monthly_metrics mm ON mm.id = s.metric_id"""
    ).fetchall()

    results = []
    for company_id, metric_id, base_score, report_date_str in rows:
        report_date = datetime.strptime(report_date_str, "%Y-%m-%d").date()
        faded_score = calculate_faded_score(base_score, report_date, as_of_date)
        faded_flag = flag_from_score(faded_score)

        conn.execute(
            """INSERT INTO score_history
               (company_id, metric_id, score, flag, source, as_of_date)
               VALUES (?, ?, ?, ?, 'fade', ?)
               ON CONFLICT(company_id, as_of_date, source)
               DO UPDATE SET score = excluded.score,
                             flag = excluded.flag,
                             metric_id = excluded.metric_id,
                             computed_at = datetime('now')""",
            (company_id, metric_id, faded_score, faded_flag, as_of_date.isoformat()),
        )
        results.append((company_id, base_score, faded_score, faded_flag, report_date))

    conn.commit()
    return results


def print_results(conn, results, as_of_date):
    print(f"Fade job run for {as_of_date.isoformat()}\n")
    for company_id, base_score, faded_score, faded_flag, report_date in results:
        name = conn.execute(
            "SELECT name FROM companies WHERE id = ?", (company_id,)
        ).fetchone()[0]
        days_since = (as_of_date - report_date).days
        print(
            f"  {name:<20} last report {report_date}  ({days_since:>3}d ago)  "
            f"base={base_score:5.1f}  faded={faded_score:5.1f}  flag={faded_flag}"
        )


if __name__ == "__main__":
    connection = sqlite3.connect(DB_PATH)
    today = date.today()
    fade_results = run_fade_job(connection, today)
    print_results(connection, fade_results, today)
    connection.close()
