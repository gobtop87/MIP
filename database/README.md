# database

Code for Assignments 1–3: Supabase schema/tables, the health score formula
(from `health_score.py`), score calculation + history logging, and the
daily fade/flag (risk / follow-on / on track) job.

## Assignment 1 — Data Foundation

**Tables** (`schema.sql` for local SQLite, `schema_supabase.sql` for
Postgres/Supabase — same names/columns in both): `companies`,
`monthly_metrics`, `scores`, `score_history`, `flag_history`. No separate
"Section 2" spec doc existed in this repo to pull exact names from, so these
are the names already used consistently by every module that reads/writes
this data (`fade_score.py`, `flag_reason.py`, `app.py`'s dashboard API) —
changing them now would mean updating all of those too.

**Formula**: `health_score.py`'s `calculate_health_score()` — 40% runway
(12mo = full marks), 35% month-over-month growth (15% = full marks), 25%
burn efficiency (burn ≤ revenue = full marks). This is the project's
scoring formula; nothing else should need to change when it's tuned further,
since it's isolated in this one function on purpose.

**The 6 companies**: seeded from `SEED_COMPANIES` in `build_db.py`, matching
the 6 real portfolio companies on the dashboard (`dashboard/index.html`) by
name — NexaHealth, GridLock AI, PathWise, SolarVault, Cognify Health,
VaultNet. The dashboard doesn't publish raw revenue/burn/cash (only score,
runway, and a rolled-up performance %), so those three inputs are realistic
per-company estimates — but each company's most recent `cash_balance` is set
so `runway_months` (`cash_balance / burn_rate`) comes out to *exactly* the
runway the dashboard already shows for that company, and `growth_rate` is a
real month-over-month revenue change. Earlier months are backed out from
that anchor by walking net burn (`burn_rate - revenue`) backwards.

## Going live on Supabase

**This is now implemented, not just planned.** `db.py` picks its backend at
runtime from one environment variable:

- **`DATABASE_URL` unset** (the default for anyone running `./run.sh`
  locally) → SQLite, `database/mip.db`. Zero config, exactly like before.
- **`DATABASE_URL` set** to a Postgres connection string → every module
  (`build_db.py`\*, `compute_score.py`, `fade_score.py`, `app.py`) reads and
  writes that database instead, with no other code changes needed. This is
  what makes a shared hosted deployment (see the repo root README's
  "Deploying" section) actually persistent: the data lives in Supabase, not
  on whatever machine happens to be running the web server, so it survives
  restarts/redeploys and is the same for everyone who opens the dashboard.

  \* `build_db.py` refuses to run at all when `DATABASE_URL` is set — its
  `reset=True` wipe-and-reseed is a local-dev-only operation. Seed the real
  database exactly once via `seed_supabase.sql` (below) instead.

One-time setup, once you have a Supabase project:

1. In the Supabase SQL editor, run `database/schema_supabase.sql` to create
   the tables (this now includes the same `score_history` fade-dedup index
   `schema.sql` has, so both schemas behave identically).
2. Then run `database/seed_supabase.sql` in the same editor to load the 6
   real companies + their monthly numbers (kept in sync with `build_db.py`'s
   `SEED_COMPANIES` — regenerate it with `python3 database/export_supabase_seed.py`
   if that data ever changes; don't hand-edit the generated file).
3. From Project Settings → Database in Supabase, copy the connection string
   and set it as `DATABASE_URL` (Render: an environment variable on the
   service; local: `export DATABASE_URL=...` before running a script) to
   point everything at it instead of SQLite.

Tested end-to-end against a real Postgres instance while building this: schema
creation, seeding, `compute_score.py`, `fade_score.py` (including that its
same-day dedup still works), and the dashboard's KPI-editing endpoint all
verified working identically to the SQLite path. Two real SQLite/Postgres
differences turned up and got fixed as part of this: Postgres returns
`NUMERIC` columns as Python `Decimal` (breaks `calculate_health_score()`'s
float math) — schema now uses `DOUBLE PRECISION` instead — and returns `DATE`
columns as `datetime.date` objects rather than SQLite's plain text
(`fade_score.py` now handles both).

Without `DATABASE_URL` set, `schema.sql` + `build_db.py` stand up the local
SQLite database (`mip.db`) with the same shape, same as always. Run it with:

```
python3 database/build_db.py
```

It seeds the 6 real companies described above with 4 months of metrics
each, scores them, and prints the result.

`seed_test_companies.py` adds 6 obviously-fake companies (`TestCo A`
through `TestCo F`) on top of the real ones, for hand-verifying the scoring
formula (Assignment 2, step 3) without risking mixing test data into the
real portfolio:

```
python3 database/seed_test_companies.py
```

Their numbers are made up but realistic, and deliberately span the
risk/watch/on_track buckets. Safe to re-run — it deletes and reseeds any
existing `TestCo *` rows each time rather than duplicating them.

## Entering new monthly numbers

Decided on the simplest option per the assignment: **a CSV you fill in and
import**, no custom form.

1. Fill in `monthly_metrics_template.csv` (or a copy of it) — one row per
   company, just `revenue`, `burn_rate`, `cash_balance` for the new
   `report_date`. Leave a row blank to skip that company for this run.
2. `python3 database/import_monthly_metrics.py [path/to/file.csv]`
   (defaults to the template's own path). `runway_months` and `growth_rate`
   are computed automatically — growth from the company's previous
   `monthly_metrics` row, so nobody computes a % change by hand.
3. Run `compute_score.py` (below) and then `fade_score.py` (Assignment 3)
   afterward to turn the new numbers into an updated score and flag —
   importing metrics alone doesn't recompute those.

The same script works unchanged against Supabase once the connection swap
above is done (it only touches `monthly_metrics`).

## Computing scores

`build_db.py`/`seed_test_companies.py` score companies as part of seeding
them. `compute_score.py` is the standalone version of that step (Assignment
2): given a company that already has `monthly_metrics` rows, it pulls the
latest one, runs it through `calculate_health_score()`, writes the result
to `scores` (upserted — one row per company), and appends a matching
`source='report'` row to `score_history` so past calculations are never
lost.

```
python3 database/compute_score.py <company_id>   # one company
python3 database/compute_score.py --all           # every company
```

`scores` holds one row per company (the current snapshot, upserted on every
run). `score_history` is strictly append-only: every call to
`compute_score.py` inserts a new, timestamped row and never overwrites a
previous one — even calling it twice in a row for the same company logs two
history entries. (The daily fade job in `fade_score.py` is the one
exception: its `source='fade'` rows dedup to one per company per day via a
partial unique index scoped to that source only, so it can safely rerun
without stacking penalties — `source='report'` rows are unaffected.)

All database access is isolated in `db.py` — `get_conn()` (a context
manager yielding a connection, committed/closed on exit) and `init_db()`
(builds `mip.db` from `schema.sql`). `build_db.py`, `fade_score.py`, and
`app.py` all go through these instead of opening their own connections, so
swapping in the real Supabase/Postgres database later means rewriting only
`db.py` — no other file needs to change.

## Score fading

`fade_score.py` is the daily fade job: for each company it takes the real
score from `scores` (untouched — never overwritten) and how many days it's
been since their last `monthly_metrics` report, applies the fade schedule,
and writes the result to `score_history` as a `source='fade'` row keyed by
`as_of_date`. Fade is recomputed from scratch every run from
(base score, report date, today), so running it twice in a day just
replaces that day's row instead of stacking a penalty, and a company fades
back to full score the moment a fresh report comes in.

No fade-schedule spec doc exists in this repo yet, so the schedule lives in
one constant, `PROVISIONAL_FADE_SCHEDULE` in `fade_score.py`, clearly marked
for replacement once a real one is written:
- no penalty within 30 days of the last report
- −5 points per full week after that
- floor of 0

## Flagging

After computing each day's faded score, the job labels the company via
`flag_from_faded_score()` in `fade_score.py`:
- faded score below 35 -> `risk`
- faded score above 75 -> `follow_on`
- everything else -> `on_track`

The label is stored on the company record itself (`companies.flag`), and
only when it actually changes does a row get appended to `flag_history`
(`old_flag`, `new_flag`, `as_of_date`) — that table is the audit trail for
"when did this company's status change", separate from `score_history`'s
one-row-per-day log of every score. Comparing against the flag already
saved on the company means reruns on the same day don't log a duplicate
change.

This flag vocabulary (`risk` / `on_track` / `follow_on`) is specific to the
daily fade job's company-level status. The unrelated `flag` already stored
on `scores`/`monthly_metrics`-derived `score_history` rows (`'report'`
source) still uses `health_score.py`'s own bucket labels — that's a
separate, earlier piece of the pipeline and out of scope here.

## Flag reasons

`flag_reason.py` generates one plain sentence explaining each company's
flag, e.g. `"Flagged as risk: revenue growth fell 147% below target, the
largest gap of any metric."` It compares runway, revenue growth, and burn
rate against the healthy benchmarks baked into `calculate_health_score`
(12 months runway, 15% MoM growth, burn ≤ revenue) and names whichever is
furthest off (or, for an on-track/follow-on company, closest to concerning
/ the strongest performer).

If fading — not the underlying metrics — is what produced the flag (i.e.
the un-faded score would land in a better bucket than the faded one does),
the sentence says so instead of blaming a metric, e.g. `"On track: no
numbers reported in 38 days, so the score has faded."`

The reason is stored alongside the flag everywhere the flag itself is
stored: `companies.flag_reason` (refreshed every run, even when the flag
doesn't change), `score_history.reason` (on each day's `'fade'` row), and
`flag_history.reason` (the explanation as of that status change).

Run it once a day:

```
python3 database/fade_score.py
```

**Scheduling:** the simplest option is a cron entry on whatever machine/server
runs this job, e.g. run daily at 6am:

```
0 6 * * * cd /path/to/MIP/database && /usr/bin/python3 fade_score.py >> fade.log 2>&1
```

If this ends up running in CI instead of a persistent server, a GitHub
Actions workflow on a `schedule:` cron trigger does the same thing without
needing a machine to stay up.
