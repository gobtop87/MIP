"""Portfolio company list for Assignment 4 (Watch the News).

IDs and names match the real dashboard's 6 companies (dashboard/index.html)
so this module, the alerts/ module, and the dashboard's API layer (app.py)
can all refer to the same company without a separate mapping table.
Competitor names are real so genuine news actually matches.
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
        "id": "nexahealth",
        "name": "NexaHealth",
        "sector": "Healthcare",
        "competitors": ["Teladoc", "Hims & Hers", "Cerebral", "Amwell"],
        "keywords": GENERAL_KEYWORDS + ["telehealth", "fda", "clinical trial"],
    },
    {
        "id": "gridlock",
        "name": "GridLock AI",
        "sector": "Cybersecurity",
        "competitors": ["CrowdStrike", "Palo Alto Networks", "SentinelOne", "Okta"],
        "keywords": GENERAL_KEYWORDS + ["ransomware", "vulnerability", "breach"],
    },
    {
        "id": "pathwise",
        "name": "PathWise",
        "sector": "AI / ML Infrastructure",
        "competitors": ["OpenAI", "Anthropic", "Scale AI", "Databricks", "Hugging Face"],
        "keywords": GENERAL_KEYWORDS + ["large language model", "foundation model", "GPU"],
    },
    {
        "id": "solarvault",
        "name": "SolarVault",
        "sector": "Clean Energy",
        "competitors": ["Sunrun", "SunPower", "Tesla Energy", "Enphase Energy"],
        "keywords": GENERAL_KEYWORDS + ["solar", "battery storage", "clean energy"],
    },
    {
        "id": "cognify",
        "name": "Cognify Health",
        "sector": "Healthcare",
        "competitors": ["Tempus", "Komodo Health", "Innovaccer", "Butterfly Network"],
        "keywords": GENERAL_KEYWORDS + ["clinical data", "diagnostics", "electronic health record"],
    },
    {
        "id": "vaultnet",
        "name": "VaultNet",
        "sector": "Cybersecurity",
        "competitors": ["Zscaler", "Cloudflare", "Fortinet", "Rapid7"],
        "keywords": GENERAL_KEYWORDS + ["firewall", "zero trust", "breach"],
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
