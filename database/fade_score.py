"""
Daily score-fading job.

Meant to run once a day (see scheduling note at the bottom of this file).
For every company it looks at the real score in `scores` (computed from
their most recent monthly_metrics report) and how long it's been since that
report, applies the fade schedule, and writes today's faded score/flag to
`score_history` as a 'fade' row. It then labels the company from that faded
score ('risk' / 'on_track' / 'follow_on'), stores the label and a plain-
English reason on the company record, and logs a `flag_history` row
whenever that label actually changes.

The real `scores` row is never touched, and the fade is recomputed from
scratch every run (base score + days-since-report), so:
  - running this twice on the same day is a no-op (same inputs -> same
    output -> the UNIQUE(company_id, as_of_date, source) constraint just
    replaces the row instead of double-penalizing, and the flag compare is
    against the flag already stored from the first run, so no duplicate
    "change" gets logged either)
  - a company that files a fresh report immediately fades back to its full
    score, because fade is never written back onto the base score.

Run: python3 database/fade_score.py
"""

from datetime import date, datetime

from db import get_conn
from flag_reason import generate_flag_reason

# Thresholds for labeling a company from its faded score. Given directly
# (not a placeholder), so no PROVISIONAL marker needed.
FLAG_THRESHOLDS = {
    "risk_below": 35,       # faded score < 35      -> 'risk'
    "follow_on_above": 75,  # faded score > 75      -> 'follow_on'
    # anything in between                            -> 'on_track'
}

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


def flag_from_faded_score(faded_score, thresholds=FLAG_THRESHOLDS):
    """Label a company from its faded score: 'risk' | 'on_track' | 'follow_on'."""
    if faded_score < thresholds["risk_below"]:
        return "risk"
    elif faded_score > thresholds["follow_on_above"]:
        return "follow_on"
    else:
        return "on_track"


def run_fade_job(conn, as_of_date=None):
    as_of_date = as_of_date or date.today()

    rows = conn.execute(
        """SELECT s.company_id, s.metric_id, s.score, mm.report_date,
                  mm.revenue, mm.burn_rate, mm.runway_months, mm.growth_rate
           FROM scores s
           JOIN monthly_metrics mm ON mm.id = s.metric_id"""
    ).fetchall()

    results = []
    for (company_id, metric_id, base_score, report_date_str,
         revenue, burn_rate, runway_months, growth_rate) in rows:
        report_date = datetime.strptime(report_date_str, "%Y-%m-%d").date()
        days_since_report = (as_of_date - report_date).days
        faded_score = calculate_faded_score(base_score, report_date, as_of_date)
        faded_flag = flag_from_faded_score(faded_score)

        # If fading alone knocked the flag into a worse bucket than the real
        # metrics would justify on their own, staleness is the actual cause.
        base_flag = flag_from_faded_score(base_score)
        is_stale = base_flag != faded_flag

        reason = generate_flag_reason(
            faded_flag, is_stale, days_since_report,
            revenue, burn_rate, runway_months, growth_rate,
        )

        conn.execute(
            """INSERT INTO score_history
               (company_id, metric_id, score, flag, source, as_of_date, reason)
               VALUES (?, ?, ?, ?, 'fade', ?, ?)
               ON CONFLICT(company_id, as_of_date, source)
               DO UPDATE SET score = excluded.score,
                             flag = excluded.flag,
                             metric_id = excluded.metric_id,
                             reason = excluded.reason,
                             computed_at = datetime('now')""",
            (company_id, metric_id, faded_score, faded_flag, as_of_date.isoformat(), reason),
        )

        old_flag = conn.execute(
            "SELECT flag FROM companies WHERE id = ?", (company_id,)
        ).fetchone()[0]

        flag_changed = old_flag != faded_flag
        if flag_changed:
            conn.execute(
                """INSERT INTO flag_history (company_id, old_flag, new_flag, reason, as_of_date)
                   VALUES (?, ?, ?, ?, ?)""",
                (company_id, old_flag, faded_flag, reason, as_of_date.isoformat()),
            )
            conn.execute(
                "UPDATE companies SET flag = ?, flag_reason = ? WHERE id = ?",
                (faded_flag, reason, company_id),
            )
        else:
            conn.execute(
                "UPDATE companies SET flag_reason = ? WHERE id = ?", (reason, company_id)
            )

        results.append(
            (company_id, base_score, faded_score, faded_flag, report_date, flag_changed, reason)
        )

    conn.commit()
    return results


def print_results(conn, results, as_of_date):
    print(f"Fade job run for {as_of_date.isoformat()}\n")
    for company_id, base_score, faded_score, faded_flag, report_date, flag_changed, reason in results:
        name = conn.execute(
            "SELECT name FROM companies WHERE id = ?", (company_id,)
        ).fetchone()[0]
        days_since = (as_of_date - report_date).days
        change_note = "  <- status changed" if flag_changed else ""
        print(
            f"  {name:<20} last report {report_date}  ({days_since:>3}d ago)  "
            f"base={base_score:5.1f}  faded={faded_score:5.1f}  flag={faded_flag}{change_note}"
        )
        print(f"      {reason}")


if __name__ == "__main__":
    today = date.today()
    with get_conn() as connection:
        fade_results = run_fade_job(connection, today)
        print_results(connection, fade_results, today)
