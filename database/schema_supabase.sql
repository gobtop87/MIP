-- =============================================================================
-- Supabase (Postgres) schema for Assignment 1's shared database.
--
-- Same tables, columns, and names as the local SQLite prototype
-- (database/schema.sql) — this is that schema translated to Postgres syntax
-- so it can be pasted straight into the Supabase SQL editor. Nothing in
-- fade_score.py / flag_reason.py / build_db.py needs to change to point at
-- this instead of SQLite, aside from swapping the `sqlite3` connection for a
-- Postgres one (see database/README.md).
-- =============================================================================

CREATE TABLE companies (
    id           BIGSERIAL PRIMARY KEY,
    name         TEXT NOT NULL,
    industry     TEXT,
    founded_year INTEGER,
    flag         TEXT,
    flag_reason  TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE monthly_metrics (
    id             BIGSERIAL PRIMARY KEY,
    company_id     BIGINT NOT NULL REFERENCES companies(id),
    report_date    DATE NOT NULL,
    revenue        DOUBLE PRECISION NOT NULL,
    burn_rate      DOUBLE PRECISION NOT NULL,
    cash_balance   DOUBLE PRECISION NOT NULL,
    runway_months  DOUBLE PRECISION NOT NULL,
    growth_rate    DOUBLE PRECISION NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, report_date)
);

CREATE TABLE scores (
    id          BIGSERIAL PRIMARY KEY,
    company_id  BIGINT NOT NULL UNIQUE REFERENCES companies(id),
    metric_id   BIGINT NOT NULL REFERENCES monthly_metrics(id),
    score       DOUBLE PRECISION NOT NULL,
    flag        TEXT NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- source: 'report' = a real monthly_metrics report (compute_score.py) --
--                      always appends, one row per calculation, never
--                      deduped or overwritten.
--         'fade'    = the daily fade job (fade_score.py) -- deduped to one
--                      row per company per day by the partial unique index
--                      below, so reruns on the same day update that day's
--                      row instead of stacking a penalty.
CREATE TABLE score_history (
    id          BIGSERIAL PRIMARY KEY,
    company_id  BIGINT NOT NULL REFERENCES companies(id),
    metric_id   BIGINT NOT NULL REFERENCES monthly_metrics(id),
    score       DOUBLE PRECISION NOT NULL,
    flag        TEXT NOT NULL,
    source      TEXT NOT NULL DEFAULT 'report',
    as_of_date  DATE NOT NULL,
    reason      TEXT,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Only 'fade' rows dedup by day; 'report' rows are always append-only.
CREATE UNIQUE INDEX score_history_fade_daily
    ON score_history(company_id, as_of_date)
    WHERE source = 'fade';

CREATE TABLE flag_history (
    id          BIGSERIAL PRIMARY KEY,
    company_id  BIGINT NOT NULL REFERENCES companies(id),
    old_flag    TEXT,
    new_flag    TEXT NOT NULL,
    reason      TEXT,
    as_of_date  DATE NOT NULL,
    changed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Append-only log of every manual KPI edit made through the dashboard --
-- see database/schema.sql for the full explanation. "Restoring" an entry
-- re-applies its numbers as a new edit rather than deleting anything.
CREATE TABLE kpi_edits (
    id           BIGSERIAL PRIMARY KEY,
    company_id   BIGINT NOT NULL REFERENCES companies(id),
    revenue      DOUBLE PRECISION NOT NULL,
    burn_rate    DOUBLE PRECISION NOT NULL,
    cash_balance DOUBLE PRECISION NOT NULL,
    growth_rate  DOUBLE PRECISION NOT NULL,
    score        DOUBLE PRECISION NOT NULL,
    flag         TEXT NOT NULL,
    edited_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
