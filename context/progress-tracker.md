# Progress Tracker

Update this file whenever the current phase, active feature, or implementation state changes.

## Current Phase

- Phase 1: Foundation

## Current Goal

- Guide 6: Agent Orchestra

## Completed

- Feature 1: Store Researcher Data in Supabase (Structured) — COMPLETE
  - Supabase `research_documents` table created
  - `supabase` dependency added to `backend/ingest/pyproject.toml`
  - `parse_bullet_points()` helper and Supabase write added to `backend/ingest/ingest_s3vectors.py`
  - `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` env vars added to Lambda in `terraform/3_ingestion/main.tf`
  - `package_docker.py` created for ingest (Podman-based, linux/amd64 build)
  - Verified end-to-end: S3 Vectors + Supabase both written on each research run

- Feature 2: Replace Aurora Serverless v2 with Supabase (Guide 5 Database) — COMPLETE ✓ verified
  - `backend/database/pyproject.toml` — replaced `boto3` with `supabase>=2.0.0` + `psycopg2-binary`
  - `backend/database/src/client.py` — replaced `DataAPIClient` with thin `SupabaseClient` wrapper
  - `backend/database/src/models.py` — rewrote all query logic using supabase-py query builder; `Database` interface unchanged
  - `backend/database/src/__init__.py` — exports `SupabaseClient` instead of `DataAPIClient`
  - `backend/database/migrations/001_schema.sql` — updated to use `gen_random_uuid()`, added `research_documents` table
  - `backend/database/run_migrations.py` — rewrote to use `psycopg2` + `DATABASE_URL`
  - `backend/database/seed_data.py` — rewrote to use `Database` model instead of raw boto3
  - `backend/database/verify_database.py` — rewrote for supabase query builder
  - `backend/database/reset_db.py` — rewrote to truncate tables via supabase client
  - `backend/database/test_connection.py` — new file (replaces `test_data_api.py`)
  - `backend/database/test_data_api.py` — deleted
  - `terraform/6_agents/variables.tf` — replaced `aurora_cluster_arn`/`aurora_secret_arn` with `supabase_url`/`supabase_service_role_key`
  - `terraform/6_agents/main.tf` — removed Aurora IAM statements; all 5 Lambda env vars updated
  - `terraform/6_agents/terraform.tfvars.example` — updated with Supabase vars
  - `terraform/7_frontend/main.tf` — removed `data.terraform_remote_state.database`; removed Aurora IAM policy; updated Lambda env vars
  - `terraform/7_frontend/variables.tf` — added `supabase_url` and `supabase_service_role_key`
  - `terraform/7_frontend/terraform.tfvars.example` — updated with Supabase vars

## In Progress

- None.

## Next Up

- None.

## Open Questions

- `terraform/5_database/` — kept as-is (student can delete when ready; no code depends on it)
- `.env.example` — student should replace `AURORA_CLUSTER_ARN`/`AURORA_SECRET_ARN` with `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, and `DATABASE_URL`

## Architecture Decisions

- Supabase write in ingest is non-fatal: if `SUPABASE_URL`/`SUPABASE_SERVICE_KEY` are absent, the block is skipped.
- `run_migrations.py` uses `psycopg2` + `DATABASE_URL` (postgres direct connection) because supabase-py does not support DDL via its REST API.
- All agents still use `from src import Database; db = Database()` — interface unchanged.
- `terraform/5_database/` directory left intact; student should `terraform destroy` it to reclaim Aurora costs.
- RLS (Row Level Security) is intentionally not enabled. All database access goes through Lambda functions using the Supabase service role key, which bypasses RLS by design. User data isolation is enforced in code by always filtering queries with `clerk_user_id`. RLS would only be needed if the frontend called Supabase directly using the anon key — Alex does not do this.

## Session Notes

- None.
