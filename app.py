"""Entry point for the MIP dashboard.

Serves the dashboard UI (dashboard/index.html). Future API routes for
real portfolio/news/alert data should be added here as they're built,
replacing the mock data currently hardcoded in the dashboard's JS.
"""
from pathlib import Path

from flask import Flask, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
DASHBOARD_DIR = BASE_DIR / "dashboard"

app = Flask(__name__)


@app.route("/")
def dashboard():
    return send_from_directory(DASHBOARD_DIR, "index.html")


if __name__ == "__main__":
    app.run(debug=True)
