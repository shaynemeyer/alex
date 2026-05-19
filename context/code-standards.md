# Code Standards

## General

- Keep modules small and single-purpose. Each file owns one clear responsibility.
- Fix root causes — do not layer workarounds or add defensive `isinstance` / `try/except` blocks that hide the real error.
- Do not mix unrelated concerns in one module, handler, or component.
- Work incrementally: one change at a time, validate before moving on.
- Never use emojis in code, print statements, or log messages.

## Python (Backend)

- Use `uv` for all package management: `uv add <package>`, `uv run <script>`. Never `pip install` or bare `python`.
- Every backend directory is its own `uv` project with its own `pyproject.toml` and `uv.lock`.
- Use `logging` (not `print`) in all Lambda and agent code; set level at the module top with `logger = logging.getLogger()`.
- Validate and parse Lambda event input at the top of `lambda_handler`; return `400` before any logic runs if required fields are missing.
- Use module-level docstrings on every file. Keep inline comments to a minimum — only when the *why* is non-obvious.
- Keep functions short. If a function exceeds ~30 lines, split it.

## OpenAI Agents SDK

- Import as `from agents import Agent, Runner, trace`. The package name is `openai-agents`, not `agents`.
- Each agent directory has a fixed structure: `lambda_handler.py`, `agent.py`, `templates.py`.
- An agent may use Structured Outputs **or** Tools — never both in the same agent (LiteLLM/Bedrock limitation).
- Pass typed context via `Agent[ContextType]` and `RunContextWrapper[ContextType]`; never thread context through global state.
- Always wrap agent runs with `with trace("Agent Name"):`.
- Set `AWS_REGION_NAME` (not `AWS_REGION`) via `os.environ` before constructing `LitellmModel` — LiteLLM requires this specific key.
- Read model ID and region from environment variables; never hardcode them.

## AWS and Infrastructure

- All configuration flows from `terraform.tfvars` → Lambda environment variables → Python `os.getenv(...)`. No hardcoded ARNs, regions, or bucket names in code.
- Use `os.getenv("KEY", "default")` at the point of use; centralise defaults in one place per agent (`create_agent` or top of `lambda_handler`).
- Lambda packages must be built with Podman targeting `linux/amd64`. Use `package_docker.py` — never build locally and upload directly.
- Each terraform directory is independent with its own local state. Do not share state between directories.

## Testing

- Each agent has `test_simple.py` (local, with `MOCK_LAMBDAS=true`) and `test_full.py` (live AWS).
- Run `test_simple.py` first; only run `test_full.py` after the package is deployed.
- Do not mock at the database or AWS SDK level in `test_full.py` — those tests must hit real infrastructure.

## TypeScript / Next.js (Frontend)

- The frontend uses Next.js Pages Router (not App Router) — required by Clerk.
- Add `"use client"` equivalent (`useState`, `useEffect`) only when the component needs browser interactivity.
- Define explicit `interface` types for all API response shapes in `lib/api.ts`. Avoid `any`.
- Keep route handlers in `pages/api/` thin — push business logic into `lib/`.
- All backend calls go through the helpers in `lib/api.ts`; never call `fetch` directly from page components.
- Use `NEXT_PUBLIC_API_URL` for the API base URL; never hardcode gateway URLs.

## File Organisation

### Backend

- `lambda_handler.py` — entry point, event parsing, status updates, calls `agent.py`.
- `agent.py` — `create_agent()` factory, tool definitions, context dataclass.
- `templates.py` — all prompt strings and instructions.
- `observability.py` — LangFuse tracing wrapper.
- `test_simple.py` / `test_full.py` — local and AWS integration tests.

### Frontend

- `pages/` — route-level components; no business logic.
- `components/` — UI composition only.
- `lib/` — API client, config, shared utilities.
- Name files after the responsibility they contain, not the technology.
