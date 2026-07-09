"""Assignment 5 end-to-end: filter sample articles for relevance, then write
alerts for the relevant ones.

Usage:
    export ANTHROPIC_API_KEY=...
    python3 alerts/run.py
"""

import json
import os
import sys

import anthropic

from data.companies import COMPANIES
from data.sample_articles import SAMPLE_ARTICLES
from relevance import filter_articles
from alert_writer import write_alert


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY before running this script.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    print(f"Judging relevance of {len(SAMPLE_ARTICLES)} articles...\n")
    judgments = filter_articles(COMPANIES, SAMPLE_ARTICLES, client)
    articles_by_id = {a["id"]: a for a in SAMPLE_ARTICLES}

    relevant = [j for j in judgments if j["relevant"]]
    irrelevant = [j for j in judgments if not j["relevant"]]

    print(f"Relevant: {len(relevant)} / {len(judgments)}\n")
    for j in judgments:
        tag = "RELEVANT" if j["relevant"] else "skip    "
        company = j.get("company") or "-"
        print(f"[{tag}] {j['article_id']} -> {company}: {j['reason']}")

    print("\nWriting alerts for relevant articles...\n")
    alerts = []
    for j in relevant:
        article = articles_by_id[j["article_id"]]
        alert = write_alert(article, j, client)
        alerts.append(alert)
        print(
            f"[{alert['urgency'].upper()}] {alert['company']} "
            f"({article['title']})\n"
            f"  What happened: {alert['what_happened']}\n"
            f"  Why it matters: {alert['why_it_matters']}\n"
        )

    with open("alerts_output.json", "w") as f:
        json.dump({"judgments": judgments, "alerts": alerts}, f, indent=2)
    print("Saved full results to alerts_output.json")


if __name__ == "__main__":
    main()
