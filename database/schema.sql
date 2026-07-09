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
-- `flag` is the company's current status ('risk' | 'on_track' | 'follow_on'),
-- derived from its latest faded score and kept up to date by the daily fade
-- job (see fade_score.py). NULL until the fade job has run at least once.
-- `flag_reason` is a plain-English sentence explaining that flag (see
-- flag_reason.py) — refreshed every run, even on days the flag itself
-- doesn't change.
CREATE TABLE companies (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    industry     TEXT,
    founded_year INTEGER,
    flag         TEXT,
    flag_reason  TEXT,
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
--
-- source: 'report' = score computed straight from a new monthly_metrics row;
--         'fade'    = score computed by the daily fade job for a day with no
--                      new report. as_of_date is the calendar date the row's
--                      score is valid for (the report_date for 'report' rows,
--                      the day the fade job ran for 'fade' rows). The unique
--                      constraint means re-running the fade job on the same
--                      day overwrites that day's row instead of stacking a
--                      second penalty on top.
CREATE TABLE score_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  INTEGER NOT NULL REFERENCES companies(id),
    metric_id   INTEGER NOT NULL REFERENCES monthly_metrics(id),
    score       REAL NOT NULL,
    flag        TEXT NOT NULL,
    source      TEXT NOT NULL DEFAULT 'report',  -- 'report' | 'fade'
    as_of_date  TEXT NOT NULL,                   -- YYYY-MM-DD this score reflects
    reason      TEXT,                            -- plain-English explanation ('fade' rows only)
    computed_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(company_id, as_of_date, source)
);

-- Append-only log of company status changes ('risk' | 'on_track' |
-- 'follow_on'). Unlike score_history (one row per day, every day), this only
-- gets a new row when the flag actually changes, so it directly answers
-- "when did this company's status change and to what". old_flag is NULL for
-- a company's first-ever flag assignment.
CREATE TABLE flag_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  INTEGER NOT NULL REFERENCES companies(id),
    old_flag    TEXT,
    new_flag    TEXT NOT NULL,
    reason      TEXT,               -- plain-English explanation as of the change
    as_of_date  TEXT NOT NULL,       -- YYYY-MM-DD the change was detected on
    changed_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
