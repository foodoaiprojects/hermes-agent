---
name: postgres-reader
description: Query the Chefbook Postgres DB (read-only) via the pg_* tools. Use when the user's task needs data about users, recipes, posts, feedback, or prior hermes sessions — e.g. personalizing a prompt with the user's likes/dislikes, looking up session history, or answering questions about product data.
version: 0.1.0
author: Chefbook
metadata:
  hermes:
    tags: [database, postgres, chefbook, read-only, rds]
    requires_toolsets: [postgres-reader]
prerequisites:
  env: [HERMES_ENABLE_PROJECT_PLUGINS]
---

# postgres-reader

Read-only Postgres access to the Chefbook RDS database. Paired with the
`postgres-reader` plugin (in `.hermes/plugins/postgres-reader/`) which
exposes five tools the LLM can call directly.

## When to Use

- User asks about **their product data**: "what recipes has user X saved?",
  "how many posts did we publish last week?", "show me user 42's feedback".
- **Personalizing a generation** — before calling an image/video/content
  tool, look up the user's past likes/dislikes/preferences in
  `chefbook.user_feedback` (or the equivalent table) and fold them into the
  prompt.
- **Session inspection** — "what did I ask yesterday?", "what model was
  running on session abc123?" — query `hermes.sessions` / `hermes.messages`.
- **Ad-hoc analytics** that fit in a single SELECT (counts, groupings,
  recent activity). For big aggregations or real-time dashboards, redirect
  to the API server instead.

## When NOT to Use

- The user wants to **modify** anything. This skill is physically read-only
  — Postgres rejects DML/DDL at the transaction level. If they want to
  insert/update/delete, they need a proper API endpoint or migration.
- The answer needs **real-time** data with sub-second freshness across
  replicas — read-replica lag can make this stale; go through the API
  server's cached endpoints.
- The table they want lives **elsewhere** (not `chefbook` or `hermes`
  schema) — list schemas first with `pg_schemas` before guessing.

## The two schemas

| Schema | Owner | Contents |
|---|---|---|
| `chefbook` | Product | User-facing product data: users, recipes, posts, feedback, media, etc. |
| `hermes` | Agent runtime | Hermes's own state: sessions, messages, memory queues. Only populated after migration off SQLite. |

If you don't know which schema a table lives in, call `pg_schemas` first,
then `pg_tables` on the candidate schema.

## Recommended workflow

```
1. Unsure about layout?  →  pg_schemas, then pg_tables.
2. Know the table name?  →  pg_describe first (columns, types, indexes)
                            so your SELECT matches reality.
3. Simple look-see?      →  pg_sample (first N rows).
4. Specific question?    →  pg_query with a targeted SELECT.
```

**Always reference tables as `schema.table`** — e.g. `chefbook.users`,
never bare `users`. The tools don't set a default `search_path`.

## Pitfalls & Troubleshooting

1. **Permission Errors**: The current database user may have restricted access to certain schemas (e.g., `chefbook`). If queries return a "Permission denied" error, you will need to operate with different credentials or notify the user. Always verify permissions by attempting a sample query or describe call before querying large datasets.
2. **Table Lookup**: Use `SELECT tablename, schemaname FROM pg_tables` to confirm the location of a table if standard lookups (`pg_tables()`, `pg_describe()`) return empty results without error, as they may be checking the wrong schema scope.
3. **Read-only is enforced by Postgres**, not application code. The role has `default_transaction_read_only = on`. Any write attempt returns `ReadOnlySqlTransaction` — don't retry it; report the failure and pick a different approach.
4. **Row cap: 200** per `pg_query` / `pg_sample` call. Tighten your WHERE clause rather than cranking `limit` — the cap is hard.
5. **Statement timeout: 30s**. If a query is too slow, the server cancels it. Don't wrap heavy analytics in this tool; that's API-server / OLAP territory.
6. **Don't leak PII into logs or final responses** unless the user
   explicitly asked for specific rows. Summarize when possible.

## Tool quick reference

| Tool | Args | Notes |
|---|---|---|
| `pg_schemas` | — | Lists non-system schemas. |
| `pg_tables` | `schema?` | Omit schema → both `chefbook` and `hermes`. |
| `pg_describe` | `schema`, `table` | Columns + indexes. Run this before non-trivial queries. |
| `pg_sample` | `schema`, `table`, `limit?` | First N rows, max 200. |
| `pg_query` | `sql`, `limit?` | Arbitrary SELECT; Postgres rejects writes; max 200 rows. |
