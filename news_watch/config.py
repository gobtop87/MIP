"""Mock portfolio company list for Assignment 4 (Watch the News).

Company names are anonymized (Company A, B, C...) since this is a dev/demo
build. Sectors and competitor names are real so genuine news actually
matches. Swap in real portfolio company names + real competitors once this
is wired to the shared Supabase database from Assignment 1.
"""

# Keywords worth watching for any company, regardless of sector. Trimmed to
# the highest-signal terms — a broad general-keyword list matches the same
# article against all 6 companies at once and inflates daily volume well
# past the 30-80/day target (redundant/lower-signal terms removed: "raises",
# "series a/b/c" overlap with "funding round"; "earnings" and "partnership"
# are too common to be useful signal on their own).
GENERAL_KEYWORDS = [
    "funding round",
    "acquisition",
    "acquires",
    "acquired by",
    "data breach",
    "layoffs",
    "lawsuit",
    "ipo",
    "bankruptcy",
]

COMPANIES = [
    {
        "id": "company-a",
        "name": "Company A",
        "sector": "Fintech / Payments",
        "competitors": ["Stripe", "Plaid", "Adyen", "Square", "Block Inc"],
        "keywords": GENERAL_KEYWORDS + ["payments", "fraud detection"],
    },
    {
        "id": "company-b",
        "name": "Company B",
        "sector": "AI / ML Infrastructure",
        "competitors": ["OpenAI", "Anthropic", "Scale AI", "Databricks", "Hugging Face"],
        "keywords": GENERAL_KEYWORDS + ["large language model", "foundation model", "GPU"],
    },
    {
        "id": "company-c",
        "name": "Company C",
        "sector": "Cybersecurity",
        "competitors": ["CrowdStrike", "Palo Alto Networks", "SentinelOne", "Okta"],
        "keywords": GENERAL_KEYWORDS + ["ransomware", "vulnerability", "breach"],
    },
    {
        "id": "company-d",
        "name": "Company D",
        "sector": "E-commerce / Logistics",
        "competitors": ["Shopify", "ShipBob", "Flexport", "Faire"],
        "keywords": GENERAL_KEYWORDS + ["supply chain", "fulfillment", "warehouse"],
    },
    {
        "id": "company-e",
        "name": "Company E",
        "sector": "HealthTech",
        "competitors": ["Teladoc", "Ro", "Hims & Hers", "Cerebral"],
        "keywords": GENERAL_KEYWORDS + ["telehealth", "fda", "clinical trial"],
    },
    {
        "id": "company-f",
        "name": "Company F",
        "sector": "DevTools / SaaS",
        "competitors": ["Vercel", "Datadog", "GitHub", "Atlassian"],
        "keywords": GENERAL_KEYWORDS + ["outage", "developer platform", "api"],
    },
]

RSS_FEEDS = [
    ("TechCrunch", "https://techcrunch.com/feed/"),
    ("VentureBeat", "https://venturebeat.com/feed/"),
    ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ("Crunchbase News", "https://news.crunchbase.com/feed/"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
]

# Required by SEC's fair-access policy: https://www.sec.gov/os/webmaster-faq#developers
SEC_USER_AGENT = "MIP News Watcher research@example.com"

DAILY_ITEM_TARGET = (30, 80)
