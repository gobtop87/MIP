# alerts

Code for Assignments 5–6: filtering news items for relevance, writing
short urgency-rated alerts, and connecting high-urgency alerts back to a
company's score/flag.

## Assignment 5 (done)

No external API is used anywhere in this module — relevance and urgency
are both decided with plain rules over the fields Assignment 4 already
saved to `news_items`.

- `relevance.py` — a competitor mention is always relevant; a match on the
  company's own sector-specific keyword is relevant on its own; a match on
  a *general* keyword (funding, layoffs, lawsuit, etc.) only counts if the
  article also mentions one of that company's sector terms, since generic
  keywords otherwise match every company regardless of topic.
- `urgency.py` — a static keyword → tier map (`data breach`, `bankruptcy`,
  `lawsuit` → high; `acquisition`, `layoffs`, `ipo` → medium; everything
  else, including a plain competitor mention, → low/medium default).
- `messages.py` — short alert text from an f-string template.
- `db.py` — an `alerts` table in the same `news_watch/news.db`, one row
  per `news_items.id` (deduped via a unique constraint).
- `generate_alerts.py` — entry point: reads news items that don't have an
  alert yet, filters/rates them, and inserts the result.

Run it after `news_watch.fetch_news` has populated `news_items`:

```bash
./venv/bin/python -m alerts.generate_alerts
```

Known limitation: this is keyword co-occurrence, not real entity
recognition, so a headline that happens to contain both a company's sector
term and a general keyword can pass even when the article isn't really
about that company (e.g. "breach" is Company C's own sector keyword, so
any breach-related headline mentioning the word "breach" clears the bar).
Tightening this further would mean real NLP/entity matching, which is out
of scope while avoiding external APIs.

## Assignment 6 (not started, now unblocked)

This used to be blocked on Assignments 1–3 not existing yet — they're done
now (real `companies`/`monthly_metrics`/`scores` schema, live in Supabase in
production, SQLite locally), so this is buildable. It's also still genuinely
useful: right now a `high`-urgency alert (data breach, lawsuit, bankruptcy —
see `urgency.py`) just sits in `news_watch/news.db` and never touches a
company's `flag` in `database/mip.db`. A company can look "on track"
financially while sitting on an unaddressed breach alert, and nothing
surfaces that on the dashboard.

**The goal**: a company with a recent, unhandled `high`-urgency alert should
get escalated to `risk`, even if its financials alone wouldn't put it there —
same way `fade_score.py` already escalates a company to `risk` when its
*score* crosses a threshold, just triggered by an alert instead.

**Suggested shape** (adjust as you learn more — this is a starting design,
not a spec to follow blindly):

1. New script, e.g. `alerts/escalate_flags.py`, run after
   `alerts.generate_alerts` (either chained in `run.sh`/`render.yaml`'s build
   command, or as its own step).
2. Add an `applied_to_flag INTEGER NOT NULL DEFAULT 0` column to the
   `alerts` table (`alerts/db.py`'s `SCHEMA`) so an alert only escalates a
   flag once, not every time the job reruns.
3. Query `news_watch/news.db` for `alerts` where `urgency = 'high'` and
   `applied_to_flag = 0`. `alerts.company_id` is the *dashboard* id
   (`nexahealth`, `gridlock`, ...) — map it to a `database/mip.db` company
   the same way `app.py` already does: look up the name in
   `news_watch.config.COMPANIES`, then find that name in `companies`.
4. For each match, in `database/mip.db` (via `database/db.py`'s
   `get_conn()`, same as every other script here): set `companies.flag =
   'risk'`, write a `flag_history` row (reuse the shape `fade_score.py`
   already writes), and set a `flag_reason` that names the actual alert,
   e.g. `f"Flagged as risk: {alert['message']}"` — more specific than
   `flag_reason.py`'s metric-based sentences, which don't know alerts exist.
5. Mark the alert `applied_to_flag = 1` so reruns don't redo it or double-log
   `flag_history`.
6. Open question worth deciding deliberately rather than defaulting: should
   a company *un-escalate* automatically once its alerts age out or the next
   `fade_score.py` run recomputes a fresh flag, or does it need a human to
   acknowledge the alert first? Either is defensible — pick one and write
   down why in this README, same as the fade schedule's
   `PROVISIONAL_FADE_SCHEDULE` note does.

**Definition of done**: seed a `high`-urgency alert for a company currently
`on_track`, run the new script, and confirm `companies.flag` flips to
`risk` with a `flag_reason` that quotes the alert — both locally (SQLite)
and against the real Supabase database (`DATABASE_URL` set, see the root
README's "Deploying" section for how that's tested).
