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

        filings.append(
            {
                "source_name": "SEC EDGAR",
                "headline": f"{company_name} filed {form_type} mentioning \"{query}\"",
                "url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}",
                "published_at": filing_date,
                "snippet": f"Filing {accession_no} matched full-text search for '{query}'.",
            }
        )
    return filings
