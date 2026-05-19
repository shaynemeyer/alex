# Alex - Agentic Learning Equities eXplainer

**Alex** (Agentic Learning Equities eXplainer) is a multi-agent SaaS financial planning platform — the capstone for Weeks 3-4 of Ed Donner's "AI in Production" course on Udemy.

---

## Directory Structure

```ascii
alex/
├── backend/
│   ├── planner/         # Orchestrator agent (Lambda)
│   ├── tagger/          # Instrument classification agent (Lambda)
│   ├── reporter/        # Portfolio analysis agent (Lambda)
│   ├── charter/         # Visualization agent (Lambda)
│   ├── retirement/      # Retirement projection agent (Lambda)
│   ├── researcher/      # Market research agent (App Runner)
│   ├── ingest/          # Document ingestion Lambda
│   ├── database/        # Shared database library
│   └── api/             # FastAPI backend for frontend
├── frontend/            # NextJS React application
├── terraform/           # Independent IaC directories (each has own state)
│   ├── 2_sagemaker/
│   ├── 3_ingestion/
│   ├── 4_researcher/
│   ├── 6_agents/
│   ├── 7_frontend/
│   └── 8_enterprise/
└── scripts/             # deploy.py, run_local.py, destroy.py
```

---

## Terraform

Each `terraform/N_*/` directory is **independent** with its own local state. No remote S3 state bucket needed.

- Always copy `terraform.tfvars.example` → `terraform.tfvars` and fill in all values before `terraform apply`
- Use `terraform output` in a previous directory to get ARNs needed by the next
- Destroy in reverse order when cleaning up

---

## Python / Tooling

- **Always use `uv`**: `uv add package`, `uv run script.py` — never `pip install` or bare `python`
- **Container runtime**: user uses **Podman** (not Docker). Use `podman` for all container commands and Lambda packaging
- Lambda packages are built for `linux/amd64` via container

Each agent directory has:

- `lambda_handler.py` — Lambda entry point, runs the agent
- `agent.py` — Agent creation
- `templates.py` — Prompts

Test files:

- `test_simple.py` — Local with `MOCK_LAMBDAS=true`
- `test_full.py` — Against deployed AWS resources

---

## Agent SDK Patterns (OpenAI Agents SDK)

Package: `openai-agents` (not `agents`). Import: `from agents import Agent, Runner, trace`

LiteLLM connects to Bedrock:

```python
model = LitellmModel(model=f"bedrock/{model_id}")
```

**LiteLLM requires `AWS_REGION_NAME`** (not `AWS_REGION` or `DEFAULT_AWS_REGION`):

```python
os.environ["AWS_REGION_NAME"] = bedrock_region
```

**Limitation**: An agent cannot use both Structured Outputs and Tool calling via LiteLLM+Bedrock — use one or the other per agent.

Standard handler pattern:

```python
model, tools, task = create_agent(job_id, portfolio_data, user_preferences, db)

with trace("Retirement Agent"):
    agent = Agent(
        name="Retirement Specialist",
        instructions=RETIREMENT_INSTRUCTIONS,
        model=model,
        tools=tools,
    )
    result = await Runner.run(agent, input=task, max_turns=20)
    response = result.final_output
```

Context passing for tools that need user identity:

```python
with trace("Reporter Agent"):
    agent = Agent[ReporterContext](
        name="Report Writer", instructions=REPORTER_INSTRUCTIONS, model=model, tools=tools
    )
    result = await Runner.run(agent, input=task, context=context, max_turns=10)

@function_tool
async def get_market_insights(wrapper: RunContextWrapper[ReporterContext], symbols: List[str]) -> str:
    ...
```

---

## Model Strategy

Use **Nova Pro**, not Claude Sonnet (rate limits too strict):

- Model IDs: `us.amazon.nova-pro-v1:0` or `eu.amazon.nova-pro-v1:0`
- Requires inference profiles; grant access in Bedrock console (may need multiple regions)

Agent Collaboration Pattern:

```ascii
User Request → SQS Queue → Planner (Orchestrator)
                            ├─→ Tagger (if needed)
                            ├─→ Reporter ──┐
                            ├─→ Charter ───┼─→ Results → Database
                            └─→ Retirement ┘
```

---

## Common Issues

**Podman not running** — packaging scripts fail; check `podman ps` works first.

**Bedrock access denied** — model access not granted or wrong region; check Bedrock console → Model access. Inference profiles need multi-region approval.

**Terraform tfvars missing** — cryptic errors; always verify `terraform.tfvars` exists and is complete.

**AWS region mismatch** — LiteLLM needs `AWS_REGION_NAME`; verify env vars propagate from tfvars. Add logging to confirm which region is in use.

**Lambda failures** — check CloudWatch: `aws logs tail /aws/lambda/alex-{agent-name} --follow`. Common causes: bad package, missing env vars, IAM permissions.

**Aurora not ready** — takes 10-15 min to reach "available". Verify Data API enabled (`EnableHttpEndpoint: true`). Use `terraform output` in `5_database` for correct ARNs.

---

## Key Config Files

| File                           | Purpose                                           |
| ------------------------------ | ------------------------------------------------- |
| `.env`                         | Root env vars (populated incrementally per guide) |
| `frontend/.env.local`          | Clerk keys for frontend                           |
| `terraform/*/terraform.tfvars` | Per-directory infra config (copy from `.example`) |
