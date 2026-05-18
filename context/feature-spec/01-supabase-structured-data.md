# Plan: Store Researcher Data in Supabase (Structured)

## Context

The researcher agent currently stores analysis as vector embeddings in S3 Vectors (for semantic search by the reporter). The raw text contains topic, timestamp, and bullet-point analysis but is only queryable by similarity — not by topic, date, or content filters. The goal is to **also** write parsed, structured rows to Supabase so the data is SQL-queryable (dashboards, filtering, auditing) while S3 Vectors continues to serve the reporter's semantic search.

---

## Approach

Add a Supabase write to the existing ingest Lambda (`backend/ingest/ingest_s3vectors.py`) immediately after the S3 Vectors put succeeds. Parse the research text into bullet points at write time. No changes to the researcher agent or reporter agent.

---

## Step 1: Create Supabase Table

Run in the Supabase SQL editor:

```sql
create table research_documents (
  id           uuid        primary key default gen_random_uuid(),
  vector_id    text        not null,
  topic        text,
  full_text    text        not null,
  bullet_points text[]     not null default '{}',
  researched_at timestamptz,
  created_at   timestamptz not null default now()
);
```

---

## Step 2: Add `supabase` to the ingest project

```bash
cd backend/ingest
uv add supabase
```

---

## Step 3: Edit `backend/ingest/ingest_s3vectors.py`

**Critical file**: [backend/ingest/ingest_s3vectors.py](backend/ingest/ingest_s3vectors.py)

Add at the top (after existing imports):

```python
from supabase import create_client

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
```

Add a parse helper (before `lambda_handler`):

```python
def parse_bullet_points(text: str) -> list:
    """Extract bullet-point lines from research text."""
    bullets = []
    for line in text.strip().splitlines():
        s = line.strip()
        if not s:
            continue
        if s[0] in ('-', '•', '*') or (len(s) > 2 and s[0].isdigit() and s[1] in '.)'):
            bullets.append(s.lstrip('-•* 0123456789.)').strip())
    return bullets
```

After the `s3_vectors.put_vectors(...)` call (line ~88), add:

```python
        # Write structured record to Supabase
        if SUPABASE_URL and SUPABASE_SERVICE_KEY:
            supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
            supabase.table('research_documents').insert({
                'vector_id': vector_id,
                'topic': metadata.get('topic'),
                'full_text': text,
                'bullet_points': parse_bullet_points(text),
                'researched_at': metadata.get('timestamp'),
            }).execute()
            print(f"Stored structured record in Supabase for vector_id: {vector_id}")
```

Supabase write is intentionally non-fatal — if `SUPABASE_URL`/`SUPABASE_SERVICE_KEY` are absent the block is skipped, so existing deployments without Supabase continue to work.

---

## Step 4: Add env vars to the ingest Lambda terraform

**File**: [terraform/3_ingestion/main.tf](terraform/3_ingestion/main.tf)

In the Lambda `environment.variables` block, add:

```hcl
SUPABASE_URL         = var.supabase_url
SUPABASE_SERVICE_KEY = var.supabase_service_key
```

Add variable declarations (e.g. in `variables.tf` or bottom of `main.tf`):

```hcl
variable "supabase_url"         { type = string; default = "" }
variable "supabase_service_key" { type = string; default = "" }
```

Add to `terraform/3_ingestion/terraform.tfvars`:

```bash
supabase_url         = "https://xxxx.supabase.co"
supabase_service_key = "eyJ..."   # service_role key from Supabase project settings
```

---

## Step 5: Rebuild and redeploy

```bash
# Rebuild Lambda package with new supabase dependency
cd backend/ingest
uv run package_docker.py

# Redeploy ingest Lambda
cd terraform/3_ingestion
terraform apply
```

---

## Verification

1. Trigger a research run via the researcher's `/research` endpoint
2. Check CloudWatch logs for the ingest Lambda — should see `Stored structured record in Supabase`
3. In Supabase dashboard → Table Editor → `research_documents` — row should appear with parsed `bullet_points` array
4. S3 Vectors search should still work normally (reporter unaffected)
