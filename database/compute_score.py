"""
Assignment 2: reads a company's latest monthly_metrics report, runs it
through calculate_health_score() (Assignment 1's formula), and writes the
result back as that company's current score in `scores` — plus an
append-only copy in `score_history` (source='report') so past calculations
are never overwritten, only ever added to.

Uses database/db.py for all database access, so pointing this at Supabase
later is a one-file change (see db.py).

Run for a single company:
    python3 database/compute_score.py <company_id>

Run for every company:
    python3 database/compute_score.py --all
"""

import argparse

from db import get_conn
from health_score import calculate_health_score, flag_from_score


def _latest_metric(conn, company_id):
    """Most recent monthly_metrics row for a company, or None if it has none yet."""
    return conn.execute(
        """SELECT id, report_date, revenue, burn_rate, runway_months, growth_rate
           FROM monthly_metrics
           WHERE company_id = ?
           ORDER BY report_date DESC
           LIMIT 1""",
        (company_id,),
    ).fetchone()


def _company_exists(conn, company_id):
    return conn.execute("SELECT 1 FROM companies WHERE id = ?", (company_id,)).fetchone() is not None


def compute_score_for_company(conn, company_id):
    """
    Score `company_id` from its latest monthly_metrics report, upsert
    `scores` (the current snapshot), and append a new `score_history`
    ('report') row logging this calculation.

    Returns (score, flag), or None if the company has no metrics reported
    yet. Every call appends a fresh, timestamped history row — even calling
    this twice in a row for the same company adds two rows, never
    overwriting the first.
    """
    metric = _latest_metric(conn, company_id)
    if metric is None:
        return None
    metric_id, report_date, revenue, burn_rate, runway_months, growth_rate = metric

    # The one call that will change when the real formula lands.
    score = calculate_health_score(revenue, burn_rate, runway_months, growth_rate)
    flag = flag_from_score(score)

    conn.execute(
        """INSERT INTO scores (company_id, metric_id, score, flag)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(company_id) DO UPDATE SET
               metric_id = excluded.metric_id,
               score = excluded.score,
               flag = excluded.flag,
               computed_at = datetime('now')""",
        (company_id, metric_id, score, flag),
    )
    # Always appends — every score calculation gets its own timestamped row,
    # never overwriting a previous one (even a repeat run for the same
    # company on the same day gets a new row here).
    conn.execute(
        """INSERT INTO score_history
           (company_id, metric_id, score, flag, source, as_of_date)
           VALUES (?, ?, ?, ?, 'report', ?)""",
        (company_id, metric_id, score, flag, report_date),
    )
    return score, flag


def compute_all(conn):
    """Score every company. Returns {company_id: (score, flag) or None}."""
    company_ids = [row[0] for row in conn.execute("SELECT id FROM companies ORDER BY id").fetchall()]
    return {company_id: compute_score_for_company(conn, company_id) for company_id in company_ids}


def _print_result(conn, company_id, result):
    name = conn.execute("SELECT name FROM companies WHERE id = ?", (company_id,)).fetchone()[0]
    if result is None:
        print(f"  {name:<20} no monthly_metrics reports yet — skipped")
        return
    score, flag = result
    print(f"  {name:<20} score={score:5.1f}  flag={flag}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "company_id", nargs="?", type=int, default=None,
        help="Score just this company, by its companies.id.",
    )
    parser.add_argument("--all", action="store_true", help="Score every company.")
    args = parser.parse_args()

    if args.company_id is None and not args.all:
        parser.error("pass a company id, or --all to score every company")
    if args.company_id is not None and args.all:
        parser.error("pass either a company id or --all, not both")

    with get_conn() as connection:
        if args.all:
            results = compute_all(connection)
            print(f"Scored {len(results)} companies:\n")
            for company_id, result in results.items():
                _print_result(connection, company_id, result)
        else:
            if not _company_exists(connection, args.company_id):
                raise SystemExit(f"No company with id {args.company_id}")
            result = compute_score_for_company(connection, args.company_id)
            _print_result(connection, args.company_id, result)
