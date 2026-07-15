# Assignment 6: Connect High-Urgency Alerts to Company Flags

## What you're building

Right now, two parts of MIP don't talk to each other:

- **The news alerts system** (`alerts/`, Assignment 5) watches for news about
  each portfolio company and rates it low/medium/high urgency — things like
  a data breach, lawsuit, or bankruptcy filing get rated `high`.
- **The scoring system** (`database/`, Assignments 1–3) looks at a company's
  financials and assigns them a status: `risk`, `on_track`, or `follow_on`.

A company can have a `high`-urgency data breach alert sitting right there in
its news feed while the dashboard still shows it as `on_track`, because its
financials alone still look fine. Your job is to close that gap: **when a
company has a recent `high`-urgency alert, it should get flagged `risk`,
even if the numbers alone wouldn't put it there.**

No external APIs, no new services — everything you need already exists in
the two databases this project already has. You're connecting two things
that already work, not building something from scratch.

---

## Before you start: read these first

1. `alerts/README.md` — the "Assignment 6" section there has the original
   design notes this document expands on. Skim the whole file for context on
   how alerts get created.
2. `database/README.md` — read the "Flagging" and "Flag reasons" sections
   specifically. You're extending the same pattern `fade_score.py` already
   uses to set a company's flag, just triggered by an alert instead of a
   stale/low score.
3. `alerts/generate_alerts.py` — read this end to end. Your new script will
   follow the exact same structure and import pattern.
4. `database/fade_score.py` — read `run_fade_job()`. This is the closest
   existing example of "read some data, decide a flag, write it back,
   log the change" — the same shape your script needs.

---

## The two databases you're bridging

This is the trickiest part conceptually, so make sure it clicks before you
start writing code:

- **`news_watch/news.db`** (SQLite, always local — never moved to Supabase)
  holds `news_items` and `alerts`. A company here is identified by a short
  string id, e.g. `"nexahealth"`, `"gridlock"` — see
  `news_watch/config.py`'s `COMPANIES` list.
- **`database/mip.db`** (SQLite locally, or Supabase in production — see
  "Going live on Supabase" in `database/README.md`) holds `companies`,
  `monthly_metrics`, `scores`, `flag_history`, etc. A company here is
  identified by an auto-generated integer id, and the two databases don't
  share that id — the only thing they agree on is the company's **name**
  (e.g. `"NexaHealth"`).

So: `alerts.company_id` (a string like `"nexahealth"`) → look it up in
`news_watch.config.COMPANIES` to get the real `name` (`"NexaHealth"`) → look
up *that* in `database/mip.db`'s `companies` table by `name` to get the
integer id you actually need to write a flag change against.

`app.py` already does exactly this lookup in a couple of places
(`_score_flag_for`, `_get_or_create_company`) — read those for a working
example of the pattern before you write your own.

---

## Step-by-step

### 1. Add a column so an alert only escalates a flag once

Open `alerts/db.py` and add a column to the `alerts` table's `SCHEMA`:

```python
applied_to_flag INTEGER NOT NULL DEFAULT 0
```

Without this, your script would re-flag the same company every single time
it runs, forever, off the same one alert. Add a small helper function too:

```python
def mark_alert_applied(alert_id):
    with get_conn() as conn:
        conn.execute("UPDATE alerts SET applied_to_flag = 1 WHERE id = ?", (alert_id,))
```

**Since `alerts` already exists in the live database** (both your local
`news_watch/news.db` and anyone else's), a plain `CREATE TABLE` won't work
for this — you need an `ALTER TABLE`. Two versions:

```sql
-- SQLite (local dev)
ALTER TABLE alerts ADD COLUMN applied_to_flag INTEGER NOT NULL DEFAULT 0;
```
```sql
-- Postgres/Supabase (if this ever needs to run against production)
ALTER TABLE alerts ADD COLUMN applied_to_flag INTEGER NOT NULL DEFAULT 0;
```
(Same syntax works on both, conveniently.)

### 2. Write a query for "un-escalated high-urgency alerts"

In `alerts/db.py`, add a function like:

```python
def unescalated_high_urgency_alerts():
    """High-urgency alerts that haven't flipped a company to 'risk' yet."""
    with get_conn() as conn:
        cur = conn.execute(
            """SELECT id, news_item_id, company_id, message
               FROM alerts
               WHERE urgency = 'high' AND applied_to_flag = 0"""
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
```

### 3. Create `alerts/escalate_flags.py`

This is your main entry point. Follow `alerts/generate_alerts.py`'s exact
shape — same `sys.path` setup at the top so it can import from `database.*`
too (that project doesn't currently need to, yours does):

```python
"""Assignment 6 entry point: escalate a company to 'risk' when it has a
recent high-urgency alert, even if its financials alone wouldn't put it
there. Run after alerts.generate_alerts:

    python -m alerts.escalate_flags
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alerts import db as alerts_db
from database.db import get_conn as get_mip_conn
from news_watch.config import COMPANIES

COMPANIES_BY_ID = {c["id"]: c for c in COMPANIES}


def run():
    candidates = alerts_db.unescalated_high_urgency_alerts()
    escalated = 0

    for alert in candidates:
        company = COMPANIES_BY_ID.get(alert["company_id"])
        if not company:
            continue

        with get_mip_conn() as conn:
            row = conn.execute(
                "SELECT id, flag FROM companies WHERE name = ?", (company["name"],)
            ).fetchone()
            if not row:
                continue  # company hasn't been seeded into mip.db yet
            company_row_id, old_flag = row

            if old_flag != "risk":
                reason = f"Flagged as risk: {alert['message']}"
                conn.execute(
                    "UPDATE companies SET flag = 'risk', flag_reason = ? WHERE id = ?",
                    (reason, company_row_id),
                )
                conn.execute(
                    """INSERT INTO flag_history (company_id, old_flag, new_flag, reason, as_of_date)
                       VALUES (?, ?, 'risk', ?, date('now'))""",
                    (company_row_id, old_flag, reason),
                )
                escalated += 1

        alerts_db.mark_alert_applied(alert["id"])

    print(f"Checked {len(candidates)} high-urgency alert(s), escalated {escalated} to risk.")


if __name__ == "__main__":
    run()
```

This is a **starting point, not a spec to copy blindly** — read it, understand
every line, and adjust as you learn more about the codebase. In particular:

- `date('now')` is SQLite syntax. If you want this to also work against
  Postgres/Supabase, check how `fade_score.py` handles dates instead (it
  passes a real Python `date` object rather than relying on the database's
  own "now" function).
- Right now this only ever sets `flag = 'risk'`. Should it check whether the
  company is already `follow_on` and not downgrade a strong company over one
  ambiguous alert? That's a judgment call — see the open question below.

### 4. Wire it into the pipeline

Add it to `run.sh`, right after the alerts step, and to `render.yaml`'s
`buildCommand` the same way:

```bash
./venv/bin/python -m alerts.generate_alerts
./venv/bin/python -m alerts.escalate_flags   # <- add this
```

### 5. Decide (and document) the open question

**Should an escalated flag ever go back to normal automatically, or does it
need a human to clear it?**

Both are reasonable:
- *Auto-clear*: the next time `fade_score.py` runs, it recomputes the flag
  from scratch based on financials alone, silently erasing the escalation.
- *Sticky until acknowledged*: the escalation should survive until someone
  explicitly reviews it — which would mean teaching `fade_score.py` to
  *not* overwrite a flag that was set by an alert, only one set by itself.

Pick one, and write a short paragraph in `alerts/README.md` (same section
where this assignment is described) explaining which you chose and why —
the same way `PROVISIONAL_FADE_SCHEDULE` in `fade_score.py` documents its
own reasoning. Don't just leave the decision implicit in the code.

---

## Definition of done

You're done when all of these are true:

1. `python -m alerts.generate_alerts` followed by `python -m alerts.escalate_flags`
   runs cleanly with no errors, both locally (SQLite) and with `DATABASE_URL`
   set to a Postgres/Supabase connection string.
2. Seed a `high`-urgency alert for a company that's currently `on_track`
   (you can insert one directly via `alerts_db.insert_alert(...)`, or just
   temporarily edit `alerts/urgency.py`'s keyword map to rate something
   `high` that would normally come through as `medium`/`low`).
3. After running your script, that company's `flag` in `database/mip.db`
   (or Supabase) is now `risk`, and `flag_reason` mentions the actual alert
   message — not a generic sentence.
4. A `flag_history` row was written recording the change.
5. Running the script a second time on the same alert does **not** create a
   duplicate `flag_history` row (this is what `applied_to_flag` is for).
6. The dashboard (`app.py` → `/api/companies` → `dashboard/index.html`)
   shows the new flag and reason without any other code changes — if it
   doesn't, something about how you wrote to `companies`/`flag_history`
   doesn't match what the rest of the app already expects.
7. `alerts/README.md` has a short paragraph documenting which way you
   decided the "does it auto-clear" question, and why.

---

## What not to touch

- Don't change `database/schema.sql` / `schema_supabase.sql` beyond what's
  needed for this (you shouldn't need any schema changes there at all —
  `flag_history` and `companies.flag` already exist and already support
  what you need).
- Don't change `fade_score.py`'s own logic unless your answer to the "does
  it auto-clear" question requires it (see above) — and if you do, explain
  why in your PR description.
- Don't add a new external API or library for this. If you find yourself
  reaching for one, stop and reread the "no external API" framing above —
  you're almost certainly overcomplicating it.
