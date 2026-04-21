"""postgres-reader — read-only Postgres tools for the hermes-agent LLM.

Exposes five tools the agent can call during reasoning:

  pg_schemas   — list non-system schemas
  pg_tables    — list tables in a schema (defaults: chefbook + hermes)
  pg_describe  — columns + indexes of a specific table
  pg_sample    — first N rows of a table
  pg_query     — arbitrary SELECT, read-only enforced at transaction level

Credentials: fetched from AWS Secrets Manager (default secret id
`hermes/db/readonly`, override with HERMES_PG_READER_SECRET_ID). Falls back
to $DATABASE_URL for local dev / tunneled RDS.

Read-only enforcement is done by Postgres itself: every tool opens a fresh
connection, runs `SET TRANSACTION READ ONLY`, and executes within that
transaction. Any INSERT/UPDATE/DELETE/DDL fails with `ReadOnlySqlTransaction`.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
from typing import Any, Iterable

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Constants / defaults
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_SECRET_ID = "hermes/db/readonly"
DEFAULT_REGION = "us-east-1"
DEFAULT_STATEMENT_TIMEOUT_MS = 30_000
DEFAULT_ROW_CAP = 200
DEFAULT_SAMPLE_LIMIT = 10
DEFAULT_SCHEMAS = ("chefbook", "hermes")
RESULT_MAX_CHARS = 20_000

# Identifier allowlist — conservative on purpose. Anything with special chars
# gets rejected instead of quoted, because getting escape right once is easier
# than auditing every SQL interpolation.
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


# ─────────────────────────────────────────────────────────────────────────────
# Lazy imports (psycopg / boto3) with friendly errors
# ─────────────────────────────────────────────────────────────────────────────

_psycopg_cache: Any = None
_psycopg_err: str | None = None


def _psycopg():
    """Return the psycopg module, caching the import. Raises with a clear
    message if the driver isn't installed — the check_fn below uses this to
    hide these tools from the LLM when the dep is missing."""
    global _psycopg_cache, _psycopg_err
    if _psycopg_cache is not None:
        return _psycopg_cache
    if _psycopg_err is not None:
        raise RuntimeError(_psycopg_err)
    try:
        import psycopg
        from psycopg.rows import dict_row  # noqa: F401 — attribute access later
        _psycopg_cache = psycopg
        return psycopg
    except ImportError as e:
        _psycopg_err = (
            f"postgres-reader: psycopg not installed ({e}). "
            f"Run: pip install 'psycopg[binary]'"
        )
        raise RuntimeError(_psycopg_err) from e


# ─────────────────────────────────────────────────────────────────────────────
# Connection config (Secrets Manager + DATABASE_URL fallback)
# ─────────────────────────────────────────────────────────────────────────────

_conninfo_cache: str | None = None
_conninfo_lock = threading.Lock()


def _conninfo_from_secrets_manager() -> str:
    secret_id = os.environ.get("HERMES_PG_READER_SECRET_ID", DEFAULT_SECRET_ID)
    region = (
        os.environ.get("AWS_REGION")
        or os.environ.get("AWS_DEFAULT_REGION")
        or DEFAULT_REGION
    )
    try:
        import boto3
    except ImportError as e:
        raise RuntimeError(
            "postgres-reader: boto3 not installed and no $DATABASE_URL set. "
            "Run: pip install boto3 — or export DATABASE_URL for local dev."
        ) from e

    client = boto3.client("secretsmanager", region_name=region)
    resp = client.get_secret_value(SecretId=secret_id)
    raw = resp.get("SecretString")
    if not raw:
        raise RuntimeError(f"Secret '{secret_id}' has no SecretString.")
    data = json.loads(raw)

    missing = [k for k in ("host", "port", "dbname", "username", "password") if k not in data]
    if missing:
        raise RuntimeError(f"Secret '{secret_id}' missing keys: {missing}")

    return (
        f"host={data['host']} port={data['port']} dbname={data['dbname']} "
        f"user={data['username']} password={data['password']} "
        "sslmode=require connect_timeout=10"
    )


def _libpq_quote(v: str) -> str:
    """Escape a libpq conninfo value: backslash-escape ' and \\, then single-quote."""
    escaped = v.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def _conninfo_from_db_env_vars() -> str | None:
    """Compose a libpq conninfo string from discrete DB_* env vars.

    Returns None when DB_HOST isn't set (signal that discrete vars aren't in use).
    Uses libpq key='value' format so passwords with special characters like
    ``) ( # { * $`` don't need URL-encoding.
    """
    host = os.environ.get("DB_HOST")
    if not host:
        return None
    port = os.environ.get("DB_PORT", "5432")
    dbname = os.environ.get("DB_DATABASE") or os.environ.get("DB_NAME") or "postgres"
    user = os.environ.get("DB_USERNAME") or os.environ.get("DB_USER") or ""
    password = os.environ.get("DB_PASSWORD", "")
    sslmode = os.environ.get("DB_SSLMODE", "require")

    parts = [
        f"host={_libpq_quote(host)}",
        f"port={port}",
        f"dbname={_libpq_quote(dbname)}",
    ]
    if user:
        parts.append(f"user={_libpq_quote(user)}")
    if password:
        parts.append(f"password={_libpq_quote(password)}")
    parts.append(f"sslmode={sslmode}")
    parts.append("connect_timeout=10")
    return " ".join(parts)


def _get_conninfo() -> str:
    global _conninfo_cache
    if _conninfo_cache is not None:
        return _conninfo_cache
    with _conninfo_lock:
        if _conninfo_cache is not None:
            return _conninfo_cache
        # Resolution order: DATABASE_URL → discrete DB_* vars → AWS Secrets Manager.
        url = os.environ.get("DATABASE_URL")
        if url:
            _conninfo_cache = url
        else:
            from_env = _conninfo_from_db_env_vars()
            _conninfo_cache = from_env if from_env else _conninfo_from_secrets_manager()
        return _conninfo_cache


def _connect():
    """Open a fresh connection in read-only mode."""
    psycopg = _psycopg()
    from psycopg.rows import dict_row
    conn = psycopg.connect(_get_conninfo(), autocommit=False, row_factory=dict_row)
    with conn.cursor() as cur:
        cur.execute("SET TRANSACTION READ ONLY")
        cur.execute(f"SET LOCAL statement_timeout = {DEFAULT_STATEMENT_TIMEOUT_MS}")
    return conn


def _run(sql: str, params: tuple | list | None = None, *, fetch_limit: int | None = None) -> list[dict]:
    """Execute SQL and return all rows (or up to `fetch_limit`)."""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            if cur.description is None:
                return []
            if fetch_limit is None:
                return list(cur.fetchall())
            return list(cur.fetchmany(fetch_limit))


# ─────────────────────────────────────────────────────────────────────────────
# Availability check (determines whether tools show up to the LLM)
# ─────────────────────────────────────────────────────────────────────────────

def _is_available() -> bool:
    """Toolset check-fn. Hides the tools if the driver or creds aren't set up."""
    try:
        _psycopg()
    except Exception:
        return False
    if os.environ.get("DATABASE_URL"):
        return True
    if os.environ.get("DB_HOST"):
        return True
    try:
        import boto3  # noqa: F401
    except ImportError:
        return False
    # We don't pre-fetch the secret here (would need AWS creds at import time
    # and would slow startup). Presence of boto3 + a secret-id override or the
    # default is enough to expose the tool; if creds are actually bad, the
    # first call fails with a clear error the LLM can react to.
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Identifier helpers
# ─────────────────────────────────────────────────────────────────────────────

def _check_ident(s: str, label: str) -> str:
    if not isinstance(s, str) or not _IDENT_RE.match(s):
        raise ValueError(
            f"Invalid {label} '{s}'. Must match [A-Za-z_][A-Za-z0-9_]*."
        )
    return s


# ─────────────────────────────────────────────────────────────────────────────
# Output formatting
# ─────────────────────────────────────────────────────────────────────────────

def _json_default(v: Any) -> Any:
    try:
        return str(v)
    except Exception:
        return repr(v)


def _format_rows(rows: list[dict], *, truncated: bool = False, note: str | None = None) -> str:
    payload: dict[str, Any] = {"rows": rows, "row_count": len(rows)}
    if truncated:
        payload["truncated"] = True
    if note:
        payload["note"] = note
    out = json.dumps(payload, default=_json_default, ensure_ascii=False, indent=2)
    if len(out) > RESULT_MAX_CHARS:
        # Trim rows until we fit; keep the shape readable.
        while rows and len(out) > RESULT_MAX_CHARS:
            rows = rows[: max(1, len(rows) // 2)]
            payload["rows"] = rows
            payload["row_count"] = len(rows)
            payload["truncated"] = True
            payload["note"] = (note + " " if note else "") + "output truncated to fit context"
            out = json.dumps(payload, default=_json_default, ensure_ascii=False, indent=2)
    return out


def _error(msg: str) -> str:
    return json.dumps({"error": msg}, ensure_ascii=False)


# ─────────────────────────────────────────────────────────────────────────────
# Tool handlers
# ─────────────────────────────────────────────────────────────────────────────

def _handle_psycopg_error(e: Exception) -> str:
    psycopg = _psycopg_cache
    if psycopg is not None:
        if isinstance(e, psycopg.errors.ReadOnlySqlTransaction):
            return _error("Blocked: postgres-reader is read-only by design. "
                          "The query attempted to modify data.")
        if isinstance(e, psycopg.errors.InsufficientPrivilege):
            return _error(f"Permission denied: {e}")
    return _error(f"Database error: {e}")


def tool_pg_schemas(args: dict, **_kw) -> str:
    try:
        rows = _run(
            """
            SELECT nspname AS schema,
                   pg_catalog.pg_get_userbyid(nspowner) AS owner
            FROM   pg_catalog.pg_namespace
            WHERE  nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
              AND  nspname NOT LIKE 'pg_temp_%'
              AND  nspname NOT LIKE 'pg_toast_temp_%'
            ORDER  BY nspname
            """
        )
        return _format_rows(rows)
    except Exception as e:
        return _handle_psycopg_error(e)


def tool_pg_tables(args: dict, **_kw) -> str:
    schema = args.get("schema")
    try:
        if schema:
            _check_ident(schema, "schema")
            schemas: Iterable[str] = [schema]
        else:
            schemas = DEFAULT_SCHEMAS
        rows = _run(
            """
            SELECT table_schema AS schema,
                   table_name   AS name,
                   table_type   AS kind
            FROM   information_schema.tables
            WHERE  table_schema = ANY(%s)
            ORDER  BY table_schema, table_name
            """,
            (list(schemas),),
        )
        return _format_rows(rows)
    except ValueError as e:
        return _error(str(e))
    except Exception as e:
        return _handle_psycopg_error(e)


def tool_pg_describe(args: dict, **_kw) -> str:
    try:
        schema = _check_ident(args.get("schema", ""), "schema")
        table = _check_ident(args.get("table", ""), "table")
    except ValueError as e:
        return _error(str(e))
    try:
        cols = _run(
            """
            SELECT column_name             AS column,
                   data_type               AS type,
                   is_nullable             AS nullable,
                   column_default          AS default,
                   character_maximum_length AS max_len
            FROM   information_schema.columns
            WHERE  table_schema = %s AND table_name = %s
            ORDER  BY ordinal_position
            """,
            (schema, table),
        )
        if not cols:
            return _error(f"No table {schema}.{table} found (or no read access).")

        idx = _run(
            """
            SELECT i.relname AS index_name,
                   pg_get_indexdef(ix.indexrelid) AS definition
            FROM   pg_class t
            JOIN   pg_namespace n ON n.oid = t.relnamespace
            JOIN   pg_index    ix ON ix.indrelid = t.oid
            JOIN   pg_class    i  ON i.oid = ix.indexrelid
            WHERE  n.nspname = %s AND t.relname = %s
            ORDER  BY i.relname
            """,
            (schema, table),
        )
        payload = {"columns": cols, "indexes": idx}
        out = json.dumps(payload, default=_json_default, ensure_ascii=False, indent=2)
        if len(out) > RESULT_MAX_CHARS:
            out = out[: RESULT_MAX_CHARS - 32] + "\n... (truncated)"
        return out
    except Exception as e:
        return _handle_psycopg_error(e)


def tool_pg_sample(args: dict, **_kw) -> str:
    try:
        schema = _check_ident(args.get("schema", ""), "schema")
        table = _check_ident(args.get("table", ""), "table")
    except ValueError as e:
        return _error(str(e))
    limit = args.get("limit", DEFAULT_SAMPLE_LIMIT)
    if not isinstance(limit, int) or limit < 1:
        limit = DEFAULT_SAMPLE_LIMIT
    limit = min(limit, DEFAULT_ROW_CAP)
    try:
        # Identifiers are validated; safe to interpolate.
        rows = _run(
            f'SELECT * FROM "{schema}"."{table}" LIMIT %s',
            (limit,),
        )
        return _format_rows(rows)
    except Exception as e:
        return _handle_psycopg_error(e)


def tool_pg_query(args: dict, **_kw) -> str:
    sql = args.get("sql") or args.get("query") or ""
    if not isinstance(sql, str) or not sql.strip():
        return _error("`sql` is required and must be a non-empty SELECT statement.")
    sql = sql.strip().rstrip(";")
    limit = args.get("limit", DEFAULT_ROW_CAP)
    if not isinstance(limit, int) or limit < 1:
        limit = DEFAULT_ROW_CAP
    limit = min(limit, DEFAULT_ROW_CAP)
    try:
        rows = _run(sql, fetch_limit=limit)
        # Detect truncation: if fetchmany returned exactly `limit`, there may
        # be more. This is a soft signal — not a guarantee.
        truncated = len(rows) == limit
        note = (
            f"Result capped at {limit} rows. Refine your SELECT with LIMIT "
            "or a tighter WHERE to see more." if truncated else None
        )
        return _format_rows(rows, truncated=truncated, note=note)
    except Exception as e:
        return _handle_psycopg_error(e)


# ─────────────────────────────────────────────────────────────────────────────
# Tool schemas
# ─────────────────────────────────────────────────────────────────────────────

PG_SCHEMAS_SCHEMA = {
    "name": "pg_schemas",
    "description": (
        "List non-system schemas in the Chefbook Postgres DB. "
        "Use this first if you don't know which schema a table lives in. "
        "Typical schemas: `chefbook` (product data), `hermes` (agent state)."
    ),
    "parameters": {"type": "object", "properties": {}, "required": []},
}

PG_TABLES_SCHEMA = {
    "name": "pg_tables",
    "description": (
        "List tables in a schema. Defaults to showing both `chefbook` and "
        "`hermes` when no schema is specified. Use this to discover what "
        "tables exist before querying."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "schema": {
                "type": "string",
                "description": "Schema name to list (e.g. 'chefbook'). "
                               "Omit to list both chefbook and hermes.",
            },
        },
        "required": [],
    },
}

PG_DESCRIBE_SCHEMA = {
    "name": "pg_describe",
    "description": (
        "Show columns (name, type, nullable, default) and indexes for a "
        "specific table. Always call this before writing a non-trivial "
        "`pg_query` so you know the column names and types."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "schema": {"type": "string", "description": "Schema name."},
            "table":  {"type": "string", "description": "Table name."},
        },
        "required": ["schema", "table"],
    },
}

PG_SAMPLE_SCHEMA = {
    "name": "pg_sample",
    "description": (
        "Fetch the first N rows of a table. Useful for eyeballing the data "
        "shape without writing SQL. Max 200 rows."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "schema": {"type": "string", "description": "Schema name."},
            "table":  {"type": "string", "description": "Table name."},
            "limit":  {"type": "integer", "description": "Row count (default 10, max 200)."},
        },
        "required": ["schema", "table"],
    },
}

PG_QUERY_SCHEMA = {
    "name": "pg_query",
    "description": (
        "Run an arbitrary SELECT (or WITH ... SELECT / EXPLAIN) against the "
        "Chefbook Postgres. READ-ONLY — any INSERT/UPDATE/DELETE/DDL is "
        "rejected by the server. Max 200 rows returned; add LIMIT in your "
        "SQL to stay under the cap. Always reference tables as "
        "`schema.table` (e.g. `chefbook.user_feedback`)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "SELECT statement. Do not include trailing semicolon.",
            },
            "limit": {
                "type": "integer",
                "description": "Hard row cap on the returned rows (default 200, max 200).",
            },
        },
        "required": ["sql"],
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Plugin entry point
# ─────────────────────────────────────────────────────────────────────────────

def register(ctx) -> None:
    """Called by hermes-agent's PluginManager at startup."""
    ctx.register_tool(
        name="pg_schemas",
        toolset="postgres-reader",
        schema=PG_SCHEMAS_SCHEMA,
        handler=tool_pg_schemas,
        check_fn=_is_available,
        emoji="🐘",
    )
    ctx.register_tool(
        name="pg_tables",
        toolset="postgres-reader",
        schema=PG_TABLES_SCHEMA,
        handler=tool_pg_tables,
        check_fn=_is_available,
        emoji="🐘",
    )
    ctx.register_tool(
        name="pg_describe",
        toolset="postgres-reader",
        schema=PG_DESCRIBE_SCHEMA,
        handler=tool_pg_describe,
        check_fn=_is_available,
        emoji="🐘",
    )
    ctx.register_tool(
        name="pg_sample",
        toolset="postgres-reader",
        schema=PG_SAMPLE_SCHEMA,
        handler=tool_pg_sample,
        check_fn=_is_available,
        emoji="🐘",
    )
    ctx.register_tool(
        name="pg_query",
        toolset="postgres-reader",
        schema=PG_QUERY_SCHEMA,
        handler=tool_pg_query,
        check_fn=_is_available,
        emoji="🐘",
    )
    logger.info("postgres-reader: registered 5 tools (toolset=postgres-reader)")
