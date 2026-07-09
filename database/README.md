# database

Code for Assignments 1–3: Supabase schema/tables, the health score formula
(from `health_score.py`), score calculation + history logging, and the
daily fade/flag (risk / follow-on / on track) job.

## Standalone prototype

Until the real Supabase tables exist, `schema.sql` + `build_db.py` stand
up a local SQLite database (`mip.db`) with the same shape: `companies`,
`monthly_metrics`, `scores`, `score_history`. Run it with:

```
python3 database/build_db.py
```

It seeds 4 fake companies with a few months of metrics each, scores them
with the placeholder formula in `health_score.py`, and prints the result.
`calculate_health_score()` is the only thing that should need to change
when the real formula is ready; swap the table names for the Supabase
equivalents when that schema lands.

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
