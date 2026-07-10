"""Entry point for the MIP dashboard.

Serves the dashboard UI (dashboard/index.html). Future API routes for
real portfolio/health-score/alert data should be added here as they're
built, replacing the mock data still hardcoded in the dashboard's JS.
"""
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from news_watch import db as news_db
from news_watch.config import COMPANIES as NEWS_COMPANIES
from news_watch.webapp import get_news_items, get_summary

BASE_DIR = Path(__file__).resolve().parent
DASHBOARD_DIR = BASE_DIR / "dashboard"

app = Flask(__name__)


@app.route("/")
def dashboard():
    return send_from_directory(DASHBOARD_DIR, "index.html")


@app.route("/api/news")
def api_news():
    """Assignment 4's news matches, for the dashboard's News Feed page."""
    news_db.init_db()
    company_id = request.args.get("company") or None
    return jsonify(
        {
            "companies": NEWS_COMPANIES,
            "summary": get_summary(),
            "items": get_news_items(company_id=company_id),
            "total_today": news_db.count_items_today(),
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
