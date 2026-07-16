#!/usr/bin/env bash
# One-command setup + launch for the MIP dashboard.
# Usage: ./run.sh
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d venv ]; then
    echo "Creating virtualenv..."
    python3 -m venv venv
fi

echo "Installing dependencies..."
./venv/bin/pip install -q -r requirements.txt

if [ ! -f database/mip.db ]; then
    echo "Building score/flag data (first run)..."
    ./venv/bin/python database/build_db.py >/dev/null
else
    echo "Refreshing score fades/flags..."
fi
./venv/bin/python database/fade_score.py >/dev/null

echo "Seeding news data..."
./venv/bin/python -m news_watch.seed_demo_data >/dev/null

echo "Generating alerts..."
./venv/bin/python -m alerts.generate_alerts >/dev/null

echo "Escalating flags for high-urgency alerts..."
./venv/bin/python -m alerts.escalate_flags >/dev/null

# Open the browser a couple seconds after the server starts, then start the server.
(sleep 2 && ./venv/bin/python -c "import webbrowser; webbrowser.open('http://127.0.0.1:8000')") &

echo "Starting dashboard at http://127.0.0.1:8000 ..."
exec ./venv/bin/python app.py
