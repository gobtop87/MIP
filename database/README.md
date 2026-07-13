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

No Supabase project/credentials were available when this was built, so:

1. Run `schema_supabase.sql` in the Supabase SQL editor to create the tables.
2. Run `python3 database/export_supabase_seed.py` to regenerate
   `seed_supabase.sql` from the same `SEED_COMPANIES` data `build_db.py`
   uses (keeps the two in sync — don't hand-edit `seed_supabase.sql`), then
   run its contents in the SQL editor to load the 6 companies + their
   monthly numbers.
3. Point the Python modules at Postgres instead of SQLite: swap the
   `sqlite3.connect(DB_PATH)` calls (in `build_db.py`, `fade_score.py`,
   `import_monthly_metrics.py`, `app.py`) for a Postgres connection (e.g.
   `psycopg2.connect(os.environ["DATABASE_URL"])`) and switch `?`
   placeholders to `%s`. The insert/query logic itself doesn't need to
   change — this schema was designed to make that swap mechanical.

Until then, `schema.sql` + `build_db.py` stand up a local SQLite database
(`mip.db`) with the same shape, and this repo (shared via git) is how the
data is shared with the rest of the team in the meantime. Run it with:

```
python3 database/build_db.py
```

It seeds the 6 real companies described above with 4 months of metrics
each, scores them, and prints the result.

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
3. Re-run `build_db.py`'s scoring step (Assignment 2) / `fade_score.py`
   (Assignment 3) afterward to turn the new numbers into an updated score
   and flag — importing metrics alone doesn't recompute those.

The same script works unchanged against Supabase once the connection swap
above is done (it only touches `monthly_metrics`).

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
