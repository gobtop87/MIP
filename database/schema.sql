-- =============================================================================
-- Local prototype schema (SQLite) for the "score fading & flags" pipeline.
--
-- This mirrors the tables the real project will have in Supabase (Postgres).
-- Table/column names are chosen to map 1:1 onto the real schema later:
--   companies       -> Supabase `companies`
--   monthly_metrics -> Supabase `monthly_metrics` (the monthly report data)
--   scores          -> Supabase `scores`          (latest score per company)
--   score_history   -> Supabase `score_history`   (append-only log, used to
--                                                   detect "fading" trends)
-- =============================================================================

-- One row per portfolio company.
CREATE TABLE companies (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    industry     TEXT,
    founded_year INTEGER,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

-- One row per company per reporting month (the raw metrics a report gives us).
CREATE TABLE monthly_metrics (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id     INTEGER NOT NULL REFERENCES companies(id),
    report_date    TEXT NOT NULL,     -- YYYY-MM-DD, first of the reporting month
    revenue        REAL NOT NULL,     -- monthly revenue, USD
    burn_rate      REAL NOT NULL,     -- net monthly cash burn, USD
    cash_balance   REAL NOT NULL,     -- cash in bank as of report_date, USD
    runway_months  REAL NOT NULL,     -- cash_balance / burn_rate
    growth_rate    REAL NOT NULL,     -- month-over-month revenue growth (0.10 = 10%)
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(company_id, report_date)
);

-- Latest score snapshot per company (one row per company, kept up to date).
CREATE TABLE scores (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  INTEGER NOT NULL UNIQUE REFERENCES companies(id),
    metric_id   INTEGER NOT NULL REFERENCES monthly_metrics(id),
    score       REAL NOT NULL,   -- 0-100 placeholder health score
    flag        TEXT NOT NULL,   -- 'on_track' | 'watch' | 'at_risk'
    computed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Append-only history of every score ever computed. Comparing consecutive
-- rows per company is how the future "fading" job will detect a declining
-- trend rather than just looking at a single snapshot.
CREATE TABLE score_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  INTEGER NOT NULL REFERENCES companies(id),
    metric_id   INTEGER NOT NULL REFERENCES monthly_metrics(id),
    score       REAL NOT NULL,
    flag        TEXT NOT NULL,
    computed_at TEXT NOT NULL DEFAULT (datetime('now'))
);
