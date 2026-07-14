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
    revenue        NUMERIC NOT NULL,
    burn_rate      NUMERIC NOT NULL,
    cash_balance   NUMERIC NOT NULL,
    runway_months  NUMERIC NOT NULL,
    growth_rate    NUMERIC NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, report_date)
);

CREATE TABLE scores (
    id          BIGSERIAL PRIMARY KEY,
    company_id  BIGINT NOT NULL UNIQUE REFERENCES companies(id),
    metric_id   BIGINT NOT NULL REFERENCES monthly_metrics(id),
    score       NUMERIC NOT NULL,
    flag        TEXT NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE score_history (
    id          BIGSERIAL PRIMARY KEY,
    company_id  BIGINT NOT NULL REFERENCES companies(id),
    metric_id   BIGINT NOT NULL REFERENCES monthly_metrics(id),
    score       NUMERIC NOT NULL,
    flag        TEXT NOT NULL,
    source      TEXT NOT NULL DEFAULT 'report',
    as_of_date  DATE NOT NULL,
    reason      TEXT,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, as_of_date, source)
);

CREATE TABLE flag_history (
    id          BIGSERIAL PRIMARY KEY,
    company_id  BIGINT NOT NULL REFERENCES companies(id),
    old_flag    TEXT,
    new_flag    TEXT NOT NULL,
    reason      TEXT,
    as_of_date  DATE NOT NULL,
    changed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
