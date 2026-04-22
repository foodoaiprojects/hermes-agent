# Deploy hermes-api (dev)

Three actors in this system:

1. **This repo (`hermes-agent`)** — code + `.github/workflows/deploy-dev.yml`.
   Pushes to `main` auto-build + deploy to ECS.
2. **`terraform-scripts` repo** — owns the ECS service, task role, Service
   Connect namespace, ECR repo. Applied manually (once per infra change).
3. **RDS** — roles and schemas seeded once via `db_migrations/001_bootstrap.sql`.

Once Terraform is applied and the DB is bootstrapped, deploys are fully
automatic: `git push origin main` → image builds → new task def revision
registered → ECS rolls the service.

---

## Prerequisites — one-time setup

### A. Bootstrap the database

Once per environment. Run as RDS master over WireGuard:

```bash
cd hermes-agent
psql "postgres://<master>:<pw>@<rds-host>:5432/postgres?sslmode=require" \
     -v ON_ERROR_STOP=1 \
     -v reader_password="'<reader-pw>'" \
     -v writer_password="'<writer-pw>'" \
     -f db_migrations/001_bootstrap.sql
```

### B. Create + populate the hermes secret

Hermes uses its own Secrets Manager secret **`hermes-agent-dev`** — kept
separate from the chefbook secret so hermes keys can be rotated
independently and the chefbook task's IAM policy stays scoped to its
own data.

```bash
aws secretsmanager create-secret \
  --name hermes-agent-dev \
  --description "Secrets for the hermes-api ECS service" \
  --secret-string "$(cat <<'EOF'
{
  "OPENROUTER_API_KEY": "sk-or-v1-...",
  "DB_PASSWORD":        "<reader-pw>",
  "DB_RW_PASSWORD":     "<writer-pw>"
}
EOF
)" \
  --region eu-north-1
```

If the secret already exists, use `put-secret-value` instead of
`create-secret` (same `--secret-string`).

Constraints:
- `DB_PASSWORD` **must** match the reader password you passed to
  `001_bootstrap.sql`.
- `DB_RW_PASSWORD` **must** match the writer password from the same.

Terraform references the secret via `data "aws_secretsmanager_secret"`
so it must exist *before* `terraform apply` in `environments/dev/` runs.

### C. Apply the Terraform changes

From `terraform-scripts` repo, after pulling the edits:

```bash
# 1. Refresh the GitHub Actions IAM user's PassRole permissions
cd environments/iam
terraform init
terraform apply                         # adds hermes task role ARNs

# 2. Create the hermes ECS service + ECR repo + Service Connect namespace
cd ../dev
terraform init
terraform apply                         # first apply fails the ECS service
                                        # because ECR is empty — that's
                                        # expected. See step D below.
```

You also need to **manually edit** `modules/ecs/main.tf` to add a
`service_connect_configuration` block to `aws_ecs_service "app"` — see
`modules/ecs/PATCH_app_service.md` for the exact snippet.

Grab the Terraform outputs for later:

```bash
terraform output hermes_ecr_repository_url
terraform output hermes_ecs_cluster_name
terraform output hermes_ecs_service_name
terraform output hermes_task_family
```

### D. Seed the ECR repo with a first image

Before the ECS service can start, push an initial image. This matches what
GHA does, just run once locally:

```bash
cd hermes-agent

ACCOUNT_ID=878070683567
REGION=eu-north-1
REPO=chefbook-dev-hermes

aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

docker buildx build \
  --platform linux/amd64 \
  -t "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO:latest" \
  --push .
```

Then `terraform apply` again in `environments/dev/` — the ECS service will
start successfully this time.

### E. Configure GitHub Actions on the hermes-agent repo

Go to **Settings → Secrets and variables → Actions**:

**Secrets** (from the `github-actions-ecr` IAM user created by
`environments/iam/`):

| Secret | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | access key of the `github-actions-ecr` IAM user |
| `AWS_SECRET_ACCESS_KEY` | secret of the same |

Generate once with `aws iam create-access-key --user-name github-actions-ecr`.

**Variables** (matches the Terraform outputs from step A):

| Variable | Value |
|---|---|
| `AWS_ACCOUNT_ID` | `878070683567` |
| `AWS_REGION` | `eu-north-1` |
| `ECR_REPOSITORY` | `chefbook-dev-hermes` |
| `ECS_CLUSTER` | `chefbook-dev-cluster` |
| `ECS_SERVICE` | `chefbook-dev-hermes-service` |
| `ECS_TASK_FAMILY` | `chefbook-dev-hermes` |

### F. Wire chefbook to reach hermes

In the chefbook API repo's task-definition env block, add:

```
HERMES_BASE_URL = http://hermes-api:8000
```

Then redeploy chefbook. Its pod now resolves `hermes-api` via Service
Connect — traffic stays inside the cluster.

---

## Day-to-day — deploys are automatic

Push to `main`:

```bash
git push origin main
```

The workflow:

1. Builds the image for `linux/amd64` with layer cache (typically 2–3 min).
2. Pushes to `chefbook-dev-hermes:<sha>` and `:latest`.
3. Pulls the current live task def, swaps the image to the new SHA.
4. Registers a new task definition revision.
5. Updates `chefbook-dev-hermes-service`. ECS rolling-deploys the new
   revision. Workflow waits up to 15 min for stability.

You can also trigger manually from the Actions tab (workflow_dispatch)
with an optional `reason` field.

---

## Rolling back

Find a prior revision number:

```bash
aws ecs list-task-definitions \
  --family-prefix chefbook-dev-hermes \
  --sort DESC --max-items 10 \
  --region eu-north-1
```

Pin the service to it:

```bash
aws ecs update-service \
  --cluster chefbook-dev-cluster \
  --service chefbook-dev-hermes-service \
  --task-definition chefbook-dev-hermes:<REVISION> \
  --region eu-north-1
```

ECS rolls the old revision back in.

---

## Adding a database migration

1. Write `db_migrations/002_<description>.sql`, idempotent.
2. Run it against RDS over WireGuard, same command as step B.
3. Then push the code that depends on the new schema. The app does not
   run DDL — migrations always land before code.

---

## Operational

- **Logs**: CloudWatch log group `chefbook-dev-app`, stream prefix `hermes/`.
- **Exec into a task**: `aws ecs execute-command --cluster
  chefbook-dev-cluster --task <id> --container hermes-api --interactive
  --command /bin/bash` (the task role has `ssmmessages:*`).
- **Health**: inside another chefbook container, `curl http://hermes-api:8000/healthz`.
- **Scaling**: raise `hermes_desired_count` in Terraform. The job queue is
  Postgres-backed (`FOR UPDATE SKIP LOCKED`), so multiple replicas share
  work safely.

---

## Prod

Mirror of dev: copy the same wiring into `environments/prod/main.tf` with
appropriate values. Add a second workflow `deploy-prod.yml` that only
triggers on tag push (`v*`) or manual dispatch, and uses `vars.*` with a
`prod-` prefix.
