# alerts

Code for Assignments 5–6: filtering news items for relevance, writing
short urgency-rated alerts, and connecting high-urgency alerts back to a
company's score/flag.

## Assignment 5 — relevance filter + alert writer

Files:

- `data/companies.py` — placeholder portfolio list (name, sector,
  competitors, keywords). **Swap in the real list** once Assignment 4
  produces one.
- `data/sample_articles.py` — made-up sample articles (mix of relevant and
  noise) for testing before real news is flowing in from Assignment 4.
- `relevance.py` — asks Claude whether each article is relevant to a
  portfolio company (directly or via a competitor) and why.
- `alert_writer.py` — for each relevant article, asks Claude to write a
  short alert: what happened, why it matters to that company, and urgency
  (low/medium/high).
- `run.py` — ties the two together and prints/saves the results.

### Running it

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your-key-here
python3 run.py
```

Results print to the console and are saved to `alerts_output.json`.

### Per the assignment's testing step

Before trusting this broadly: read the 10 sample articles yourself, decide
by hand which ones should count as relevant to which company, then compare
against `run.py`'s output. Adjust the prompt in `relevance.py` (and rerun)
wherever it disagrees with your judgment, then do the same spot-check on
the alerts `alert_writer.py` produces.

### Known gap

Assignment 1 (the database) isn't built yet, so this currently reads from
the placeholder files in `data/` and writes to `alerts_output.json`
instead of a real `alerts` table. Once the database exists, swap the
`data/` reads and the JSON write in `run.py` for real reads/writes.
