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
"""
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, send_from_directory

from news_watch.config import COMPANIES
from news_watch.db import get_conn as get_news_conn

BASE_DIR = Path(__file__).resolve().parent
DASHBOARD_DIR = BASE_DIR / "dashboard"
MIP_DB_PATH = BASE_DIR / "database" / "mip.db"

app = Flask(__name__)

FLAG_LABELS = {"risk": "Risk", "follow_on": "Follow-On", "on_track": "On Track"}


@app.route("/")
def dashboard():
    return send_from_directory(DASHBOARD_DIR, "index.html")


def _score_flag_for(name):
    """Latest flag/score/runway for a company, from Pair B's database/mip.db."""
    if not MIP_DB_PATH.exists():
        return None
    conn = sqlite3.connect(MIP_DB_PATH)
    try:
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
    finally:
        conn.close()
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


if __name__ == "__main__":
    # 5000 collides with macOS AirPlay Receiver; see news_watch/webapp.py.
    app.run(debug=True, port=8000)
