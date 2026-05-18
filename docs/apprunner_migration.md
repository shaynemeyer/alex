# App Runner → Lambda Container Migration

## Background

The Researcher service was originally deployed on AWS App Runner. App Runner has been deprecated for this use case in favour of Lambda container images, which offer:

- **Lower cost** for infrequent invocations (pay per request, not per running hour)
- **No idle charges** (App Runner billed even when idle)
- **Simpler scheduler integration** (scheduler Lambda invokes researcher Lambda directly, no HTTP round-trip)
- **Same runtime** — the same Docker image and FastAPI code runs in both environments

The Lambda max timeout is 15 minutes, well above the 20–30 seconds a typical research task takes.

---

## Files Changed

### `backend/researcher/Dockerfile`

| Before                                            | After                                                                                   |
| ------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `CMD ["uv", "run", "uvicorn", "server:app", ...]` | `ENTRYPOINT ["/app/.venv/bin/python", "-m", "awslambdaric"]` / `CMD ["server.handler"]` |
| No `@playwright/mcp` pre-install                  | `RUN npm install -g @playwright/mcp@latest`                                             |
| No npm cache config                               | `ENV NPM_CONFIG_CACHE=/tmp/.npm`                                                        |

**Why the npm changes?** Lambda container filesystems are read-only outside of `/tmp`. If `npx @playwright/mcp@latest` ran at invocation time without a pre-installed package, it would try to write to the npm cache (by default under `~/.npm`, which is read-only). Pre-installing globally and pointing the cache to `/tmp` avoids this.

**Why `/app/.venv/bin/python` instead of `uv run`?** `uv run` can attempt venv sync writes at startup. Using the venv's Python binary directly avoids any filesystem writes at Lambda invocation time.

---

### `backend/researcher/server.py`

Added at the bottom (before `if __name__ == "__main__"`):

```python
from mangum import Mangum
handler = Mangum(app)
```

`Mangum` is an ASGI adapter that converts Lambda events (Function URL or API Gateway) into the ASGI format that FastAPI expects. All existing endpoints (`/`, `/health`, `/research`, `/research/auto`, `/test-bedrock`) work without modification.

---

### `backend/researcher/mcp_servers.py`

Changed `npx @playwright/mcp@latest` → `npx @playwright/mcp` (removed `@latest`).

With `@latest`, `npx` checks the npm registry on every invocation to find the newest version — this requires a cache write. Without the version tag, `npx` uses the globally pre-installed package directly, with no network check and no writes needed.

---

### `backend/researcher/pyproject.toml` + `uv.lock`

Added two dependencies (via `uv add`):

- `mangum>=0.21.0` — ASGI ↔ Lambda adapter
- `awslambdaric>=4.0.0` — Lambda Runtime Interface Client for custom container images

---

### `terraform/4_researcher/main.tf`

**Removed:**

- `aws_apprunner_service.researcher`
- `aws_iam_role.app_runner_role` + `aws_iam_role_policy_attachment.app_runner_ecr_access`
- `aws_iam_role.app_runner_instance_role` + `aws_iam_role_policy.app_runner_instance_bedrock_access`

**Added:**

- `aws_iam_role.researcher_lambda_role` — trust policy for `lambda.amazonaws.com`
- `aws_iam_role_policy_attachment.researcher_lambda_basic` — CloudWatch Logs
- `aws_iam_role_policy.researcher_lambda_bedrock` — same Bedrock permissions as before
- `aws_lambda_function.researcher` — container image, 2048 MB memory, 900s timeout, 1 GB `/tmp`
- `aws_lambda_function_url.researcher` — public HTTPS endpoint, no auth, CORS enabled

**Updated (scheduler):**

- `aws_lambda_function.scheduler_lambda` — env var changed from `APP_RUNNER_URL` to `RESEARCHER_FUNCTION_NAME`
- `aws_iam_role_policy.lambda_scheduler_invoke_researcher` — new policy granting `lambda:InvokeFunction` on the researcher Lambda
- Timeout reduced from 180s to 60s (scheduler now fires async; no need to wait for research to complete)

---

### `terraform/4_researcher/outputs.tf`

| Before                   | After                     |
| ------------------------ | ------------------------- |
| `app_runner_service_url` | `researcher_function_url` |
| `app_runner_service_id`  | `researcher_function_arn` |

---

### `backend/researcher/deploy.py`

Replaced App Runner update logic with:

```python
aws lambda update-function-code \
  --function-name alex-researcher \
  --image-uri <ecr_url>:<tag> \
  --region <region>
```

Polls `Configuration.LastUpdateStatus` until `Successful` (vs. the previous App Runner operation polling). Displays the Lambda Function URL on success.

---

### `backend/researcher/test_research.py`

Replaced App Runner service URL lookup (`aws apprunner list-services`) with:

```python
terraform output -raw researcher_function_url
```

---

### `backend/scheduler/lambda_function.py`

Replaced HTTP call to App Runner with a direct async Lambda invocation:

```python
client.invoke(
    FunctionName=function_name,
    InvocationType="Event",   # async — fire and forget
    Payload=json.dumps(payload),
)
```

The payload is a Lambda Function URL-compatible event routed to `/research/auto`. The scheduler Lambda no longer needs to wait for research to finish (was previously a 3-minute HTTP timeout).

---

## Deployment Flow

```bash
# Step 1: Deploy ECR + IAM role (first time only)
cd terraform/4_researcher
terraform init
terraform apply -target=aws_ecr_repository.researcher \
                -target=aws_iam_role.researcher_lambda_role

# Step 2: Build container image and update Lambda
cd backend/researcher
uv run deploy.py

# Step 3: Deploy the Lambda function and Function URL
cd terraform/4_researcher
terraform apply

# Step 4: Test
uv run test_research.py
uv run test_research.py "NVIDIA AI chip market share"
```

---

## Architecture Diagram (Updated)

```ascii
User ──────────────────────────────► Lambda Function URL
                                          │
Schedule[EventBridge] ──► Lambda       Lambda
                          Scheduler ──► Researcher ──► Bedrock (Nova Pro)
                                          │
                                          └──► API Gateway ──► Lambda Ingest ──► S3 Vectors
```
