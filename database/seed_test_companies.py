"""
Adds 6 clearly-fake companies (TestCo A-F) to the local SQLite prototype,
so there's data to hand-verify the scoring formula against (Assignment 2,
step 3: pick a few companies, work out the expected score by hand, check
this program agrees) without touching the 6 real portfolio companies
build_db.py seeds.

Names are deliberately unrealistic ("TestCo A", ...) so they can't be
mistaken for real portfolio companies later. Numbers are made up but
realistic, and deliberately spread across the flag buckets
(risk / watch / on_track) so there's something interesting to check by
hand in each bucket.

Safe to re-run: any existing TestCo rows (and their metrics/scores/history)
are deleted and reseeded from scratch first.

Run after database/build_db.py:
    python3 database/seed_test_companies.py
"""

from build_db import print_company_data, seed_company
from db import get_conn

# report_date, revenue, burn_rate, cash_balance, growth_rate
TEST_COMPANIES = [
    {
        # Solid, well-capitalized: 12mo runway, decent growth, burns less
        # than it makes. Expect a healthy on_track score.
        "name": "TestCo A",
        "industry": "Test / SaaS",
        "founded_year": 2023,
        "metrics": [("2026-07-01", 500_000, 300_000, 3_600_000, 0.12)],
    },
    {
        # Barely any cash left, burning almost 2x revenue, shrinking.
        # Expect a low, at_risk score.
        "name": "TestCo B",
        "industry": "Test / Consumer",
        "founded_year": 2022,
        "metrics": [("2026-07-01", 80_000, 150_000, 200_000, -0.05)],
    },
    {
        # Deep runway, strong growth, efficient burn. Expect a near-max score.
        "name": "TestCo C",
        "industry": "Test / Fintech",
        "founded_year": 2021,
        "metrics": [("2026-07-01", 1_200_000, 400_000, 10_000_000, 0.20)],
    },
    {
        # Middling on every dimension. Expect a score in the "watch" band.
        "name": "TestCo D",
        "industry": "Test / Logistics",
        "founded_year": 2023,
        "metrics": [("2026-07-01", 300_000, 280_000, 2_000_000, 0.05)],
    },
    {
        # Short runway (1.5mo), burning 2x revenue, shrinking. Expect a
        # bottom-of-the-scale at_risk score.
        "name": "TestCo E",
        "industry": "Test / Hardware",
        "founded_year": 2020,
        "metrics": [("2026-07-01", 150_000, 300_000, 450_000, -0.02)],
    },
    {
        # Comfortable runway, modest growth, reasonable burn. Expect a solid
        # on_track score.
        "name": "TestCo F",
        "industry": "Test / Healthcare",
        "founded_year": 2022,
        "metrics": [("2026-07-01", 600_000, 350_000, 5_000_000, 0.08)],
    },
]


def _delete_existing_test_companies(conn):
    names = [c["name"] for c in TEST_COMPANIES]
    placeholders = ",".join("?" * len(names))
    ids = [
        row[0]
        for row in conn.execute(
            f"SELECT id FROM companies WHERE name IN ({placeholders})", names
        ).fetchall()
    ]
    if not ids:
        return
    id_placeholders = ",".join("?" * len(ids))
    for table in ("score_history", "scores", "flag_history", "monthly_metrics"):
        conn.execute(f"DELETE FROM {table} WHERE company_id IN ({id_placeholders})", ids)
    conn.execute(f"DELETE FROM companies WHERE id IN ({id_placeholders})", ids)


def seed_test_companies(conn):
    _delete_existing_test_companies(conn)
    company_ids = []
    for company in TEST_COMPANIES:
        company_id = seed_company(
            conn, company["name"], company["industry"], company["founded_year"], company["metrics"]
        )
        company_ids.append(company_id)
    return company_ids


if __name__ == "__main__":
    with get_conn() as connection:
        company_ids = seed_test_companies(connection)
        print(f"Seeded {len(company_ids)} test companies into database/mip.db\n")
        for company_id, company in zip(company_ids, TEST_COMPANIES):
            print_company_data(
                connection, company_id, company["name"], company["industry"], company["founded_year"]
            )
