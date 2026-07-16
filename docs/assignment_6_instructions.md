# Assignment 6: Connect High-Urgency Alerts to Company Flags

## The goal

Right now, two parts of MIP don't talk to each other: the news system rates
alerts by urgency (low/medium/high — data breaches, lawsuits, bankruptcies
come through as `high`), and the scoring system flags each company `risk`,
`on_track`, or `follow_on` based on their financials alone. A company can
have an unaddressed `high`-urgency alert sitting in its news feed while the
dashboard still shows it as perfectly healthy.

**Build the connection: when a company has a recent, unhandled
`high`-urgency alert, it should show up as `risk` on the dashboard — even
if its financials alone wouldn't put it there.**

No external APIs needed. Everything required already exists in the
project's two databases — you're connecting two things that already work,
not building something from scratch.

## Why it matters

The whole point of this dashboard is catching problems early. Right now a
serious news event about a portfolio company can go completely unnoticed on
the "Morning Dashboard" view unless someone happens to click into the News
Feed for that specific company. This closes that gap.

## Where to start

- `alerts/README.md` and `database/README.md` — read both for context on how
  alerts and flags currently work independently.
- `database/fade_score.py` — the existing job that already sets a company's
  flag from a different trigger (a stale/low score). Yours is the same idea,
  different trigger.
- `alerts/generate_alerts.py` — the closest existing example of a script
  that reads from one part of the data and writes to another.

One open question worth deciding deliberately, not by accident: **should an
escalated flag clear itself automatically once things quiet down, or does a
person need to acknowledge it first?** Either is defensible — pick one and
write down why.

## Definition of done

- A company with a recent `high`-urgency alert shows as `risk` on the
  dashboard, with a reason that references the actual alert (not a generic
  sentence).
- Running the process twice doesn't double up — the same alert shouldn't
  re-trigger the same flag change over and over.
- It works whether the app is running locally or against the real Supabase
  database in production.
