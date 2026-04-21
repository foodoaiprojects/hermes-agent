-- 001_bootstrap.sql
-- =========================================================================
-- One-time bootstrap for the Chefbook RDS so hermes-agent + its FastAPI
-- wrapper can run.
--
-- Run as the RDS master user (e.g. `postgres`) over WireGuard:
--
--   psql "postgres://<master>:<pw>@<rds-host>:5432/postgres?sslmode=require" \
--        -v ON_ERROR_STOP=1 \
--        -v reader_password="'<reader-pw>'" \
--        -v writer_password="'<writer-pw>'" \
--        -f db_migrations/001_bootstrap.sql
--
-- The -v flags pre-inject the passwords as psql variables. Leave the
-- single-quotes around each value — psql treats the whole thing as the
-- literal to substitute.
--
-- Idempotent: safe to re-run. Role passwords are updated each time via
-- ALTER ROLE — convenient for rotation.
-- =========================================================================

\set ON_ERROR_STOP on

-- ── Membership — lets the master user CREATE objects on behalf of app roles
-- (RDS is not a true superuser, so this GRANT is required before
-- `CREATE SCHEMA ... AUTHORIZATION hermes_rw` works.)
-- =========================================================================

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'hermes_rw') THEN
    CREATE ROLE hermes_rw LOGIN PASSWORD :writer_password;
  ELSE
    EXECUTE format('ALTER ROLE hermes_rw LOGIN PASSWORD %L', :writer_password);
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'foodo_dev_reader') THEN
    CREATE ROLE foodo_dev_reader LOGIN PASSWORD :reader_password;
  ELSE
    EXECUTE format('ALTER ROLE foodo_dev_reader LOGIN PASSWORD %L', :reader_password);
  END IF;
END
$$;

-- Grant the master role membership in both app roles so it can own objects
-- on their behalf. Safe to re-run.
GRANT hermes_rw       TO CURRENT_USER;
GRANT foodo_dev_reader TO CURRENT_USER;

-- ── Extensions (pgcrypto for gen_random_uuid())
-- =========================================================================
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── Hermes schema (owned by hermes_rw so the app can do DDL if needed)
-- =========================================================================
CREATE SCHEMA IF NOT EXISTS hermes AUTHORIZATION hermes_rw;

-- ── hermes.api_jobs — job queue for async FastAPI endpoints
-- =========================================================================
SET ROLE hermes_rw;

CREATE TABLE IF NOT EXISTS hermes.api_jobs (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  endpoint     TEXT NOT NULL,
  user_id      TEXT NOT NULL,
  input        JSONB NOT NULL,
  status       TEXT NOT NULL DEFAULT 'queued',
  result       JSONB,
  error        TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at   TIMESTAMPTZ,
  finished_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_api_jobs_status_created
  ON hermes.api_jobs (status, created_at);

RESET ROLE;

-- ── Grants
-- =========================================================================

-- Writer: full access to the hermes schema, read-only on chefbook.
GRANT USAGE                              ON SCHEMA hermes   TO hermes_rw;
GRANT SELECT, INSERT, UPDATE, DELETE     ON ALL TABLES IN SCHEMA hermes   TO hermes_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE hermes_rw IN SCHEMA hermes
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO hermes_rw;

GRANT USAGE                              ON SCHEMA chefbook TO hermes_rw;
GRANT SELECT                             ON ALL TABLES IN SCHEMA chefbook TO hermes_rw;
ALTER DEFAULT PRIVILEGES IN SCHEMA chefbook
  GRANT SELECT ON TABLES TO hermes_rw;

-- Reader: read-only on both schemas. Also tighten at the role level
-- as defence in depth.
GRANT USAGE  ON SCHEMA hermes   TO foodo_dev_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA hermes   TO foodo_dev_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE hermes_rw IN SCHEMA hermes
  GRANT SELECT ON TABLES TO foodo_dev_reader;

GRANT USAGE  ON SCHEMA chefbook TO foodo_dev_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA chefbook TO foodo_dev_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA chefbook
  GRANT SELECT ON TABLES TO foodo_dev_reader;

ALTER ROLE foodo_dev_reader SET default_transaction_read_only = on;

-- ── Sanity check — surfaces grant issues early
-- =========================================================================
DO $$
BEGIN
  PERFORM 1 FROM hermes.api_jobs LIMIT 1;
  RAISE NOTICE 'bootstrap complete — hermes.api_jobs accessible';
END
$$;
