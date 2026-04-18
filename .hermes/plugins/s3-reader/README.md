# s3-reader plugin

Read-only AWS S3 access for the hermes-agent LLM — so the agent can find
generated media, inspect uploaded files, and produce presigned URLs to
hand back to the user.

## Tools registered (toolset: `s3-reader`)

| Tool | Purpose |
|---|---|
| `s3_list_buckets` | List buckets visible to the IAM identity. |
| `s3_list_objects` | List keys in a bucket (prefix + pagination). |
| `s3_head_object` | Metadata only (size, type, etag, user metadata). |
| `s3_get_object` | Fetch object body (5 MB cap, text inline, binary summarised). |
| `s3_presign_get` | GET-only presigned URL (default 15 min, max 6 h). |

## Safety model

1. **Code-level**: the plugin only ever calls `GetObject`, `ListBuckets`,
   `ListObjectsV2`, `HeadObject`, `generate_presigned_url` (for GetObject).
   There is no code path that Puts, Copies, or Deletes.
2. **IAM-level** (the real boundary): restrict the caller's role to
   `s3:Get*`, `s3:List*`, `s3:HeadObject`. See policy below.
3. **Size cap**: `s3_get_object` issues a byte-range request so the full
   object never hits the wire past 5 MB.
4. **Presigned URL scope**: only `get_object` — the URL cannot upload or
   delete.

## One-time setup

### 1. Enable project plugins

```bash
export HERMES_ENABLE_PROJECT_PLUGINS=1
```

In ECS task definition:

```json
{"name": "HERMES_ENABLE_PROJECT_PLUGINS", "value": "1"}
```

### 2. Point hermes at the bundled skill

Same config as `postgres-reader` — if you've already done this, nothing to
change. In `~/.hermes/config.yaml`:

```yaml
skills:
  external_dirs:
    - ${HERMES_PROJECT_ROOT}/skills
```

Set `HERMES_PROJECT_ROOT` to the repo path (locally) or the container
checkout path (ECS).

### 3. Install Python deps

```bash
pip install boto3
```

Already required for `postgres-reader`; no-op if it's installed.

### 4. Grant read-only S3 permissions to the IAM role

Attach to the ECS task role (or your local IAM user) — scope the bucket
resources to match what the agent should actually see:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid":    "ListAllBucketsForDiscovery",
      "Effect": "Allow",
      "Action": "s3:ListAllMyBuckets",
      "Resource": "*"
    },
    {
      "Sid":    "ReadChefbookBuckets",
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetObject",
        "s3:GetObjectAttributes",
        "s3:HeadObject"
      ],
      "Resource": [
        "arn:aws:s3:::chefbook-generated-media",
        "arn:aws:s3:::chefbook-generated-media/*",
        "arn:aws:s3:::chefbook-user-uploads",
        "arn:aws:s3:::chefbook-user-uploads/*"
      ]
    }
  ]
}
```

Drop `s3:ListAllMyBuckets` if you don't want the agent enumerating every
bucket in the account — the other tools still work if you tell the agent
the bucket name directly.

## Local-dev auth

On your laptop, boto3 picks up creds from the standard chain:

1. `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_SESSION_TOKEN` env vars
2. `~/.aws/credentials` + `~/.aws/config`
3. `AWS_PROFILE` env var → selected profile in the files above

Region is read from `AWS_REGION` or `AWS_DEFAULT_REGION`, defaulting to
`us-east-1`.

## Verifying the plugin + skill loaded

```bash
hermes plugins
# s3-reader   0.1.0   project   enabled   5 tools
```

From inside a session:

```
/tools             # look for s3-reader toolset (five 🪣 s3_* tools)
/skills            # look for chefbook/s3-reader
```

## Smoke tests (inside a hermes session)

```
# 1. list buckets
"What S3 buckets can you see?"

# 2. list objects in a bucket
"List the first 20 objects in chefbook-generated-media under prefix users/42/"

# 3. read a small config
"What's in chefbook-config/prompts/v3.json?"

# 4. produce a shareable URL
"Give me a 10-minute link to users/42/images/2026-04-18/abc.jpg in
 chefbook-generated-media."
```

## Disabling

`~/.hermes/config.yaml`:

```yaml
plugins:
  disabled:
    - s3-reader
```

## Files

| File | Purpose |
|---|---|
| `plugin.yaml` | Manifest — name, version, deps, tool list. |
| `__init__.py` | `register(ctx)` + tool handlers + schemas. |
| `README.md` | This file. |
| `../../skills/chefbook/s3-reader/SKILL.md` | Companion skill: teaches the agent *when* to use these tools. |
