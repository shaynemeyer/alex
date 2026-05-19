# Alex - the Agentic Learning Equities Explainer

## Multi-agent Enterprise-Grade SaaS Financial Planner

### Prerequisites

- **Python** — managed via [uv](https://docs.astral.sh/uv/). Always use `uv run` and `uv add`, never `python` or `pip` directly.
- **Podman** (or Docker) — required to build the researcher container image. Install [Podman Desktop](https://podman-desktop.io/) and ensure `podman machine start` has been run before deploying the researcher.
- **Node.js** — required for the frontend. Use v22 or later.
- **Terraform** — required for all infrastructure. v1.5 or later.
- **AWS CLI** — configured with the `aiengineer` IAM user and your default region.

### The directories

1. **backend** - the agent code, organized into subdirectories, each a uv project (as is the backend parent directory)
2. **frontend** - a NextJS React frontend integrated with Clerk
3. **terraform** - separate terraform subdirectories with state for each part
4. **scripts** - the final deployment script

---

## Notes

This work is based on the amazing work of Ed Donner and his amazing Udemy Course - <https://www.udemy.com/course/generative-and-agentic-ai-in-production>
