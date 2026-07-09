"""Assignment 5, steps 2-3: decide whether a news item is relevant to a
portfolio company (directly or via a competitor), and why.
"""

import json

import anthropic

MODEL = "claude-sonnet-5"

_TOOL = {
    "name": "submit_relevance",
    "description": "Report relevance judgments for a batch of news articles.",
    "input_schema": {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "article_id": {"type": "string"},
                        "relevant": {"type": "boolean"},
                        "company": {
                            "type": ["string", "null"],
                            "description": "Portfolio company this article is relevant to, or null if not relevant.",
                        },
                        "relation": {
                            "type": ["string", "null"],
                            "enum": ["direct", "competitor", None],
                            "description": "Whether the article is about the company itself or a competitor.",
                        },
                        "reason": {
                            "type": "string",
                            "description": "One sentence: why this is (or isn't) relevant.",
                        },
                    },
                    "required": ["article_id", "relevant", "company", "reason"],
                },
            }
        },
        "required": ["results"],
    },
}


def _companies_block(companies: list[dict]) -> str:
    lines = []
    for c in companies:
        lines.append(
            f"- {c['name']} (sector: {c['sector']}); "
            f"competitors: {', '.join(c['competitors'])}; "
            f"watch keywords: {', '.join(c['keywords'])}"
        )
    return "\n".join(lines)


def _articles_block(articles: list[dict]) -> str:
    lines = []
    for a in articles:
        lines.append(
            f"[{a['id']}] \"{a['title']}\" ({a['source']}, {a['published_at']})\n"
            f"{a['snippet']}"
        )
    return "\n\n".join(lines)


def filter_articles(
    companies: list[dict], articles: list[dict], client: anthropic.Anthropic
) -> list[dict]:
    """Return one relevance judgment per article."""
    prompt = f"""We track a portfolio of companies for a fund. Here is the
portfolio, each with its known competitors and keywords worth watching:

{_companies_block(companies)}

Here are today's candidate news articles:

{_articles_block(articles)}

For each article, decide if it is actually relevant to one of our portfolio
companies -- either because it's about that company directly, or about one
of its named competitors. Ignore articles that are just noise (unrelated
industries, generic news, coincidental keyword overlap). If relevant, say
which company it's relevant to and whether it's "direct" or "competitor",
and give one plain sentence explaining why.

Report your judgment for every article via the submit_relevance tool."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        tools=[_TOOL],
        tool_choice={"type": "tool", "name": "submit_relevance"},
        messages=[{"role": "user", "content": prompt}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_relevance":
            return block.input["results"]

    raise RuntimeError("Model did not return a submit_relevance tool call")
