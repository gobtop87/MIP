"""Static credibility ratings for known news sources.

This is a simple, editable lookup rather than anything computed from the
articles themselves — there's no reliable signal in the data we fetch
(NewsAPI, RSS, SEC EDGAR) to score credibility automatically.
"""

RATINGS_BY_SOURCE_NAME = {
    "reuters": "High",
    "bloomberg": "High",
    "the wall street journal": "High",
    "wsj": "High",
    "associated press": "High",
    "ap": "High",
    "financial times": "High",
    "techcrunch": "Medium",
    "the verge": "Medium",
    "ars technica": "Medium",
    "venturebeat": "Medium",
    "crunchbase news": "Medium",
    "business wire": "Medium",
    "pr newswire": "Medium",
}


def get_credibility(source, source_name):
    if source == "sec_edgar":
        return "Official (Regulatory Filing)"
    rating = RATINGS_BY_SOURCE_NAME.get((source_name or "").strip().lower())
    return rating or "Unverified"
