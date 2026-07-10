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

# The 6 real dashboard companies (dashboard/index.html), so this database and
# the live dashboard describe the same portfolio. `name` is the join key
# used by app.py's API routes to line this table up with news_watch/news.db
# and the dashboard's own company records — none of the three modules share
# an ID scheme, but all three agree on these names.
#
# Report dates are set within the fade job's 30-day grace period of "today"
# (see database/fade_score.py) so the seeded metrics alone determine each
# company's flag, without staleness fading distorting it. Metrics are
# hand-picked so calculate_health_score() lands each company in the same
# risk/on_track/follow_on bucket the dashboard's hardcoded UI already shows.
SEED_COMPANIES = [
    {
        "name": "NexaHealth",
        "industry": "Healthcare",
        "founded_year": 2020,
        "metrics": [
            # report_date, revenue, burn_rate, cash_balance, growth_rate
            ("2026-04-01", 120000, 140000, 560000, 0.020),
            ("2026-05-01", 118000, 145000, 415000, -0.017),
            ("2026-06-01", 112000, 150000, 265000, -0.051),
            ("2026-07-01", 105000, 155000, 110000, -0.063),
        ],
    },
    {
        "name": "GridLock AI",
        "industry": "Cybersecurity",
        "founded_year": 2021,
        "metrics": [
            ("2026-04-01", 200000, 210000, 650000, 0.010),
            ("2026-05-01", 195000, 215000, 435000, -0.025),
            ("2026-06-01", 188000, 220000, 215000, -0.036),
            ("2026-07-01", 180000, 225000, 90000, -0.044),
        ],
    },
    {
        "name": "PathWise",
        "industry": "AI / ML Infrastructure",
        "founded_year": 2022,
        "metrics": [
            ("2026-04-01", 2800000, 900000, 14000000, 0.140),
            ("2026-05-01", 3200000, 950000, 15500000, 0.143),
            ("2026-06-01", 3600000, 1000000, 17000000, 0.125),
            ("2026-07-01", 3900000, 1050000, 19000000, 0.100),
        ],
    },
    {
        "name": "SolarVault",
        "industry": "Clean Energy",
        "founded_year": 2019,
        "metrics": [
            ("2026-04-01", 1900000, 700000, 9000000, 0.090),
            ("2026-05-01", 2050000, 720000, 9600000, 0.079),
            ("2026-06-01", 2200000, 740000, 10200000, 0.073),
            ("2026-07-01", 2350000, 760000, 10800000, 0.068),
        ],
    },
    {
        "name": "Cognify Health",
        "industry": "Healthcare",
        "founded_year": 2020,
        "metrics": [
            ("2026-04-01", 850000, 520000, 3200000, 0.045),
            ("2026-05-01", 880000, 530000, 3400000, 0.035),
            ("2026-06-01", 905000, 540000, 3550000, 0.028),
            ("2026-07-01", 930000, 550000, 3700000, 0.028),
        ],
    },
    {
        "name": "VaultNet",
        "industry": "Cybersecurity",
        "founded_year": 2018,
        "metrics": [
            ("2026-04-01", 1200000, 650000, 5000000, 0.050),
            ("2026-05-01", 1260000, 660000, 5250000, 0.050),
            ("2026-06-01", 1320000, 670000, 5500000, 0.048),
            ("2026-07-01", 1390000, 680000, 5750000, 0.053),
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
                """INSERT INTO score_history
                   (company_id, metric_id, score, flag, source, as_of_date)
                   VALUES (?, ?, ?, ?, 'report', ?)""",
                (company_id, metric_id, score, flag, report_date),
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
