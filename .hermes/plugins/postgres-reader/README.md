# postgres-reader plugin

A hermes-agent plugin that gives the LLM **read-only** access to the Chefbook
RDS Postgres database. The agent uses it to look up user feedback, session
state, recipes, posts, and anything else in the `chefbook` and `hermes`
schemas when reasoning about a task (e.g. personalizing an image-gen prompt
using the user's past likes/dislikes).

## Tools registered (toolset: `postgres-reader`)

| Tool | Purpose |
|---|---|
| `pg_schemas` | List non-system schemas. |
| `pg_tables` | List tables (defaults: chefbook + hermes). |
| `pg_describe` | Columns + indexes of a specific table. |
| `pg_sample` | First N rows of a table (max 200). |
| `pg_query` | Arbitrary SELECT (read-only enforced by Postgres itself; max 200 rows). |

## Safety — why this is physically read-only

Every tool call opens a fresh connection, runs `SET TRANSACTION READ ONLY`,
and executes inside that transaction. Any INSERT / UPDATE / DELETE / DDL
fails with `ReadOnlySqlTransaction` at the **Postgres server**, not in
application code — so there is no way for a crafted query or a compromised
handler to mutate the database, even if the `hermes_ro` DB user were
accidentally granted write permissions.

As defence in depth, follow the role setup in the next section so the DB
user itself has zero write grants.

## One-time setup

### 1. Enable project plugins

Hermes loads plugins from `~/.hermes/plugins/` by default. To also load
this repo's `./.hermes/plugins/`, set the opt-in env var:

```bash
export HERMES_ENABLE_PROJECT_PLUGINS=1
```

In ECS, add it to the task definition:

```json
{
  "name":  "HERMES_ENABLE_PROJECT_PLUGINS",
  "value": "1"
}
```

### 1a. Point hermes at the repo's bundled skills

The companion `SKILL.md` (at `skills/chefbook/postgres-reader/SKILL.md` in
this repo) teaches the agent *when* to reach for `pg_*` tools and what
tables exist. Hermes only auto-discovers skills from `~/.hermes/skills/`,
so add this repo's `skills/` dir as an external source in
`~/.hermes/config.yaml`:

```yaml
skills:
  external_dirs:
    - ${HERMES_PROJECT_ROOT}/skills
```

Then set `HERMES_PROJECT_ROOT` to the absolute repo path. Locally:

```bash
export HERMES_PROJECT_ROOT=/Users/mishal/Documents/foodo/hermes-agent
```

In ECS (task definition env):

```json
{
  "name":  "HERMES_PROJECT_ROOT",
  "value": "/app"
}
```

(Replace `/app` with whatever path the Dockerfile checks out the repo to.)
`${VAR}` expansion in `external_dirs` means the same config.yaml works on
your laptop and in the container.

### 2. Install Python deps

```bash
pip install 'psycopg[binary]' boto3
```

Or add to your deployment image's `requirements.txt` / equivalent.

### 3. Create the read-only role in RDS

Connect as superuser and run:

```sql
CREATE ROLE hermes_ro WITH LOGIN PASSWORD 'CHANGE_ME';

GRANT USAGE  ON SCHEMA chefbook TO hermes_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA chefbook TO hermes_ro;
GRANT USAGE  ON SCHEMA hermes   TO hermes_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA hermes   TO hermes_ro;

ALTER DEFAULT PRIVILEGES IN SCHEMA chefbook
  GRANT SELECT ON TABLES TO hermes_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA hermes
  GRANT SELECT ON TABLES TO hermes_ro;

-- Defence in depth: the role itself is read-only.
ALTER ROLE hermes_ro SET default_transaction_read_only = on;
```

### 4. Store creds in AWS Secrets Manager

```bash
aws secretsmanager create-secret \
  --name hermes/db/readonly \
  --description "Read-only creds for postgres-reader hermes plugin" \
  --secret-string '{
    "host":     "chefbook-prod.xxxxx.us-east-1.rds.amazonaws.com",
    "port":     5432,
    "dbname":   "chefbook",
    "username": "hermes_ro",
    "password": "THE_PASSWORD_YOU_JUST_SET"
  }'
```

Override the secret id with `HERMES_PG_READER_SECRET_ID` env var if yours
lives elsewhere (e.g. `my-team/hermes/ro`).

### 5. Grant the ECS task role access to the secret

IAM policy on the task role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect":   "Allow",
      "Action":   "secretsmanager:GetSecretValue",
      "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:hermes/db/readonly-*"
    }
  ]
}
```

## Local-dev shortcut

If you're tunneling to RDS and don't want to involve Secrets Manager:

```bash
export DATABASE_URL='postgres://hermes_ro:PASS@localhost:5433/chefbook?sslmode=disable'
export HERMES_ENABLE_PROJECT_PLUGINS=1
hermes chat
```

When `DATABASE_URL` is set, the plugin uses it and skips Secrets Manager
entirely.

## Verifying the plugin + skill loaded

```bash
hermes plugins
# postgres-reader   0.1.0   project   enabled   5 tools
```

Or from inside a session:

```
/tools            # look for postgres-reader (five 🐘 pg_* tools)
/skills           # look for chefbook/postgres-reader
```

If tools are missing:

1. `HERMES_ENABLE_PROJECT_PLUGINS=1` is set.
2. `pip install 'psycopg[binary]'` succeeded.
3. AWS creds are available (or `DATABASE_URL` is set).

If the skill is missing:

1. `HERMES_PROJECT_ROOT` is set and points at the repo root.
2. `~/.hermes/config.yaml` has `skills.external_dirs` including
   `${HERMES_PROJECT_ROOT}/skills`.

## Disabling

In `~/.hermes/config.yaml`:

```yaml
plugins:
  disabled:
    - postgres-reader
```

## Files

| File | Purpose |
|---|---|
| `plugin.yaml` | Manifest — name, version, deps, tool list. |
| `__init__.py` | `register(ctx)` + tool handlers + schemas. |
| `README.md` | This file. |
| `../../skills/chefbook/postgres-reader/SKILL.md` | Companion skill: teaches the agent *when* to use these tools + the table layout. |
