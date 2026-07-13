# database

Code for Assignments 1–3: Supabase schema/tables, the health score formula
(from `health_score.py`), score calculation + history logging, and the
daily fade/flag (risk / follow-on / on track) job.

## Standalone prototype

Until the real Supabase tables exist, `schema.sql` + `build_db.py` stand
up a local SQLite database (`mip.db`) with the same shape: `companies`,
`monthly_metrics`, `scores`, `score_history`, `flag_history`. Run it with:

```
python3 database/build_db.py
```

It seeds 6 real portfolio companies (see `dashboard/index.html`) with a
few months of metrics each, scores them with the placeholder formula in
`health_score.py`, and prints the result. `calculate_health_score()` is
the only thing that should need to change when the real formula is ready.

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

Re-running is safe: it recomputes from the same latest report and replaces
that report's `scores`/`score_history` rows instead of duplicating them.

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
