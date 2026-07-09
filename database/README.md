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
