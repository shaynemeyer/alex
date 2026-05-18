# Plan: Replace Aurora Serverless v2 with Supabase (Guide 5 Database)

## Context

Guide 5 instructs students to deploy Aurora Serverless v2 PostgreSQL with the AWS Data API (~$43/month minimum). Since we're already adding Supabase for the researcher structured-data feature ([01-supabase-structured-data.md](01-supabase-structured-data.md)), we can use Supabase as the single database for the entire Alex platform — eliminating Aurora's cost and AWS networking complexity.

The `backend/database/` library does not exist yet (it is built in Guide 5), so this is a **greenfield implementation** using Supabase rather than a migration of existing code.

**Connection approach**: `supabase-py` REST API — stateless HTTP, no connection pooling, consistent with the ingest Lambda's Supabase usage, and mirrors the Aurora Data API pattern that Guide 5 was designed around.

---

## Step 1: Create Supabase Tables (SQL Editor)

Run in the Supabase SQL editor (single script):

```sql
-- Core Alex tables (Guide 5 schema)
create table users (
  clerk_user_id            text    primary key,
  display_name             text,
  years_until_retirement   integer,
  target_retirement_income decimal,
  asset_class_targets      jsonb,
  region_targets           jsonb
);

create table instruments (
  symbol                 text    primary key,
  name                   text,
  instrument_type        text,
  current_price          decimal,
  allocation_regions     jsonb,
  allocation_sectors     jsonb,
  allocation_asset_class jsonb
);

create table accounts (
  id              uuid    primary key default gen_random_uuid(),
  clerk_user_id   text    references users(clerk_user_id),
  account_name    text,
  account_purpose text,
  cash_balance    decimal,
  cash_interest   decimal
);

create table positions (
  id         uuid    primary key default gen_random_uuid(),
  account_id uuid    references accounts(id),
  symbol     text    references instruments(symbol),
  quantity   decimal,
  as_of_date date
);

create table jobs (
  id                 uuid        primary key default gen_random_uuid(),
  clerk_user_id      text        references users(clerk_user_id),
  job_type           text,
  status             text,
  request_payload    jsonb,
  report_payload     jsonb,
  charts_payload     jsonb,
  retirement_payload jsonb,
  summary_payload    jsonb,
  error_message      text,
  started_at         timestamptz,
  completed_at       timestamptz
);

-- Research data table (from 01-supabase-structured-data.md)
create table research_documents (
  id            uuid        primary key default gen_random_uuid(),
  vector_id     text        not null,
  topic         text,
  full_text     text        not null,
  bullet_points text[]      not null default '{}',
  researched_at timestamptz,
  created_at    timestamptz not null default now()
);
```

---

## Step 2: Create `backend/database/` Library

### `backend/database/pyproject.toml`

```toml
[project]
name = "alex-database"
version = "0.1.0"
dependencies = ["supabase>=2.0.0", "pydantic>=2.0.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### `backend/database/src/__init__.py`

Exports the `Database` class.

### `backend/database/src/client.py` (replaces DataAPIClient)

Thin `SupabaseClient` wrapper — initialised from `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` env vars (matching the ingest Lambda's naming). All query logic lives in the model methods, not the client.

```python
from supabase import create_client
import os

class SupabaseClient:
    def __init__(self):
        self.client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

    def table(self, name):
        return self.client.table(name)
```

### `backend/database/src/models.py`

`Database` class interface stays **identical** — all agents use `from src import Database; db = Database()` with no changes. Only the internals change from Data API SQL to supabase-py query builder.

Key query mappings:

| Method | supabase-py pattern |
| --- | --- |
| Simple select | `.table('t').select('*').eq('col', val).execute().data` |
| Insert | `.table('t').insert(data).execute().data[0]` |
| Update | `.table('t').update(data).eq('id', id).execute()` |
| Upsert | `.table('t').upsert(data, on_conflict='col1,col2').execute()` |

**Complex queries:**

- `positions.find_by_account(account_id)` — uses FK embed instead of JOIN:

  ```python
  self.db.table('positions').select('*, instruments(name, instrument_type, current_price)').eq('account_id', account_id).execute().data
  ```

  (Requires FK `positions.symbol → instruments.symbol` defined in schema — already present in `001_schema.sql`.)

- `positions.get_portfolio_value(account_id)` — fetch with embed, aggregate in Python:

  ```python
  rows = self.db.table('positions').select('quantity, instruments(current_price)').eq('account_id', account_id).execute().data
  total = sum(float(r['quantity']) * float(r['instruments']['current_price'] or 0) for r in rows)
  ```

- `positions.add_position()` — UPSERT on unique constraint:

  ```python
  self.db.table('positions').upsert(data, on_conflict='account_id,symbol').execute()
  ```

- `instruments.search(query)` — LIKE on two columns:

  ```python
  self.db.table('instruments').select('*').or_(f'symbol.ilike.%{q}%,name.ilike.%{q}%').limit(20).execute().data
  ```

Remove `db.execute_raw()` and `db.query_raw()` from the `Database` class (only used in migration scripts, which now run via Supabase SQL editor).

### `backend/database/src/schemas.py`

Pydantic v2 models: `UserCreate`, `AccountCreate`, `PositionCreate`, `InstrumentCreate`, `JobCreate`. Allocation JSONB fields validated to sum to 100.0.

### `backend/database/migrations/001_schema.sql`

SQL from Step 1, kept as reference. Applied via Supabase SQL editor or `run_migrations.py`.

### `backend/database/run_migrations.py`

Reads `migrations/*.sql` in order and executes via Supabase client.

### `backend/database/seed_data.py`

Inserts 22 ETFs using `db.instruments.create(...)` with full allocation data.

### `backend/database/reset_db.py`

Truncates tables, re-runs migrations, seeds instruments, optionally creates test user (`--with-test-data` flag).

### `backend/database/test_connection.py` _(replaces test_data_api.py)_

Connects and runs a simple query, prints PostgreSQL version and success message.

### `backend/database/verify_database.py`

Counts rows in all tables, validates allocation sums, prints health report with pass/fail banners.

---

## Step 3: Remove `terraform/5_database/`

The Aurora cluster, Secrets Manager secret, security group, subnet group, and IAM role are no longer needed. Delete the entire `terraform/5_database/` directory. Supabase requires no Terraform resources.

---

## Step 4: Update `terraform/6_agents/`

**`terraform/6_agents/variables.tf`** — replace aurora variables:

```hcl
# Remove:
variable "aurora_cluster_arn" { ... }
variable "aurora_secret_arn"  { ... }

# Add:
variable "supabase_url"              { type = string }
variable "supabase_service_role_key" { type = string }
```

**`terraform/6_agents/main.tf`**:

- IAM policy: remove `rds-data:*` and `secretsmanager:GetSecretValue` statements for aurora
- Lambda env vars: replace `AURORA_CLUSTER_ARN` / `AURORA_SECRET_ARN` with `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY`

**`terraform/6_agents/terraform.tfvars.example`**:

```
supabase_url              = "https://xxxx.supabase.co"
supabase_service_role_key = "eyJ..."
```

---

## Step 5: Update `terraform/7_frontend/`

**`terraform/7_frontend/main.tf`**:

- Remove `data "terraform_remote_state" "database"` block (pointed at removed `5_database`)
- Replace all `data.terraform_remote_state.database.outputs.aurora_cluster_arn` references with `var.supabase_url`
- Replace `aurora_secret_arn` references with `var.supabase_service_role_key`
- Remove rds-data IAM policy statements
- Add variable declarations matching Step 4

**`terraform/7_frontend/terraform.tfvars.example`** — same Supabase vars as Step 4.

---

## Step 6: Update `.env.example`

Replace:

```
AURORA_CLUSTER_ARN=...
AURORA_SECRET_ARN=...
```

With:

```
# Part 5 - Database (Supabase)
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

---

## Step 7: Rewrite `guides/5_database.md`

Replace the following sections:

- "Why Aurora Serverless v2" → "Why Supabase" (cost, no VPC, free tier, already used in ingest)
- Step 0 (IAM permissions for RDS) → not needed; remove
- Step 1 (terraform deploy) → "Create Supabase project, get URL and service role key, run SQL from Step 1 above"
- Steps 2–6 remain structurally the same but reference `test_connection.py` instead of `test_data_api.py`
- Cost Management section: replace Aurora pricing with Supabase free-tier and pro-tier notes
- Troubleshooting: replace Data API troubleshooting with Supabase connection troubleshooting

---

## Critical Files

| File                              | Action                                |
| --------------------------------- | ------------------------------------- |
| `backend/database/`               | Create entire directory (new)         |
| `terraform/5_database/`           | Delete (replaced by Supabase)         |
| `terraform/6_agents/variables.tf` | Remove aurora vars, add supabase vars |
| `terraform/6_agents/main.tf`      | Update IAM + Lambda env vars          |
| `terraform/7_frontend/main.tf`    | Remove remote_state ref, update vars  |
| `.env.example`                    | Replace `AURORA_*` with `SUPABASE_*`  |
| `guides/5_database.md`            | Rewrite for Supabase                  |

**Agent Lambda code** (`planner`, `reporter`, `tagger`, `charter`, `retirement`) — **no changes needed**. All use `from src import Database` / `db = Database()`, which remains interface-stable.

---

## Verification

1. Create Supabase project, run SQL from Step 1, confirm tables appear in Table Editor
2. `cd backend/database && uv run test_connection.py` → prints PostgreSQL version
3. `uv run run_migrations.py` → no errors
4. `uv run seed_data.py` → 22 ETFs inserted, confirmed in Supabase Table Editor
5. `uv run reset_db.py --with-test-data` → test user + 3 accounts + 5 positions created
6. `uv run verify_database.py` → all checks pass, final banner shows green
7. `terraform plan` in `terraform/6_agents` → no aurora ARN references remain
