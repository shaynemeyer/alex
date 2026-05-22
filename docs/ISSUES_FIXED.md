# Issues Fixed

## 2026-05-22 — Lambda Packaging Fails: Docker Not Found

**Affected:** `backend/tagger/package_docker.py`, `backend/reporter/package_docker.py`, `backend/charter/package_docker.py`, `backend/planner/package_docker.py`, `backend/retirement/package_docker.py`

All per-agent packaging scripts were hardcoded to call `docker` (e.g. `["docker", "run", "--rm", ...]` and `["docker", "--version"]`). This project uses **Podman** as the container runtime, so every script failed immediately with `Error: Docker is not installed or not in PATH`.

**Fix:** Replaced all `"docker"` string literals with `"podman"` in the five affected scripts.

---

## 2026-05-22 — All Agent Test Fixes

### `SupabaseClient` has no attribute `update`

**Affected:** `backend/tagger/lambda_handler.py`, `backend/planner/market.py`

`SupabaseClient` only exposes a `table()` method. Code was calling `db.client.update(table, data, condition, params)` which does not exist.

**Fix:** Replaced with the correct Supabase query builder chain: `db.client.table(...).update(data).eq(column, value).execute()`. For the tagger, the insert/update branch was simplified to a single `db.instruments.create_instrument()` call, which already uses `upsert(on_conflict="symbol")`.

---

### `Jobs.update_*()` methods return `None`, causing false save failures

**Affected:** `backend/reporter/lambda_handler.py`, `backend/retirement/lambda_handler.py`, `backend/charter/lambda_handler.py`

All `Jobs.update_report()`, `update_retirement()`, and `update_charts()` methods return `None` (no return value). Code was assigning the result to `success` and branching on it, so saves always appeared to fail even when they succeeded.

**Fix:** Removed the `success` return value check. Each method is called directly; if it raises, the exception propagates. Return value is now hardcoded `True` after the call.

---

### `Jobs` object has no attribute `delete`

**Affected:** `backend/retirement/test_simple.py`, `backend/database/src/models.py`

The test cleanup called `db.jobs.delete(job_id)` but no such method existed on the `Jobs` class.

**Fix:** Added `Jobs.delete()` to `backend/database/src/models.py`:

```python
def delete(self, job_id: str) -> None:
    self.db.table("jobs").delete().eq("id", job_id).execute()
```

---

### Reporter agent outputs reasoning narration before the report

**Affected:** `backend/reporter/templates.py`

The model was prefacing the markdown report with narration like "Now I have the market context needed. Let me analyze..." before the actual content.

**Fix:** Tightened the prompt instruction to: "Respond with ONLY the markdown report. Do not include any preamble, narration, or thinking text. Start directly with the first markdown heading."
