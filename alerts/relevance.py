"""Relevance filtering for Assignment 5.

Assignment 4 matches broadly on purpose: a generic keyword like "layoffs"
matches every company's watch list, even when the article has nothing to do
with that company's sector. This module decides which of those candidate
matches are actually worth alerting on for a given company — no external
API, just rules over the fields Assignment 4 already stored.
"""
import re

from news_watch.config import GENERAL_KEYWORDS

_GENERAL_KEYWORDS_LOWER = {k.lower() for k in GENERAL_KEYWORDS}


def sector_terms(company):
    """The company's own keywords, excluding the shared general ones."""
    return [k for k in company["keywords"] if k.lower() not in _GENERAL_KEYWORDS_LOWER]


def _contains_term(haystack, term):
    return re.search(r"\b" + re.escape(term) + r"\b", haystack, re.IGNORECASE) is not None


def is_relevant(item, company):
    """True if this news item is worth alerting on for this company.

    - A competitor mention is always relevant — it's already company-specific.
    - A match on one of the company's own sector-specific keywords is
      relevant on its own (e.g. "ransomware" for a cybersecurity company).
    - A match on a *general* keyword (funding, layoffs, lawsuit, etc.) is
      only relevant if the article also mentions one of the company's
      sector-specific terms — otherwise it's just noise from an unrelated
      company or industry using the same generic word.
    """
    if item.get("is_competitor_mention"):
        return True

    matched = (item.get("matched_term") or "").lower()
    if matched not in _GENERAL_KEYWORDS_LOWER:
        return True

    haystack = f"{item.get('headline', '')} {item.get('snippet', '')}"
    return any(_contains_term(haystack, term) for term in sector_terms(company))
