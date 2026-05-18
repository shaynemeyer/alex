# Architecture Context

## Stack

| Layer           | Technology                          | Role                                                               |
| --------------- | ----------------------------------- | ------------------------------------------------------------------ |
| Frontend        | Next.js + TypeScript                | SaaS portfolio dashboard (Pages Router)                            |
| UI              | Tailwind + Recharts                 | Styling and interactive financial chart components                 |
| Auth            | Clerk                               | User identity, route protection, and multi-tenant user management  |
| Database        | Supabase (PostgreSQL)               | Portfolios, instruments, reports, chart data, retirement analyses  |
| DB Access       | Supabase Python client              | HTTP access via Supabase REST API — no VPC or connection pools     |
| Agent Framework | OpenAI Agents SDK (`openai-agents`) | Multi-agent orchestration: planning, analysis, charting, research  |
| LLM             | AWS Bedrock (Nova Pro via LiteLLM)  | Inference for all agents using `bedrock/<model_id>` via LiteLLM   |
| Embeddings      | SageMaker Serverless (MiniLM-L6-v2) | 384-dimensional embeddings for document ingestion and search       |
| Vector Storage  | S3 Vectors                          | Knowledge base for market research (90% cheaper than OpenSearch)   |
| Compute         | AWS Lambda + App Runner             | Agent Lambda functions; Researcher runs on App Runner              |
| Orchestration   | SQS                                 | Queue-based triggering of the Financial Planner orchestrator       |
| Scheduling      | EventBridge                         | Triggers Researcher agent every 2 hours for background research    |
| IaC             | Terraform                           | Independent per-guide directories; local state files               |
| Package Manager | uv                                  | All Python code — never use `pip` or `python` directly            |

## System Boundaries

- `backend/planner/` — Orchestrator Lambda: receives SQS events, coordinates all specialist agents, retrieves vector context.
- `backend/tagger/` — Instrument classification Lambda: uses Structured Outputs to enrich unknown ETF/equity symbols.
- `backend/reporter/` — Report Writer Lambda: generates markdown portfolio narratives and stores them in Aurora.
- `backend/charter/` — Chart Maker Lambda: produces Recharts-compatible JSON for portfolio visualizations.
- `backend/retirement/` — Retirement Specialist Lambda: runs Monte Carlo projections and stores income charts.
- `backend/researcher/` — Autonomous research agent on App Runner: browses the web via Playwright MCP, stores insights in S3 Vectors.
- `backend/ingest/` — Ingestion Lambda: receives documents via API Gateway, generates embeddings via SageMaker, stores vectors in S3 Vectors.
- `backend/database/` — Shared database library (Pydantic models + Aurora Data API helpers) used by all agents.
- `backend/api/` — FastAPI Lambda: REST backend for the Next.js frontend (portfolio CRUD, job status, reports).
- `frontend/pages/` — Next.js page routes: dashboard, portfolio management, analysis results.
- `frontend/components/` — UI components: charts, report viewers, portfolio tables.
- `frontend/lib/` — Shared utilities: API client, Clerk auth helpers.
- `terraform/` — Independent directories per guide (2–8); each has its own `terraform.tfvars` and local state.

## Storage Model

- **Supabase**: users, portfolios, instruments (with classifications), reports, chart data, retirement projections, and job status. Also stores `research_documents` written by the Researcher/ingest pipeline.
- **S3 Vectors**: vector embeddings for similarity search; queried by the Financial Planner for research context at analysis time.
- **S3 (Lambda packages)**: Lambda deployment packages >50MB are stored in S3 before Lambda upload.
- **ECR**: Docker image for the Researcher App Runner container.
- **Secrets Manager / env vars**: Supabase URL and service key (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`) passed to Lambda functions as environment variables.

## Auth and Multi-Tenancy Model

- Every user is authenticated via Clerk; Clerk user ID is the tenant key in Supabase.
- Portfolio and report records are scoped to a Clerk user ID — agents never read across user boundaries.
- The API Lambda validates the Clerk JWT on every request before any database operation.
- Supabase is accessed server-side only (service key); the Supabase client is never exposed to the browser.
- Clerk is integrated using the Next.js Pages Router (not App Router).

## Agent Collaboration Pattern

```
User Request → SQS Queue → Financial Planner (Orchestrator)
                                ├─→ InstrumentTagger (if unknown symbols)
                                ├─→ Report Writer  ─┐
                                ├─→ Chart Maker    ─┼─→ Aurora (results)
                                └─→ Retirement     ─┘

EventBridge (every 2hrs) → Researcher → S3 Vectors (knowledge base)
Financial Planner → S3 Vectors (retrieve research context)
```

## LLM and Agent Implementation Model

- All agents use `openai-agents` (`from agents import Agent, Runner, trace`).
- LiteLLM bridges to Bedrock: `LitellmModel(model="bedrock/<model_id>")`.
- LiteLLM requires `os.environ["AWS_REGION_NAME"]` — not `AWS_REGION` or `DEFAULT_AWS_REGION`.
- **Critical constraint**: due to a LiteLLM + Bedrock limitation, a single Agent cannot use both Structured Outputs and Tool calling. Each agent uses one or the other, never both.
- Agents that need user-scoped database access use `Agent[ContextType]` with `RunContextWrapper` to pass context into tools.
- Standard agent invocation pattern:
  ```python
  with trace("Agent Name"):
      agent = Agent(name="...", instructions=INSTRUCTIONS, model=model, tools=tools)
      result = await Runner.run(agent, input=task, max_turns=20)
  ```

## Deployment Model

- Each `terraform/N_name/` directory is independent with its own state and `terraform.tfvars`.
- `terraform.tfvars` must be configured (copied from `.tfvars.example`) before `terraform apply`.
- Lambda packages requiring native dependencies are built with Docker/Podman targeting `linux/amd64`.
- `backend/package_docker.py` handles packaging; Docker/Podman must be running before executing it.
- The root `.env` file accumulates ARNs and endpoints across guides as infrastructure is deployed.

## Invariants

1. All Python is run via `uv run` — never `python` or `pip` directly.
2. Agent Lambda functions do not make synchronous HTTP calls to each other; the Planner invokes specialist agents via the AWS SDK (Lambda invoke).
3. A single agent uses either Structured Outputs or Tool calling — never both (LiteLLM/Bedrock constraint).
4. User data is always scoped by Clerk user ID; agents never access cross-user data.
5. Terraform directories are independent; destroying one does not affect another's state.
6. LiteLLM Bedrock integration requires `AWS_REGION_NAME` — other region env var names will silently fail.
7. The Researcher agent operates independently of the Planner; it is never invoked by the orchestrator.
