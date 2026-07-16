"""SEC EDGAR full-text search — free, no API key, but requires a descriptive
User-Agent header (SEC blocks requests without one)."""

import requests

from news_watch.config import SEC_USER_AGENT

SEARCH_URL = "https://efts.sec.gov/LATEST/search-index?q=%22{query}%22&forms=8-K"


def fetch_sec_filings(query, limit=5):
    """Search recent 8-K filings mentioning `query` (e.g. a competitor name)."""
    url = SEARCH_URL.format(query=requests.utils.quote(query))
    try:
        resp = requests.get(url, headers={"User-Agent": SEC_USER_AGENT}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        print(f"  [sec] failed to search '{query}': {exc}")
        return []

    hits = data.get("hits", {}).get("hits", [])[:limit]
    filings = []
    for hit in hits:
        src = hit.get("_source", {})
        accession_no = hit.get("_id", "").split(":")[0]
        cik = src.get("cik", "")
        display_names = src.get("display_names", [])
        company_name = display_names[0] if display_names else "Unknown filer"
        filing_date = src.get("file_date", "")
        form_type = src.get("root_forms", ["8-K"])[0]

        snippet = (
            f"{company_name} filed a Form {form_type} with the SEC on {filing_date or 'an unspecified date'}, "
            f"which was surfaced by a full-text search for \"{query}\" (accession number {accession_no}). "
            "The filing does not itself specify the exact nature of the underlying event beyond matching that "
            "search term. Companies typically file Form 8-K to disclose material events such as leadership "
            "changes, material agreements, acquisitions, or restructuring actions that investors would "
            "consider significant. Because this summary is generated from filing metadata rather than the "
            "filing's full text, the specific substance of the disclosure should be confirmed by reviewing "
            "the document directly on EDGAR."
        )
        filings.append(
            {
                "source_name": "SEC EDGAR",
                "headline": f"{company_name} filed {form_type} mentioning \"{query}\"",
                "url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}",
                "published_at": filing_date,
                "snippet": snippet,
            }
        )
    return filings
