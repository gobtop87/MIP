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

## Assignment 6 (not started)

Connecting high-urgency alerts back to a company's score/flag depends on
the health-score/flag work in `database/` (Assignments 1–3), which hasn't
been built yet.
