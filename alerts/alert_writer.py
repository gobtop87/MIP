"""Assignment 5, step 4: turn a relevant news item into a short, readable alert."""

import anthropic

MODEL = "claude-sonnet-5"

_TOOL = {
    "name": "submit_alert",
    "description": "Report a short alert for a relevant news item.",
    "input_schema": {
        "type": "object",
        "properties": {
            "what_happened": {"type": "string", "description": "One sentence."},
            "why_it_matters": {
                "type": "string",
                "description": "One sentence, specific to the portfolio company.",
            },
            "urgency": {"type": "string", "enum": ["low", "medium", "high"]},
        },
        "required": ["what_happened", "why_it_matters", "urgency"],
    },
}


def write_alert(
    article: dict, relevance: dict, client: anthropic.Anthropic
) -> dict:
    """Write one alert for an article already judged relevant."""
    prompt = f"""Portfolio company: {relevance['company']}
This article is relevant because ({relevance['relation']}): {relevance['reason']}

Article: "{article['title']}" ({article['source']}, {article['published_at']})
{article['snippet']}

Write a short alert for an investor about this article, using the
submit_alert tool:
- what_happened: one plain sentence, no jargon
- why_it_matters: one sentence tying it specifically to {relevance['company']}
- urgency: low/medium/high (high = could meaningfully hurt/help the company
  or signal a competitor pulling ahead; low = worth knowing, not urgent)"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=[_TOOL],
        tool_choice={"type": "tool", "name": "submit_alert"},
        messages=[{"role": "user", "content": prompt}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_alert":
            alert = dict(block.input)
            alert["article_id"] = article["id"]
            alert["company"] = relevance["company"]
            alert["relation"] = relevance["relation"]
            return alert

    raise RuntimeError("Model did not return a submit_alert tool call")
