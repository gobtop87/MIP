"""Entry point for the MIP dashboard.

Serves the dashboard UI (dashboard/index.html) and JSON API routes that join
live data from three previously-separate modules by company name, since none
of them share an ID scheme:
  - database/mip.db     (Pair B, Assignments 1+3: score, flag, flag_reason, runway)
  - news_watch/news.db  (Assignment 4: news_items)
  - news_watch/news.db  (Assignment 5, same file: alerts)

news_watch/config.py's COMPANIES list is the single source of truth for
company id <-> name, since the dashboard's own IDs (nexahealth, gridlock,
...) were adopted there specifically so this layer needs no separate
mapping table.

/api/companies backs the "Morning Dashboard" page (per-company flag, score,
why-flagged reason, runway, and a short recent-news/alerts preview).
/api/news backs the standalone "News Feed" page (all of Assignment 4's
matched news items, filterable by company) — it reuses news_watch/webapp.py's
query functions rather than duplicating them.
"""
import sqlite3
from datetime import date
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from database.db import DB_PATH as MIP_DB_PATH
from database.db import get_conn as get_mip_conn
from database.db import init_db as init_mip_db
from database.flag_reason import generate_flag_reason
from database.health_score import calculate_health_score, flag_from_score
from news_watch import db as news_db
from news_watch.config import COMPANIES
from news_watch.db import get_conn as get_news_conn
from news_watch.webapp import get_news_items, get_summary

BASE_DIR = Path(__file__).resolve().parent
DASHBOARD_DIR = BASE_DIR / "dashboard"

app = Flask(__name__)

FLAG_LABELS = {"risk": "Risk", "follow_on": "Follow-On", "on_track": "On Track"}
COMPANIES_BY_ID = {c["id"]: c for c in COMPANIES}

# Same thresholds fade_score.py's flag_from_faded_score uses for a company's
# overall status. Duplicated rather than imported: fade_score.py uses
# script-style bare imports (`from db import ...`) that only resolve when
# it's run directly (`python3 database/fade_score.py`), not when imported as
# database.fade_score from here.
COMPANY_FLAG_THRESHOLDS = {"risk_below": 35, "follow_on_above": 75}


def _company_flag_from_score(score):
    if score < COMPANY_FLAG_THRESHOLDS["risk_below"]:
        return "risk"
    elif score > COMPANY_FLAG_THRESHOLDS["follow_on_above"]:
        return "follow_on"
    return "on_track"


@app.route("/")
def dashboard():
    return send_from_directory(DASHBOARD_DIR, "index.html")


def _score_flag_for(name):
    """Latest flag/score/runway for a company, from Pair B's database/mip.db."""
    if not MIP_DB_PATH.exists():
        return None
    with get_mip_conn() as conn:
        row = conn.execute(
            """
            SELECT c.flag, c.flag_reason, s.score, mm.runway_months
            FROM companies c
            LEFT JOIN scores s ON s.company_id = c.id
            LEFT JOIN monthly_metrics mm ON mm.id = s.metric_id
            WHERE c.name = ?
            """,
            (name,),
        ).fetchone()
    if not row or row[0] is None:
        return None
    flag, flag_reason, score, runway_months = row
    return {"flag": flag, "flag_reason": flag_reason, "score": score, "runway_months": runway_months}


def _news_for(company_id, limit=8):
    with get_news_conn() as conn:
        rows = conn.execute(
            """
            SELECT headline, url, source_name, published_at, is_competitor_mention, matched_term
            FROM news_items WHERE company_id = ?
            ORDER BY fetched_at DESC LIMIT ?
            """,
            (company_id, limit),
        ).fetchall()
    return [
        {
            "headline": r[0],
            "url": r[1],
            "source_name": r[2],
            "published_at": r[3],
            "is_competitor_mention": bool(r[4]),
            "matched_term": r[5],
        }
        for r in rows
    ]


def _alerts_for(company_id, limit=5):
    with get_news_conn() as conn:
        try:
            rows = conn.execute(
                """
                SELECT a.urgency, a.message, n.url
                FROM alerts a JOIN news_items n ON n.id = a.news_item_id
                WHERE a.company_id = ?
                ORDER BY a.created_at DESC LIMIT ?
                """,
                (company_id, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            return []  # alerts table doesn't exist until alerts.generate_alerts has run
    return [{"urgency": r[0], "message": r[1], "url": r[2]} for r in rows]


@app.route("/api/companies")
def api_companies():
    result = []
    for c in COMPANIES:
        entry = {"id": c["id"], "name": c["name"]}
        score_flag = _score_flag_for(c["name"])
        if score_flag:
            entry["flag"] = score_flag["flag"]
            entry["flagLbl"] = FLAG_LABELS.get(score_flag["flag"], score_flag["flag"])
            entry["score"] = round(score_flag["score"]) if score_flag["score"] is not None else None
            if score_flag["flag_reason"]:
                entry["why"] = f"<b>Why flagged:</b> {score_flag['flag_reason']}"
            if score_flag["runway_months"] is not None:
                runway_mo = round(score_flag["runway_months"], 1)
                entry["runwayMo"] = runway_mo
                entry["runway"] = f"{runway_mo:g} mo"
        entry["news"] = _news_for(c["id"])
        entry["alerts"] = _alerts_for(c["id"])
        result.append(entry)
    return jsonify(result)


def _get_or_create_company(conn, name, industry):
    row = conn.execute("SELECT id FROM companies WHERE name = ?", (name,)).fetchone()
    if row:
        return row[0]
    cur = conn.execute(
        "INSERT INTO companies (name, industry) VALUES (?, ?)", (name, industry)
    )
    return cur.lastrowid


@app.route("/api/companies/<company_id>/metrics", methods=["POST"])
def update_company_metrics(company_id):
    """
    Manually edit a company's monthly financials (revenue, burn, cash,
    growth) and recompute its score/flag from them, same as a real monthly
    report would. Writes to database/mip.db so the edit persists.
    """
    company = COMPANIES_BY_ID.get(company_id)
    if not company:
        return jsonify({"error": f"Unknown company id '{company_id}'"}), 404

    data = request.get_json(silent=True) or {}
    try:
        revenue = float(data["revenue"])
        burn_rate = float(data["burn_rate"])
        cash_balance = float(data["cash_balance"])
        growth_rate = float(data["growth_rate"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "revenue, burn_rate, cash_balance, and growth_rate are required numbers"}), 400
    if burn_rate <= 0:
        return jsonify({"error": "burn_rate must be greater than 0"}), 400

    runway_months = cash_balance / burn_rate
    today = date.today().isoformat()

    if not MIP_DB_PATH.exists():
        init_mip_db()

    with get_mip_conn() as conn:
        company_row_id = _get_or_create_company(conn, company["name"], company.get("sector"))

        conn.execute(
            """INSERT INTO monthly_metrics
               (company_id, report_date, revenue, burn_rate, cash_balance, runway_months, growth_rate)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(company_id, report_date) DO UPDATE SET
                   revenue = excluded.revenue,
                   burn_rate = excluded.burn_rate,
                   cash_balance = excluded.cash_balance,
                   runway_months = excluded.runway_months,
                   growth_rate = excluded.growth_rate""",
            (company_row_id, today, revenue, burn_rate, cash_balance, runway_months, growth_rate),
        )
        metric_id = conn.execute(
            "SELECT id FROM monthly_metrics WHERE company_id = ? AND report_date = ?",
            (company_row_id, today),
        ).fetchone()[0]

        # health_score.py's own on_track/watch/at_risk vocabulary — stored
        # only on scores/score_history, separate from the company-level
        # risk/on_track/follow_on flag below (see database/README.md).
        score = calculate_health_score(revenue, burn_rate, runway_months, growth_rate)
        report_flag = flag_from_score(score)

        conn.execute(
            """INSERT INTO scores (company_id, metric_id, score, flag)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(company_id) DO UPDATE SET
                   metric_id = excluded.metric_id,
                   score = excluded.score,
                   flag = excluded.flag,
                   computed_at = datetime('now')""",
            (company_row_id, metric_id, score, report_flag),
        )
        conn.execute(
            """INSERT INTO score_history (company_id, metric_id, score, flag, source, as_of_date)
               VALUES (?, ?, ?, ?, 'report', ?)""",
            (company_row_id, metric_id, score, report_flag, today),
        )

        # A brand-new report is 0 days old, so fade_score.py's grace period
        # means no fade penalty applies — the company-level flag is just
        # this score run through the same thresholds the daily fade job uses.
        company_flag = _company_flag_from_score(score)
        reason = generate_flag_reason(
            company_flag, False, 0, revenue, burn_rate, runway_months, growth_rate
        )
        old_flag = conn.execute(
            "SELECT flag FROM companies WHERE id = ?", (company_row_id,)
        ).fetchone()[0]
        if old_flag != company_flag:
            conn.execute(
                """INSERT INTO flag_history (company_id, old_flag, new_flag, reason, as_of_date)
                   VALUES (?, ?, ?, ?, ?)""",
                (company_row_id, old_flag, company_flag, reason, today),
            )
        conn.execute(
            "UPDATE companies SET flag = ?, flag_reason = ? WHERE id = ?",
            (company_flag, reason, company_row_id),
        )

    runway_mo = round(runway_months, 1)
    return jsonify(
        {
            "id": company_id,
            "score": round(score),
            "flag": company_flag,
            "flagLbl": FLAG_LABELS.get(company_flag, company_flag),
            "why": f"<b>Why flagged:</b> {reason}",
            "runwayMo": runway_mo,
            "runway": f"{runway_mo:g} mo",
        }
    )


@app.route("/api/news")
def api_news():
    """Assignment 4's news matches, for the dashboard's News Feed page."""
    news_db.init_db()
    company_id = request.args.get("company") or None
    return jsonify(
        {
            "companies": COMPANIES,
            "summary": get_summary(),
            "items": get_news_items(company_id=company_id),
            "total_today": news_db.count_items_today(),
        }
    )


if __name__ == "__main__":
    # 5000 collides with macOS AirPlay Receiver; see news_watch/webapp.py.
    app.run(debug=True, port=8000)
