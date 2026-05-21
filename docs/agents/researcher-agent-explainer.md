# Researcher Agent Explainer

The Researcher agent is an **autonomous investment research service** — its job is to browse live financial websites, synthesise a brief analysis, and persist the findings to the Alex knowledge base via the Ingest Lambda. It runs as a containerised AWS Lambda function exposed through a public Lambda Function URL, and is triggered either on demand (HTTP POST) or automatically every two hours by an EventBridge Scheduler.

---

## What it does

1. Receives a research topic (or picks a trending one autonomously)
2. Opens a headless Chromium browser via the Playwright MCP server
3. Visits up to two financial pages (Yahoo Finance, MarketWatch, etc.)
4. Produces a concise bullet-point analysis using Amazon Bedrock (Nova Pro)
5. Calls `ingest_financial_document` to store the analysis in the knowledge base

---

## Architecture overview

```mermaid
flowchart LR
    CLIENT[Caller] -->|POST /research| LFU[Lambda Function URL]
    EB[EventBridge Scheduler every 2h] -->|invoke| SCHED[Scheduler Lambda]
    SCHED -->|GET /research/auto| LFU
    LFU --> LAMBDA[alex-researcher Lambda]
    LAMBDA --> BEDROCK[Amazon Bedrock Nova Pro]
    LAMBDA --> MCP[Playwright MCP Server stdio]
    MCP --> CHROME[Headless Chromium]
    CHROME -->|browse| WEB[Financial Websites]
    LAMBDA -->|ingest_financial_document| ALEX_API[Alex API Gateway]
    ALEX_API --> INGEST[Ingest Lambda]
    INGEST --> S3V[(S3 Vectors)]
```

---

## Request flow

```mermaid
flowchart TD
    REQ[HTTP Request] --> ROUTE{Endpoint}
    ROUTE -->|POST /research| MANUAL[topic from body optional]
    ROUTE -->|GET /research/auto| AUTO[no topic agent picks]
    MANUAL --> RUN[run_research_agent topic]
    AUTO --> RUN
    RUN --> QUERY{topic provided?}
    QUERY -->|yes| Q1[Research this investment topic: topic]
    QUERY -->|no| Q2[DEFAULT_RESEARCH_PROMPT pick trending topic]
    Q1 --> AGENT[OpenAI Agents SDK Runner.run]
    Q2 --> AGENT
    AGENT --> OUT[final_output string]
    OUT --> RESP[HTTP response]
```

---

## Agent internals

```mermaid
flowchart TD
    AGENT[Alex Investment Researcher Agent] --> INSTRUCT[get_agent_instructions with today date]
    AGENT --> MODEL[LitellmModel bedrock/us.amazon.nova-pro-v1:0]
    AGENT --> TOOLS[tools: ingest_financial_document]
    AGENT --> MCP[mcp_servers: Playwright MCP stdio]
    MCP --> BROWSER[Headless Chromium browser_snapshot browser_navigate]
    AGENT --> RUNNER[Runner.run max_turns=15]
    RUNNER --> STEP1[Step 1: navigate to Yahoo Finance or MarketWatch]
    STEP1 --> STEP2[Step 2: take browser_snapshot read content]
    STEP2 --> STEP3[Step 3: produce 3-5 bullet analysis + recommendation]
    STEP3 --> STEP4[Step 4: call ingest_financial_document]
    STEP4 --> DONE[return final_output]
```

---

## Playwright MCP server

The agent has no built-in web access. Instead, it communicates with a Playwright MCP server over stdio. The MCP server spawns a headless Chromium process and exposes browser tools (`browser_navigate`, `browser_snapshot`, etc.) as MCP tool calls.

```mermaid
flowchart LR
    AGENT[Agent tool call] -->|stdio JSON-RPC| MCP[MCPServerStdio playwright-mcp]
    MCP -->|spawn| CHROME[Chromium --headless --isolated --no-sandbox]
    CHROME -->|HTTP| WEB[Financial website]
    WEB -->|DOM snapshot| CHROME
    CHROME -->|text content| MCP
    MCP -->|tool result| AGENT
```

**Container path resolution** — in production (Lambda), the binary is pre-installed at `/app/node_modules/.bin/playwright-mcp` and Chromium lives under `/root/.cache/ms-playwright/`. The `create_playwright_mcp_server` function detects the container environment and passes the explicit `--executable-path` to avoid relying on PATH resolution.

---

## `ingest_financial_document` tool

Once the agent has its analysis, it calls this function tool to persist it.

```mermaid
flowchart TD
    CALL[ingest_financial_document topic analysis] --> CHECK{ALEX_API_ENDPOINT set?}
    CHECK -->|no| LOCAL[return success=false local mode]
    CHECK -->|yes| BUILD[build document: text=analysis metadata topic+timestamp]
    BUILD --> RETRY[ingest_with_retries up to 3 attempts exponential backoff]
    RETRY --> POST[httpx POST to ALEX_API_ENDPOINT with x-api-key header]
    POST -->|200| SUCCESS[return success=true document_id]
    POST -->|error| FAIL[return success=false error message]
    RETRY -->|3 failures| FAIL
```

The retry wrapper uses `tenacity` with exponential back-off (1s → 10s) to handle SageMaker cold-start latency on the downstream Ingest Lambda.

---

## Automated scheduling

```mermaid
flowchart LR
    EB[EventBridge Scheduler rate 2h] -->|invoke| SCHED[alex-researcher-scheduler Lambda]
    SCHED -->|HTTP GET /research/auto| LFU[Lambda Function URL]
    LFU --> RESEARCHER[alex-researcher Lambda]
    RESEARCHER --> KB[(Knowledge Base S3 Vectors)]
```

The Scheduler Lambda (`backend/scheduler/`) is a thin HTTP caller — it reads `APP_RUNNER_URL` from its environment and hits the `/research/auto` endpoint. EventBridge uses its own IAM role (`alex-eventbridge-scheduler-role`) with `lambda:InvokeFunction` permission scoped to the Scheduler Lambda ARN.

---

## Container image

```mermaid
flowchart TD
    BASE[python:3.12-slim linux/amd64] --> NODE[Install Node.js 22]
    NODE --> PW[npx playwright install --with-deps chromium]
    PW --> MCP_PKG[npm install @playwright/mcp latest]
    MCP_PKG --> UV[pip install uv]
    UV --> DEPS[uv sync --frozen pyproject.toml]
    DEPS --> CODE[COPY .py files]
    CODE --> EP[ENTRYPOINT /app/.venv/bin/python -m awslambdaric]
    EP --> CMD[CMD server.handler]
```

The entry point bypasses `uv run` at invocation time — the venv Python is called directly so the Lambda runtime does not trigger uv filesystem writes under the read-only `/tmp` constraint.

---

## Deployment pipeline

```mermaid
flowchart TD
    TF1[terraform apply 4_researcher] --> ECR[ECR repo alex-researcher]
    TF1 --> ROLE[IAM role alex-researcher-lambda-role]
    ROLE --> BP[Policies: AWSLambdaBasicExecutionRole + Bedrock InvokeModel]
    DEPLOY[uv run deploy.py] --> LOGIN[podman login to ECR]
    LOGIN --> BUILD[podman build --platform linux/amd64]
    BUILD --> PUSH[podman push to ECR with timestamped tag]
    PUSH --> UPDATE[aws lambda update-function-code]
    UPDATE --> WAIT[poll LastUpdateStatus=Successful]
    TF1 --> LFU_TF[Lambda Function URL authorization=NONE]
    LFU_TF --> LAMBDA_TF[alex-researcher Lambda timeout=300s memory=2048MB]
    LAMBDA_TF --> ENV_VARS[Env: OPENAI_API_KEY ALEX_API_ENDPOINT ALEX_API_KEY BEDROCK_REGION RESEARCHER_MODEL]
```

---

## HTTP endpoints

| Method | Path             | Purpose                                                         |
| ------ | ---------------- | --------------------------------------------------------------- |
| GET    | `/`              | Health check — returns service name and UTC timestamp           |
| GET    | `/health`        | Detailed check — shows API config, region, model, container env |
| POST   | `/research`      | On-demand research; optional `topic` in JSON body               |
| GET    | `/research/auto` | Automated research; agent picks the topic; used by scheduler    |
| GET    | `/test-bedrock`  | Smoke test for Bedrock connectivity (dev/debug only)            |

---

## Key files

| File             | Role                                                                              |
| ---------------- | --------------------------------------------------------------------------------- |
| [server.py](backend/researcher/server.py)       | FastAPI app, Lambda entry point via Mangum, all HTTP endpoints      |
| [context.py](backend/researcher/context.py)      | Agent system prompt (`get_agent_instructions`) and default research prompt         |
| [tools.py](backend/researcher/tools.py)        | `ingest_financial_document` function tool with retry logic                        |
| [mcp_servers.py](backend/researcher/mcp_servers.py)  | `create_playwright_mcp_server` — configures stdio MCP for Playwright              |
| [deploy.py](backend/researcher/deploy.py)       | Deployment script: builds container, pushes to ECR, updates Lambda               |
| [Dockerfile](backend/researcher/Dockerfile)      | Multi-stage image: Node + Chromium + Playwright MCP + Python deps                |
| [pyproject.toml](backend/researcher/pyproject.toml)  | Dependencies: `openai-agents[litellm]`, `fastapi`, `playwright`, `tenacity`, etc. |

---

## Environment variables

| Variable            | Default                           | Purpose                                             |
| ------------------- | --------------------------------- | --------------------------------------------------- |
| `RESEARCHER_MODEL`  | `bedrock/us.amazon.nova-pro-v1:0` | Bedrock model ID passed to LitellmModel             |
| `BEDROCK_REGION`    | `us-west-2`                       | AWS region for Bedrock inference                    |
| `ALEX_API_ENDPOINT` | _(required for ingest)_           | URL of the Ingest Lambda API Gateway endpoint       |
| `ALEX_API_KEY`      | _(required for ingest)_           | API key sent as `x-api-key` to the Ingest endpoint  |
| `OPENAI_API_KEY`    | _(required by SDK)_               | Needed by `openai-agents` SDK even when using LiteLLM |
| `MCP_LOGGING`       | _(optional)_                      | Enable verbose MCP stdio logging for debugging      |

---

## Notable design decisions

- **Lambda over App Runner** — despite the name "researcher service", the agent runs as a Lambda function (not App Runner). Lambda's 300s timeout is sufficient for a 2-page browse + ingest cycle; Lambda avoids the cost of a permanently running App Runner instance.
- **Playwright via MCP** — web browsing is delegated entirely to the Playwright MCP server over stdio. The agent never calls browser APIs directly; it just makes tool calls. This keeps the agent code decoupled from browser internals.
- **Pre-baked binary path** — `@playwright/mcp` is installed at image build time into `/app/node_modules/.bin/` so the Lambda runtime never hits npm. This avoids network calls and filesystem permission issues inside the Lambda execution environment.
- **Direct venv Python as entrypoint** — `uv run` writes to the filesystem; inside Lambda's read-only environment this causes errors. Calling `/app/.venv/bin/python` directly sidesteps uv entirely.
- **Concise prompting by design** — the agent instructions cap browsing at two pages and analysis at 3–5 bullets. This keeps execution well within the 300s Lambda timeout and reduces LLM token cost per run.
- **Mangum bridge** — `Mangum(app)` wraps the FastAPI ASGI app so the same codebase can be invoked as a Lambda function or run locally with `uvicorn` without any code changes.
