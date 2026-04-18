"""s3-reader — read-only AWS S3 tools for the hermes-agent LLM.

Exposes five tools:

  s3_list_buckets   — list buckets accessible to the caller's IAM identity
  s3_list_objects   — list objects in a bucket (prefix filter + pagination)
  s3_head_object    — metadata (size, content-type, last-modified, etag)
  s3_get_object     — object body; text returned inline, binary returns a
                      summary + suggests using s3_presign_get
  s3_presign_get    — time-limited GET URL (useful for sharing a file URL
                      back to the user or passing to a browser tool)

Auth: standard boto3 credential chain — on ECS/EC2, the task/instance
role. Locally, AWS_* env vars or ~/.aws/credentials.

Read-only is enforced by which API calls this plugin actually makes
(only Get*, List*, Head*). As defence in depth, constrain the caller's
IAM role to `s3:Get*`, `s3:List*`, `s3:HeadObject` — nothing else.
"""

from __future__ import annotations

import base64
import json
import logging
import mimetypes
import os
from typing import Any

logger = logging.getLogger(__name__)

# ─── Constants ──────────────────────────────────────────────────────────────

DEFAULT_REGION = "us-east-1"
DEFAULT_LIST_MAX_KEYS = 100
HARD_LIST_MAX_KEYS = 1000
DEFAULT_GET_MAX_BYTES = 5 * 1024 * 1024      # 5 MB cap per object read
DEFAULT_PRESIGN_TTL_S = 900                  # 15 min
HARD_PRESIGN_TTL_S = 3600 * 6                # 6 h — refuse longer
RESULT_MAX_CHARS = 20_000
BINARY_PEEK_BYTES = 64                       # hex preview for binary files

# Content types we treat as text even if boto3 doesn't mark them so.
_TEXT_CONTENT_TYPE_PREFIXES = (
    "text/",
    "application/json",
    "application/xml",
    "application/javascript",
    "application/x-yaml",
    "application/yaml",
    "application/x-ndjson",
    "application/csv",
    "application/x-www-form-urlencoded",
)

# ─── Lazy boto3 import ──────────────────────────────────────────────────────

_boto3_cache: Any = None
_boto3_err: str | None = None
_client_cache: dict[str, Any] = {}


def _boto3():
    global _boto3_cache, _boto3_err
    if _boto3_cache is not None:
        return _boto3_cache
    if _boto3_err is not None:
        raise RuntimeError(_boto3_err)
    try:
        import boto3
        _boto3_cache = boto3
        return boto3
    except ImportError as e:
        _boto3_err = f"s3-reader: boto3 not installed ({e}). Run: pip install boto3"
        raise RuntimeError(_boto3_err) from e


def _region() -> str:
    return (
        os.environ.get("AWS_REGION")
        or os.environ.get("AWS_DEFAULT_REGION")
        or DEFAULT_REGION
    )


def _client(region: str | None = None):
    region = region or _region()
    if region in _client_cache:
        return _client_cache[region]
    client = _boto3().client("s3", region_name=region)
    _client_cache[region] = client
    return client


# ─── Availability check ─────────────────────────────────────────────────────

def _is_available() -> bool:
    """Hide tools from the LLM when boto3 isn't installed."""
    try:
        _boto3()
        return True
    except Exception:
        return False


# ─── Output helpers ─────────────────────────────────────────────────────────

def _json_default(v: Any) -> Any:
    try:
        return str(v)
    except Exception:
        return repr(v)


def _emit(payload: dict[str, Any]) -> str:
    out = json.dumps(payload, default=_json_default, ensure_ascii=False, indent=2)
    if len(out) > RESULT_MAX_CHARS:
        # Try shaving inline object bodies first if present.
        if isinstance(payload.get("body"), str):
            keep = max(1024, RESULT_MAX_CHARS - 2048)
            payload["body"] = payload["body"][:keep] + "\n... (truncated)"
            payload["body_truncated"] = True
            out = json.dumps(payload, default=_json_default, ensure_ascii=False, indent=2)
    if len(out) > RESULT_MAX_CHARS:
        out = out[: RESULT_MAX_CHARS - 32] + "\n... (truncated)"
    return out


def _error(msg: str, **extra: Any) -> str:
    payload: dict[str, Any] = {"error": msg}
    payload.update(extra)
    return json.dumps(payload, ensure_ascii=False)


def _handle_boto_error(e: Exception) -> str:
    # Import lazily so we don't force botocore at import time.
    try:
        from botocore.exceptions import ClientError, BotoCoreError, NoCredentialsError
    except ImportError:
        return _error(f"S3 error: {e}")
    if isinstance(e, NoCredentialsError):
        return _error(
            "No AWS credentials found. On ECS/EC2 this should come from the "
            "task/instance role; locally, set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY "
            "or configure ~/.aws/credentials."
        )
    if isinstance(e, ClientError):
        code = e.response.get("Error", {}).get("Code", "")
        msg = e.response.get("Error", {}).get("Message", str(e))
        if code in ("AccessDenied", "AllAccessDisabled", "Forbidden"):
            return _error(f"Access denied by IAM: {msg}", code=code)
        if code in ("NoSuchBucket", "NoSuchKey", "404"):
            return _error(f"Not found: {msg}", code=code)
        return _error(f"S3 error [{code}]: {msg}", code=code)
    if isinstance(e, BotoCoreError):
        return _error(f"boto core error: {e}")
    return _error(f"Unexpected S3 error: {e}")


# ─── Content-type classification ────────────────────────────────────────────

def _looks_text(content_type: str | None, key: str) -> bool:
    if content_type:
        ct = content_type.split(";", 1)[0].strip().lower()
        if any(ct.startswith(p) for p in _TEXT_CONTENT_TYPE_PREFIXES):
            return True
    # Fallback: sniff by extension
    guessed, _ = mimetypes.guess_type(key)
    if guessed:
        if any(guessed.startswith(p) for p in _TEXT_CONTENT_TYPE_PREFIXES):
            return True
    # File-extension allowlist for common text-ish formats without a mime.
    ext = os.path.splitext(key)[1].lower()
    return ext in {
        ".txt", ".md", ".json", ".jsonl", ".ndjson", ".yaml", ".yml",
        ".xml", ".csv", ".tsv", ".log", ".conf", ".ini", ".toml",
        ".py", ".sh", ".sql", ".html", ".css", ".js", ".ts",
    }


# ─── Tool handlers ──────────────────────────────────────────────────────────

def tool_s3_list_buckets(args: dict, **_kw) -> str:
    try:
        resp = _client().list_buckets()
        buckets = [
            {
                "name": b["Name"],
                "created_at": b.get("CreationDate"),
            }
            for b in resp.get("Buckets", [])
        ]
        return _emit({"buckets": buckets, "count": len(buckets)})
    except Exception as e:
        return _handle_boto_error(e)


def tool_s3_list_objects(args: dict, **_kw) -> str:
    bucket = (args.get("bucket") or "").strip()
    if not bucket:
        return _error("`bucket` is required.")
    prefix = (args.get("prefix") or "").lstrip("/")
    continuation_token = args.get("continuation_token") or None
    try:
        max_keys = int(args.get("max_keys") or DEFAULT_LIST_MAX_KEYS)
    except (TypeError, ValueError):
        max_keys = DEFAULT_LIST_MAX_KEYS
    max_keys = max(1, min(max_keys, HARD_LIST_MAX_KEYS))

    params: dict[str, Any] = {"Bucket": bucket, "MaxKeys": max_keys}
    if prefix:
        params["Prefix"] = prefix
    if continuation_token:
        params["ContinuationToken"] = continuation_token

    try:
        resp = _client().list_objects_v2(**params)
    except Exception as e:
        return _handle_boto_error(e)

    items = [
        {
            "key": o["Key"],
            "size": o.get("Size"),
            "last_modified": o.get("LastModified"),
            "etag": o.get("ETag", "").strip('"'),
            "storage_class": o.get("StorageClass"),
        }
        for o in resp.get("Contents", [])
    ]
    payload: dict[str, Any] = {
        "bucket": bucket,
        "prefix": prefix or None,
        "count": len(items),
        "objects": items,
    }
    if resp.get("IsTruncated"):
        payload["is_truncated"] = True
        payload["next_continuation_token"] = resp.get("NextContinuationToken")
    return _emit(payload)


def tool_s3_head_object(args: dict, **_kw) -> str:
    bucket = (args.get("bucket") or "").strip()
    key = (args.get("key") or "").lstrip("/")
    if not bucket or not key:
        return _error("`bucket` and `key` are both required.")
    try:
        resp = _client().head_object(Bucket=bucket, Key=key)
    except Exception as e:
        return _handle_boto_error(e)
    return _emit({
        "bucket": bucket,
        "key": key,
        "size": resp.get("ContentLength"),
        "content_type": resp.get("ContentType"),
        "last_modified": resp.get("LastModified"),
        "etag": (resp.get("ETag") or "").strip('"'),
        "storage_class": resp.get("StorageClass"),
        "metadata": resp.get("Metadata") or {},
    })


def tool_s3_get_object(args: dict, **_kw) -> str:
    bucket = (args.get("bucket") or "").strip()
    key = (args.get("key") or "").lstrip("/")
    if not bucket or not key:
        return _error("`bucket` and `key` are both required.")
    try:
        max_bytes = int(args.get("max_bytes") or DEFAULT_GET_MAX_BYTES)
    except (TypeError, ValueError):
        max_bytes = DEFAULT_GET_MAX_BYTES
    max_bytes = max(1, min(max_bytes, DEFAULT_GET_MAX_BYTES))

    # Use a byte-range request so we never pull more than max_bytes across
    # the wire — matters for 100 MB objects where we'd otherwise bill for
    # the full transfer before discarding.
    range_header = f"bytes=0-{max_bytes - 1}"
    try:
        resp = _client().get_object(Bucket=bucket, Key=key, Range=range_header)
    except Exception as e:
        # If the object is smaller than the range, S3 returns InvalidRange.
        # Retry once without Range in that case.
        try:
            from botocore.exceptions import ClientError
            if isinstance(e, ClientError):
                code = e.response.get("Error", {}).get("Code", "")
                if code in ("InvalidRange", "RequestedRangeNotSatisfiable"):
                    try:
                        resp = _client().get_object(Bucket=bucket, Key=key)
                    except Exception as e2:
                        return _handle_boto_error(e2)
                else:
                    return _handle_boto_error(e)
            else:
                return _handle_boto_error(e)
        except ImportError:
            return _handle_boto_error(e)

    content_type = resp.get("ContentType")
    full_size = resp.get("ContentLength")  # size of the returned body portion
    # The `ContentRange` header tells us the *total* object size: "bytes 0-N/TOTAL"
    content_range = resp.get("ContentRange", "")
    total_size = full_size
    if "/" in content_range:
        try:
            total_size = int(content_range.rsplit("/", 1)[1])
        except ValueError:
            pass

    try:
        body_bytes = resp["Body"].read()
    except Exception as e:
        return _handle_boto_error(e)

    payload: dict[str, Any] = {
        "bucket": bucket,
        "key": key,
        "content_type": content_type,
        "size_total": total_size,
        "size_fetched": len(body_bytes),
        "truncated": total_size is not None and total_size > len(body_bytes),
    }

    if _looks_text(content_type, key):
        try:
            text = body_bytes.decode("utf-8")
            payload["body"] = text
            payload["encoding"] = "utf-8"
        except UnicodeDecodeError:
            # Fall through to binary handling below.
            pass

    if "body" not in payload:
        peek = body_bytes[:BINARY_PEEK_BYTES].hex()
        payload["body_preview_hex"] = peek
        payload["note"] = (
            "Binary content — body not inlined. Use s3_presign_get to produce "
            "a URL you can share with the user or fetch via a browser tool."
        )

    return _emit(payload)


def tool_s3_presign_get(args: dict, **_kw) -> str:
    bucket = (args.get("bucket") or "").strip()
    key = (args.get("key") or "").lstrip("/")
    if not bucket or not key:
        return _error("`bucket` and `key` are both required.")
    try:
        ttl = int(args.get("expires_in") or DEFAULT_PRESIGN_TTL_S)
    except (TypeError, ValueError):
        ttl = DEFAULT_PRESIGN_TTL_S
    if ttl < 60:
        ttl = 60
    if ttl > HARD_PRESIGN_TTL_S:
        return _error(
            f"expires_in too large — max {HARD_PRESIGN_TTL_S}s ({HARD_PRESIGN_TTL_S // 3600}h). "
            f"Got {ttl}s."
        )
    try:
        url = _client().generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=ttl,
        )
    except Exception as e:
        return _handle_boto_error(e)
    return _emit({
        "bucket": bucket,
        "key": key,
        "expires_in_s": ttl,
        "url": url,
        "note": "GetObject-scoped URL. Don't paste into chats unless the "
                "user explicitly asked for a shareable link.",
    })


# ─── Tool schemas ───────────────────────────────────────────────────────────

S3_LIST_BUCKETS_SCHEMA = {
    "name": "s3_list_buckets",
    "description": (
        "List S3 buckets visible to this session's AWS identity. "
        "Use when you don't know what bucket a file lives in. "
        "Note: the full account's bucket list is only visible if the IAM "
        "role has s3:ListAllMyBuckets."
    ),
    "parameters": {"type": "object", "properties": {}, "required": []},
}

S3_LIST_OBJECTS_SCHEMA = {
    "name": "s3_list_objects",
    "description": (
        "List objects in a bucket, optionally filtered by a key prefix. "
        "Returns up to 100 objects by default (max 1000). For large "
        "listings, paginate by passing back the `next_continuation_token` "
        "from the previous response."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "bucket": {"type": "string", "description": "Bucket name."},
            "prefix": {"type": "string", "description": "Key prefix filter (e.g. 'users/42/')."},
            "max_keys": {"type": "integer", "description": "1-1000 (default 100)."},
            "continuation_token": {"type": "string", "description": "Token from a prior truncated response."},
        },
        "required": ["bucket"],
    },
}

S3_HEAD_OBJECT_SCHEMA = {
    "name": "s3_head_object",
    "description": (
        "Get an object's metadata (size, content-type, last-modified, etag, "
        "user metadata) without reading the body. Use this first for large "
        "objects or when you just need size/type."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "bucket": {"type": "string"},
            "key":    {"type": "string", "description": "Full key path, no leading slash."},
        },
        "required": ["bucket", "key"],
    },
}

S3_GET_OBJECT_SCHEMA = {
    "name": "s3_get_object",
    "description": (
        "Read an object from S3. Text-type content is returned inline as a "
        "UTF-8 string (up to 5 MB); binary content returns size, type, and "
        "a hex preview — for binary files use s3_presign_get to produce a "
        "URL instead. A byte-range request is used under the hood so large "
        "objects don't transfer beyond the cap."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "bucket":    {"type": "string"},
            "key":       {"type": "string", "description": "Full key, no leading slash."},
            "max_bytes": {"type": "integer", "description": "Hard cap on bytes fetched (default + max: 5242880 = 5 MB)."},
        },
        "required": ["bucket", "key"],
    },
}

S3_PRESIGN_GET_SCHEMA = {
    "name": "s3_presign_get",
    "description": (
        "Generate a time-limited GET URL for an S3 object. Useful for "
        "sharing a generated image/video URL back to the user or handing "
        "off to a vision/browser tool. Scope is read-only (GetObject) — "
        "the URL cannot upload or delete. Default TTL 15 min, max 6 h."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "bucket":     {"type": "string"},
            "key":        {"type": "string", "description": "Full key, no leading slash."},
            "expires_in": {"type": "integer", "description": "TTL in seconds (60-21600; default 900)."},
        },
        "required": ["bucket", "key"],
    },
}


# ─── Plugin entry point ─────────────────────────────────────────────────────

def register(ctx) -> None:
    ctx.register_tool(
        name="s3_list_buckets",
        toolset="s3-reader",
        schema=S3_LIST_BUCKETS_SCHEMA,
        handler=tool_s3_list_buckets,
        check_fn=_is_available,
        emoji="🪣",
    )
    ctx.register_tool(
        name="s3_list_objects",
        toolset="s3-reader",
        schema=S3_LIST_OBJECTS_SCHEMA,
        handler=tool_s3_list_objects,
        check_fn=_is_available,
        emoji="🪣",
    )
    ctx.register_tool(
        name="s3_head_object",
        toolset="s3-reader",
        schema=S3_HEAD_OBJECT_SCHEMA,
        handler=tool_s3_head_object,
        check_fn=_is_available,
        emoji="🪣",
    )
    ctx.register_tool(
        name="s3_get_object",
        toolset="s3-reader",
        schema=S3_GET_OBJECT_SCHEMA,
        handler=tool_s3_get_object,
        check_fn=_is_available,
        emoji="🪣",
    )
    ctx.register_tool(
        name="s3_presign_get",
        toolset="s3-reader",
        schema=S3_PRESIGN_GET_SCHEMA,
        handler=tool_s3_presign_get,
        check_fn=_is_available,
        emoji="🪣",
    )
    logger.info("s3-reader: registered 5 tools (toolset=s3-reader)")
