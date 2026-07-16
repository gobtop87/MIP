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

## Assignment 6 (done)

Connects Assignment 5's alerts back to a company's `flag` in
`database/mip.db`: a company can look "on track" financially while sitting
on an unaddressed `high`-urgency alert, and nothing used to surface that on
the dashboard. Now it does.

- `alerts/db.py` gained an `applied_to_flag INTEGER NOT NULL DEFAULT 0`
  column on `alerts` (migrated in with `ALTER TABLE` inside `init_db()`,
  since the table already existed in every already-running copy of
  `news_watch/news.db`), plus `unescalated_high_urgency_alerts(since_iso)`
  and `mark_alert_applied(alert_id)`.
- `alerts/escalate_flags.py` is the new entry point, run after
  `alerts.generate_alerts` (chained in `run.sh` and `render.yaml`'s build
  command). For every un-escalated `high`-urgency alert from the last 30
  days (`RECENT_ALERT_WINDOW_DAYS` — provisional, same reasoning as
  `fade_score.py`'s `PROVISIONAL_FADE_SCHEDULE`: no real spec exists yet for
  how long an alert should count as "recent"), it maps `alerts.company_id`
  (the dashboard id, e.g. `"nexahealth"`) to a `database/mip.db` company the
  same way `app.py` already does — via `news_watch.config.COMPANIES`'s name,
  then a lookup by name in `companies` — and, if that company isn't already
  `risk`, sets `companies.flag = 'risk'`, writes a `flag_history` row, and
  sets `flag_reason` to `f"Flagged as risk: {alert['message']}"` (quotes the
  actual alert, unlike `flag_reason.py`'s metric-based sentences, which have
  no idea alerts exist). The alert is then marked `applied_to_flag = 1`, so
  rerunning the script never re-escalates the same alert or double-logs
  `flag_history` — it only escalates once per alert, and only touches a
  company that isn't already flagged `risk`.
- Works against both backends: it writes through `database/db.py`'s
  `get_conn()` like every other script here, and uses a real Python `date`
  object (like `fade_score.py`) rather than SQLite's `date('now')`, so it
  runs unchanged with `DATABASE_URL` pointed at Supabase.
- No schema changes to `database/mip.db` — `companies.flag`/`flag_reason`
  and `flag_history` already had everything this needed.

**The open question, decided**: should an escalated flag clear itself
automatically once things quiet down, or does it need a human to
acknowledge it first? **This chose auto-clear** — the next time
`fade_score.py` runs, it recomputes the company's flag from financials
alone, same as it always has, with no special-casing for alert-driven
flags. Reasoning:

- It's the option that needed zero changes to `fade_score.py` or to
  `database/mip.db`'s schema, both of which the assignment brief for this
  step explicitly said not to touch unless the decision required it — and
  a sticky/acknowledged design *would* require it (fade_score.py would need
  to know which flags it's allowed to overwrite, which means persisting
  that distinction somewhere new).
- An alert-driven `risk` flag is a read of the company's *current* state,
  not a permanent verdict. If the news genuinely stops (no new `high`-alerts
  land) and the next fade run finds healthy financials, showing `risk`
  forever off one aging alert is its own failure mode — alarm fatigue that
  trains people to stop trusting the flag.
- It isn't a one-shot escalation that silently vanishes the instant it's
  set, either: `RECENT_ALERT_WINDOW_DAYS` keeps a `high`-urgency alert
  eligible to (re-)escalate for 30 days, and as long as the underlying
  story keeps generating fresh `high`-urgency news, each new alert is a
  brand-new, unapplied row that re-escalates the company on its own — so a
  genuinely ongoing situation (breaking news keeps coming) stays `risk`
  continuously, while a one-off alert that never recurs and whose financials
  are actually fine fades back on its own.
- Trade-off worth naming: a single unresolved incident that stops generating
  *new* news (e.g. one breach headline, then silence) reverts to a
  financials-only flag the next time `fade_score.py` runs, even if no human
  ever actually reviewed it. Sticky-until-acknowledged is the more
  conservative choice if that trade-off turns out to matter more in
  practice — it would mean teaching `fade_score.py` to check, before
  overwriting a company's `flag`, whether the current one came from an
  alert (e.g. by checking the most recent `flag_history.reason` for the
  `"Flagged as risk: "` alert-message prefix this module writes) rather than
  from itself, and leaving it alone until some acknowledgment step clears
  it.

**Definition of done** (verified both locally with SQLite and by reading
through the Postgres path in `database/db.py` — no live Supabase project in
this environment to test against directly): seed a `high`-urgency alert for
a company currently `on_track`, run `alerts.generate_alerts` then
`alerts.escalate_flags`, and confirm `companies.flag` flips to `risk` with a
`flag_reason` that quotes the alert. Running `escalate_flags` again is a
no-op — no duplicate `flag_history` row, no reprocessing of the same
alert.
