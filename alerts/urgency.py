"""Urgency rating for Assignment 5 — a static keyword tier map, no API needed."""

HIGH_TERMS = {"data breach", "bankruptcy", "lawsuit", "shuts down", "ransomware", "breach"}
MEDIUM_TERMS = {"acquisition", "acquires", "acquired by", "ipo", "layoffs", "earnings", "vulnerability", "outage"}


def rate_urgency(item):
    """Return "high", "medium", or "low" for a news item.

    Rated by the matched term's category first (a data breach headline is
    urgent regardless of who it's about); a competitor mention that didn't
    hit a rated term still gets a "medium" default since competitor activity
    is worth a heads-up even without an urgent keyword.
    """
    matched = (item.get("matched_term") or "").lower()
    if matched in HIGH_TERMS:
        return "high"
    if matched in MEDIUM_TERMS:
        return "medium"
    if item.get("is_competitor_mention"):
        return "medium"
    return "low"
