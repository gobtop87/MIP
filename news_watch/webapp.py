"""Web dashboard for Assignment 4: shows companies and the news items
matched for them. Reads straight from news_watch/news.db.

Run:
    ./venv/bin/python -m news_watch.webapp
Then open http://localhost:8000
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, render_template, request

from news_watch import db
from news_watch.config import COMPANIES

app = Flask(__name__, template_folder="templates")

COMPANY_LOOKUP = {c["id"]: c for c in COMPANIES}


def get_summary():
    with db.get_conn() as conn:
        rows = conn.execute(
            """
            SELECT company_id, COUNT(*) AS total,
                   SUM(is_competitor_mention) AS competitor_mentions
            FROM news_items
            GROUP BY company_id
            """
        ).fetchall()
    return {r[0]: {"total": r[1], "competitor_mentions": r[2] or 0} for r in rows}


def get_news_items(company_id=None, limit=300):
    query = """
        SELECT company_id, source, source_name, headline, url, published_at,
               matched_term, is_competitor_mention, fetched_at
        FROM news_items
    """
    params = ()
    if company_id:
        query += " WHERE company_id = ?"
        params = (company_id,)
    query += " ORDER BY fetched_at DESC, published_at DESC LIMIT ?"
    params = params + (limit,)

    with db.get_conn() as conn:
        rows = conn.execute(query, params).fetchall()

    items = []
    for r in rows:
        items.append(
            {
                "company_id": r[0],
                "company_name": COMPANY_LOOKUP.get(r[0], {}).get("name", r[0]),
                "source": r[1],
                "source_name": r[2],
                "headline": r[3],
                "url": r[4],
                "published_at": r[5],
                "matched_term": r[6],
                "is_competitor_mention": bool(r[7]),
                "fetched_at": r[8],
            }
        )
    return items


@app.route("/")
def dashboard():
    db.init_db()
    selected = request.args.get("company") or None
    summary = get_summary()
    items = get_news_items(company_id=selected)
    total_today = db.count_items_today()

    return render_template(
        "dashboard.html",
        companies=COMPANIES,
        summary=summary,
        items=items,
        selected=selected,
        total_today=total_today,
    )


if __name__ == "__main__":
    db.init_db()
    # 5000 collides with macOS AirPlay Receiver (returns its own 403 before
    # Flask ever sees the request), so use 8000 instead.
    app.run(debug=True, port=8000)
