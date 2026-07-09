"""
Builds and seeds the standalone SQLite prototype (database/mip.db), then
prints everything so you can see what got seeded.

Run: python3 database/build_db.py
"""

import os
import sqlite3

from health_score import calculate_health_score, flag_from_score

DB_PATH = os.path.join(os.path.dirname(__file__), "mip.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

# Four fake companies with four months of plausible metrics each. Numbers are
# hand-picked to show a mix of outcomes: one growing steadily, one stable,
# one slowly declining, and one clearly fading fast.
SEED_COMPANIES = [
    {
        "name": "Nimbus Analytics",
        "industry": "SaaS",
        "founded_year": 2021,
        "metrics": [
            # report_date, revenue, burn_rate, cash_balance, growth_rate
            ("2026-03-01", 180000, 90000, 900000, 0.090),
            ("2026-04-01", 196000, 92000, 950000, 0.089),
            ("2026-05-01", 214000, 95000, 1000000, 0.092),
            ("2026-06-01", 235000, 98000, 1050000, 0.098),
        ],
    },
    {
        "name": "Farmwise Robotics",
        "industry": "AgTech",
        "founded_year": 2019,
        "metrics": [
            ("2026-03-01", 90000, 70000, 490000, 0.030),
            ("2026-04-01", 92000, 71000, 419000, 0.022),
            ("2026-05-01", 93500, 72000, 347000, 0.016),
            ("2026-06-01", 95000, 73000, 274000, 0.016),
        ],
    },
    {
        "name": "Voltify",
        "industry": "EV Charging Hardware",
        "founded_year": 2020,
        "metrics": [
            ("2026-03-01", 150000, 140000, 700000, 0.060),
            ("2026-04-01", 148000, 150000, 560000, 0.020),
            ("2026-05-01", 140000, 155000, 405000, -0.020),
            ("2026-06-01", 130000, 160000, 245000, -0.070),
        ],
    },
    {
        "name": "Sparrow Health",
        "industry": "HealthTech",
        "founded_year": 2022,
        "metrics": [
            ("2026-03-01", 40000, 95000, 180000, -0.030),
            ("2026-04-01", 37000, 97000, 120000, -0.075),
            ("2026-05-01", 33000, 99000, 65000, -0.108),
            ("2026-06-01", 29000, 101000, 20000, -0.121),
        ],
    },
]


def build_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())

    for company in SEED_COMPANIES:
        cur = conn.execute(
            "INSERT INTO companies (name, industry, founded_year) VALUES (?, ?, ?)",
            (company["name"], company["industry"], company["founded_year"]),
        )
        company_id = cur.lastrowid

        latest_metric_id = None
        latest_score = None
        latest_flag = None

        for report_date, revenue, burn_rate, cash_balance, growth_rate in company["metrics"]:
            runway_months = cash_balance / burn_rate

            cur = conn.execute(
                """INSERT INTO monthly_metrics
                   (company_id, report_date, revenue, burn_rate, cash_balance,
                    runway_months, growth_rate)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (company_id, report_date, revenue, burn_rate, cash_balance,
                 runway_months, growth_rate),
            )
            metric_id = cur.lastrowid

            # The one call that will change when the real formula lands.
            score = calculate_health_score(revenue, burn_rate, runway_months, growth_rate)
            flag = flag_from_score(score)

            conn.execute(
                """INSERT INTO score_history (company_id, metric_id, score, flag)
                   VALUES (?, ?, ?, ?)""",
                (company_id, metric_id, score, flag),
            )

            latest_metric_id, latest_score, latest_flag = metric_id, score, flag

        conn.execute(
            """INSERT INTO scores (company_id, metric_id, score, flag)
               VALUES (?, ?, ?, ?)""",
            (company_id, latest_metric_id, latest_score, latest_flag),
        )

    conn.commit()
    return conn


def print_seeded_data(conn):
    companies = conn.execute("SELECT id, name, industry, founded_year FROM companies").fetchall()

    for company_id, name, industry, founded_year in companies:
        print(f"\n=== {name} ({industry}, founded {founded_year}) ===")

        print("  Monthly metrics:")
        metrics = conn.execute(
            """SELECT report_date, revenue, burn_rate, cash_balance, runway_months, growth_rate
               FROM monthly_metrics WHERE company_id = ? ORDER BY report_date""",
            (company_id,),
        ).fetchall()
        for report_date, revenue, burn_rate, cash_balance, runway_months, growth_rate in metrics:
            print(
                f"    {report_date}  revenue=${revenue:>9,.0f}  burn=${burn_rate:>8,.0f}  "
                f"cash=${cash_balance:>10,.0f}  runway={runway_months:5.2f}mo  "
                f"growth={growth_rate:+.1%}"
            )

        print("  Score history:")
        history = conn.execute(
            """SELECT mm.report_date, sh.score, sh.flag
               FROM score_history sh
               JOIN monthly_metrics mm ON mm.id = sh.metric_id
               WHERE sh.company_id = ? ORDER BY mm.report_date""",
            (company_id,),
        ).fetchall()
        for report_date, score, flag in history:
            print(f"    {report_date}  score={score:5.1f}  flag={flag}")

        current = conn.execute(
            "SELECT score, flag FROM scores WHERE company_id = ?", (company_id,)
        ).fetchone()
        print(f"  Current score/flag: {current[0]:.1f} / {current[1]}")


if __name__ == "__main__":
    connection = build_database()
    print(f"Built and seeded {DB_PATH}\n")
    print_seeded_data(connection)
    connection.close()
