"""Short alert message text for Assignment 5 — template-based, no API needed."""


def build_alert_message(item, company):
    term = item.get("matched_term") or ""
    if item.get("is_competitor_mention"):
        reason = f"competitor {term} mentioned"
    else:
        reason = f"'{term}' mentioned"
    source = item.get("source_name") or item.get("source") or "unknown source"
    return f"[{company['name']}] {source}: {item['headline']} — {reason}"
