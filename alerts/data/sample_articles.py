"""Made-up sample articles for testing the relevance filter (Assignment 5, step 3-5).

Mix of: news directly about a portfolio company, news about a competitor,
and clearly irrelevant noise -- so we can check the filter tells them apart.
"""

SAMPLE_ARTICLES = [
    {
        "id": "a1",
        "title": "Fivetran raises $150M Series E led by Andreessen Horowitz",
        "source": "TechCrunch",
        "published_at": "2026-07-01",
        "snippet": (
            "Data pipeline startup Fivetran announced a $150M Series E round "
            "at a $6.5B valuation, with plans to expand its ETL platform "
            "further into the data warehouse market."
        ),
    },
    {
        "id": "a2",
        "title": "Bramble Health discloses data exposure affecting 40,000 patients",
        "source": "HealthITNews",
        "published_at": "2026-07-03",
        "snippet": (
            "Telehealth provider Bramble Health disclosed that a misconfigured "
            "database exposed patient records, including prescription history, "
            "for roughly 40,000 users. The company says it has since patched "
            "the issue and notified affected patients."
        ),
    },
    {
        "id": "a3",
        "title": "Local bakery chain expands to three new cities",
        "source": "Regional Business Journal",
        "published_at": "2026-07-02",
        "snippet": (
            "A regional bakery chain announced plans to open new locations in "
            "three cities by the end of the year, citing strong demand for "
            "artisanal bread."
        ),
    },
    {
        "id": "a4",
        "title": "Ramp launches new corporate card rewards program for SMBs",
        "source": "Fintech Weekly",
        "published_at": "2026-07-04",
        "snippet": (
            "Ramp unveiled a new rewards program targeting small and "
            "mid-sized businesses, intensifying competition in the corporate "
            "card and expense management space."
        ),
    },
    {
        "id": "a5",
        "title": "CrowdStrike warns of new ransomware campaign targeting cloud infrastructure",
        "source": "SecurityWeek",
        "published_at": "2026-07-05",
        "snippet": (
            "CrowdStrike published a threat advisory describing a new "
            "ransomware campaign exploiting misconfigured cloud storage "
            "buckets, urging enterprises to audit access controls."
        ),
    },
    {
        "id": "a6",
        "title": "Ledgerly lays off 15% of staff amid slower enterprise sales",
        "source": "The Information",
        "published_at": "2026-07-05",
        "snippet": (
            "Accounting automation startup Ledgerly confirmed layoffs "
            "affecting about 15% of its workforce, attributing the cuts to "
            "slower-than-expected enterprise sales growth and a push toward "
            "profitability."
        ),
    },
    {
        "id": "a7",
        "title": "New study finds coffee consumption linked to longevity",
        "source": "Health Daily",
        "published_at": "2026-07-06",
        "snippet": (
            "Researchers found a correlation between moderate coffee "
            "consumption and increased longevity in a study of 50,000 adults "
            "over 20 years."
        ),
    },
    {
        "id": "a8",
        "title": "Farside Logistics signs major freight contract with national retailer",
        "source": "Supply Chain Dive",
        "published_at": "2026-07-06",
        "snippet": (
            "Freight and logistics startup Farside Logistics announced a "
            "multi-year contract to manage shipping for a major national "
            "retail chain, expected to significantly grow its revenue."
        ),
    },
    {
        "id": "a9",
        "title": "Agility Robotics unveils next-generation warehouse humanoid",
        "source": "IEEE Spectrum",
        "published_at": "2026-07-07",
        "snippet": (
            "Agility Robotics showed off an updated version of its humanoid "
            "warehouse robot, claiming faster pick rates and longer battery "
            "life, as competition in industrial automation heats up."
        ),
    },
    {
        "id": "a10",
        "title": "City council approves new bike lane network downtown",
        "source": "City Times",
        "published_at": "2026-07-07",
        "snippet": (
            "The city council voted to approve a new network of protected "
            "bike lanes in the downtown core, part of a broader "
            "transportation plan."
        ),
    },
]
