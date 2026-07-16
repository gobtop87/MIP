"""Small text-cleaning helpers for scraped snippet content.

RSS feeds commonly embed full HTML (paragraphs, links) in their summary
field, which otherwise leaks raw tags and href text into the dashboard.
"""

import html
import re

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,.;:!?)])")


def clean_snippet(raw):
    """Strip HTML tags and entities from a snippet, leaving plain prose."""
    if not raw:
        return raw
    text = _TAG_RE.sub(" ", raw)
    text = html.unescape(text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    text = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", text)
    return text
