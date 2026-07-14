"""
Imports one month's new numbers from a CSV into monthly_metrics.

This is the "simplest option" decided for Assignment 1 step 4: fill in a
spreadsheet, export/save as CSV, and import it — no custom form. Only three
raw numbers are typed in per company (revenue, burn_rate, cash_balance);
runway_months and growth_rate are derived automatically (growth_rate from
the company's previous monthly_metrics row, so nobody has to compute a %
change by hand each month).

Usage:
    python3 database/import_monthly_metrics.py [path/to/file.csv]

Defaults to monthly_metrics_template.csv in this directory. Required CSV
columns: company_name, report_date (YYYY-MM-DD), revenue, burn_rate,
cash_balance. Rows with a blank revenue/burn_rate/cash_balance are skipped
(so the template can be filled in company-by-company across the month).

Companies are matched by name and must already exist in `companies`. Running
this doesn't compute a new score/flag — that's Assignment 2/3's job; run
compute_score.py (then fade_score.py) afterward.
"""

import csv
import os
import sys

from db import get_conn

DEFAULT_CSV = os.path.join(os.path.dirname(__file__), "monthly_metrics_template.csv")


def _previous_revenue(conn, company_id, report_date):
    row = conn.execute(
        """SELECT revenue FROM monthly_metrics
           WHERE company_id = ? AND report_date < ?
           ORDER BY report_date DESC LIMIT 1""",
        (company_id, report_date),
    ).fetchone()
    return row[0] if row else None


def import_csv(conn, csv_path):
    imported, skipped = [], []

    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            name = row["company_name"].strip()
            report_date = row["report_date"].strip()

            if not row["revenue"].strip() or not row["burn_rate"].strip() or not row["cash_balance"].strip():
                skipped.append((name, report_date, "missing revenue/burn_rate/cash_balance"))
                continue

            company = conn.execute(
                "SELECT id FROM companies WHERE name = ?", (name,)
            ).fetchone()
            if not company:
                skipped.append((name, report_date, "no matching company"))
                continue
            company_id = company[0]

            revenue = float(row["revenue"])
            burn_rate = float(row["burn_rate"])
            cash_balance = float(row["cash_balance"])
            runway_months = cash_balance / burn_rate

            prev_revenue = _previous_revenue(conn, company_id, report_date)
            growth_rate = (revenue - prev_revenue) / prev_revenue if prev_revenue else 0.0

            conn.execute(
                """INSERT INTO monthly_metrics
                   (company_id, report_date, revenue, burn_rate, cash_balance,
                    runway_months, growth_rate)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(company_id, report_date) DO UPDATE SET
                       revenue = excluded.revenue,
                       burn_rate = excluded.burn_rate,
                       cash_balance = excluded.cash_balance,
                       runway_months = excluded.runway_months,
                       growth_rate = excluded.growth_rate""",
                (company_id, report_date, revenue, burn_rate, cash_balance,
                 runway_months, growth_rate),
            )
            imported.append((name, report_date, revenue, burn_rate, cash_balance, runway_months, growth_rate))

    conn.commit()
    return imported, skipped


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV

    with get_conn() as connection:
        imported_rows, skipped_rows = import_csv(connection, csv_path)

    print(f"Imported {len(imported_rows)} row(s) from {csv_path}:")
    for name, report_date, revenue, burn_rate, cash_balance, runway_months, growth_rate in imported_rows:
        print(
            f"  {name:<20} {report_date}  revenue=${revenue:,.0f}  burn=${burn_rate:,.0f}  "
            f"cash=${cash_balance:,.0f}  runway={runway_months:.1f}mo  growth={growth_rate:+.1%}"
        )

    if skipped_rows:
        print(f"\nSkipped {len(skipped_rows)} row(s):")
        for name, report_date, why in skipped_rows:
            print(f"  {name:<20} {report_date}  ({why})")
