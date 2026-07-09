# MIP

## Dashboard (UI)

`dashboard/index.html` is the project's UI — a self-contained portfolio
dashboard (company list, risk/follow-on/on-track flags, trend charts).
`app.py` is a minimal Flask server that serves it, and is the intended home
for future routes/pages and any real-data API endpoints.

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/python app.py
```

Then open http://127.0.0.1:5000 in a browser.

Note: the dashboard currently renders from a hardcoded mock company array
in its own `<script>` block, not from this repo's data. Wiring it to real
data (SQLite `news_watch/news.db`, `database/`, `alerts/`, etc.) means
adding API routes to `app.py` and replacing that mock array with a `fetch()`
call — not done yet.

# MIP — News Watcher (Assignment 4)

Pulls news about portfolio companies and their competitors from NewsAPI, SEC
EDGAR, and RSS feeds, and saves matches to a database.

Companies are currently mocked (**Company A–F**) since the shared portfolio
database (Assignment 1) isn't live yet. Each mock company has a real sector
and real competitor names, so the pipeline pulls genuine news even though
the "company" itself is a placeholder. Swap in real portfolio company names
in `news_watch/config.py` once you're ready.

## Setup

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env   # optional: add a NEWSAPI_KEY if you have one
```

## Run it

```bash
./venv/bin/python -m news_watch.fetch_news
```

This will:
1. Create `news_watch/news.db` (SQLite) if it doesn't exist, and load the
   mock companies into the `companies` table.
2. Pull articles from free RSS feeds (TechCrunch, VentureBeat, The Verge,
   Crunchbase News, Ars Technica) and SEC EDGAR full-text search — no API
   key required for either.
3. If `NEWSAPI_KEY` is set in `.env`, also query NewsAPI per company.
4. Match each article/filing against every company's competitor list and
   watch-keywords (word-boundary, case-insensitive), and insert matches into
   `news_items`, deduped on `(company_id, url)`.
5. Print a summary, including whether today's volume is inside the
   30–80 items/day target from the assignment doc.

Re-running the script is safe — duplicate items (same company + URL) are
skipped, not re-inserted.

## Schema

`news_watch/db.py` defines two tables (`companies`, `news_items`) with the
same names/shape the shared Supabase database will likely use, so pointing
this at Supabase later should mostly be a matter of swapping the `sqlite3`
connection in `db.py` for a Postgres connection — the insert/query logic
doesn't need to change.

## Adjusting the watch list

Edit `news_watch/config.py`:
- `COMPANIES` — each entry's `competitors` and `keywords` drive what counts
  as a match. Add/remove terms to tune volume.
- `RSS_FEEDS` — add more feeds if volume is too low.
- `GENERAL_KEYWORDS` — watched for every company (funding rounds,
  acquisitions, data breaches, layoffs, etc.), per the assignment brief.

Note: general keywords are intentionally broad, so the same article can
match multiple companies (e.g. any "layoffs" headline matches every
company's keyword list). That's expected — Assignment 4's job is just to
get candidate items into the database; deciding what's *actually* relevant
to a specific company is Assignment 5's job.

## Scheduling

The deliverable doesn't require automation, but to run it daily:
- **Cron** (simplest): `0 7 * * * cd /path/to/MIP && ./venv/bin/python -m news_watch.fetch_news`
- **GitHub Actions**: add a scheduled workflow that checks out the repo,
  installs `requirements.txt`, and runs the module — add `NEWSAPI_KEY` as a
  repo secret if you have one.

## Known limitation in this sandbox

Live network calls to `efts.sec.gov` and the RSS feed hosts are blocked by
this remote session's outbound network policy (visible as `403` errors from
the proxy, not from the actual APIs). The fetch/match/dedupe logic is
verified against synthetic article data instead — run the script yourself
locally or in an environment with normal outbound internet access to see it
pull real news.
