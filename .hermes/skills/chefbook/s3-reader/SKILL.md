---
name: s3-reader
description: Read-only access to AWS S3 via s3_* tools. Use when you need to find, inspect, or share files stored in S3 — generated images/videos from Replicate, user uploads, exported reports, logs. Also use to produce a presigned URL you can hand back to the user in chat.
version: 0.1.0
author: Chefbook
metadata:
  hermes:
    tags: [s3, aws, storage, files, media, read-only]
    requires_toolsets: [s3-reader]
prerequisites:
  env: [HERMES_ENABLE_PROJECT_PLUGINS]
---

# s3-reader

Read-only S3 inspector. Paired with the `s3-reader` plugin (in
`.hermes/plugins/s3-reader/`) which exposes five tools:
`s3_list_buckets`, `s3_list_objects`, `s3_head_object`, `s3_get_object`,
`s3_presign_get`.

## When to Use

- User asks about a **file you know lives in S3** — generated media, user
  uploads, exported data. "Show me the last image you generated for user
  42", "what did the failure log for run X say?", "send me the CSV report
  from yesterday".
- You need to **share a file URL with the user** — use `s3_presign_get`
  (time-limited, read-only).
- You want to **pass an image/video to a vision-capable tool or model** —
  produce a presigned URL and hand it over.
- **Debugging**: peek at a log file, config dump, or generated artifact in
  S3 to understand why something went wrong.

## When NOT to Use

- The user wants to **upload, modify, or delete**. This plugin is
  physically read-only. Writes should go through an API-server endpoint
  that owns the bucket.
- The file is **gigabytes** — don't try to download it; use
  `s3_head_object` to confirm size and `s3_presign_get` to share a URL.
- **Real-time logs** — S3 isn't the right place. Check CloudWatch, or
  whichever log sink is actually used.

## Usual workflow

```
1. Don't know which bucket?   →  s3_list_buckets
2. Know the bucket?           →  s3_list_objects with a prefix
                                 (e.g. prefix="users/42/generated/")
3. Want to see what's in it?  →  s3_head_object first (size / type)
                                 then s3_get_object if it's small + text
4. Want to share with user?   →  s3_presign_get (default 15 min TTL)
```

## Size + content-type handling

- **Text-ish content** (`text/*`, JSON, YAML, CSV, XML, source code, logs):
  `s3_get_object` returns it inline up to **5 MB**. Anything larger gets
  truncated with `truncated: true` in the response — fetch a tighter byte
  range or pre-filter server-side if you need more.
- **Binary content** (images, video, PDF, archives): `s3_get_object`
  returns only size/type/etag plus a short hex preview, and instructs you
  to use `s3_presign_get` instead. Don't try to decode binary with tools
  that expect text.

## Recipes

### Find the most recent image generated for a user

```
s3_list_objects(
  bucket = "chefbook-generated-media",
  prefix = "users/42/images/",
  max_keys = 20,
)
# Sort by last_modified desc in your head, or call pg_* to correlate
# with chefbook.user_feedback rows.
```

### Share an image back to the user

```
url = s3_presign_get(
  bucket = "chefbook-generated-media",
  key    = "users/42/images/2026-04-18/abc.jpg",
  expires_in = 900,
)
# Hand `url.url` back to the user in your reply. Remind them it expires.
```

### Read a small JSON config

```
s3_head_object(bucket="chefbook-config", key="prompts/v3.json")
# → check size is reasonable (< few hundred KB)
s3_get_object(bucket="chefbook-config", key="prompts/v3.json")
# → inline UTF-8 JSON in `body`
```

### Correlate a generated image with its DB feedback row

```
1. s3_list_objects(bucket="chefbook-generated-media", prefix="users/42/images/")
2. pick the latest object key
3. pg_query("SELECT * FROM chefbook.image_feedback WHERE s3_key = %s", [key])
```

## Safety notes

1. **Read-only is enforced at the IAM layer.** The task/instance role this
   plugin uses should have only `s3:Get*`, `s3:List*`, `s3:HeadObject`
   actions. Nothing in the plugin code calls Put/Copy/Delete — but IAM is
   the real boundary, not a code check.
2. **Presigned URLs leak if shared.** Default TTL is 15 min, max 6 h. Use
   shorter TTLs for sensitive buckets. Do not paste URLs into chat unless
   the user explicitly asked for a shareable link.
3. **PII awareness.** User-uploaded content may contain faces/IDs/emails.
   Summarize when possible; don't paste user data back unless the user
   explicitly asked to see that specific file.
4. **Don't hammer listings.** If a prefix has thousands of objects, use
   `max_keys=1000` + paginate rather than spinning through tiny pages.

## Tool quick reference

| Tool | Args | Notes |
|---|---|---|
| `s3_list_buckets` | — | Needs `s3:ListAllMyBuckets`. |
| `s3_list_objects` | `bucket`, `prefix?`, `max_keys?`, `continuation_token?` | Paginated via `next_continuation_token`. |
| `s3_head_object` | `bucket`, `key` | Cheap — always call before a big GET. |
| `s3_get_object` | `bucket`, `key`, `max_bytes?` | 5 MB hard cap. Text inline, binary summarised. |
| `s3_presign_get` | `bucket`, `key`, `expires_in?` | 60 s – 6 h, default 15 min. |
