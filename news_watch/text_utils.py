"""Small text-cleaning helpers for scraped snippet content.

RSS/NewsAPI feeds commonly embed HTML markup, bare URLs, and boilerplate
("Read more", "The post ... appeared first on ...", trailing "[…]") directly
in their summary/description fields, which otherwise leaks straight into the
dashboard. clean_snippet() strips all of that and guarantees the result ends
on a complete sentence rather than being cut off mid-word or mid-thought.
"""

import html
import re

_TAG_RE = re.compile(r"<[^>]+>")
_URL_RE = re.compile(r"https?://\S+")
_WHITESPACE_RE = re.compile(r"\s+")
_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,.;:!?)])")
_TRAILING_BOILERPLATE_RE = re.compile(
    r"\s*("
    r"read more.*"
    r"|continue reading.*"
    r"|the post .*? appeared first on .*"
    r"|\[?…\]?"
    r"|\[\.\.\.\]"
    r"|\.\.\.$"
    r")\s*$",
    re.IGNORECASE,
)
_SENTENCE_END_RE = re.compile(r"[.!?](?=\s|$)")

# A leftover fragment with no sentence-ending punctuation at all and more
# words than this reads as truncated prose, not a short label — drop it
# rather than show an unfinished thought.
_MAX_UNPUNCTUATED_WORDS = 6


def clean_snippet(raw, max_chars=900):
    """Strip HTML/links/boilerplate from a snippet and return complete sentences.

    Guarantees the result either ends on a complete sentence or is empty —
    never a fragment cut off mid-word or mid-thought.
    """
    if not raw:
        return raw

    text = _TAG_RE.sub(" ", raw)
    text = html.unescape(text)
    text = _URL_RE.sub("", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()

    # Boilerplate ("Read more", "[…]", …) is almost always trailing, but feeds
    # sometimes stack more than one layer of it — strip repeatedly.
    previous = None
    while previous != text:
        previous = text
        text = _TRAILING_BOILERPLATE_RE.sub("", text).strip()

    text = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", text)

    if len(text) > max_chars:
        text = _truncate_to_sentence(text, max_chars)

    text = _drop_trailing_fragment(text)

    return text


def _truncate_to_sentence(text, max_chars):
    """Cut at the last complete sentence at/before max_chars.

    Never returns a mid-word/mid-sentence fragment — if no good sentence
    boundary is found, the original (longer) text is returned untouched
    rather than risking an incomplete cut.
    """
    truncated = text[:max_chars]
    matches = list(_SENTENCE_END_RE.finditer(truncated))
    if matches:
        cut = matches[-1].end()
        if cut > max_chars * 0.4:
            return truncated[:cut].strip()
    return text


def _drop_trailing_fragment(text):
    """Guarantee the snippet ends on a complete sentence.

    If the source content was itself truncated (common with RSS feeds that
    mark truncation with "[…]"), trim back to the last complete sentence.
    If there is no complete sentence anywhere and the leftover looks like
    truncated prose rather than a short label, drop it entirely so the
    caller's "no summary available" fallback takes over instead of showing
    an unfinished thought.
    """
    if not text or text[-1] in ".!?":
        return text
    matches = list(_SENTENCE_END_RE.finditer(text))
    if matches:
        return text[: matches[-1].end()].strip()
    if len(text.split()) > _MAX_UNPUNCTUATED_WORDS:
        return ""
    return text
