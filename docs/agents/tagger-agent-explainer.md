# Tagger Agent Explainer

The Tagger is a **classification specialist** in the Alex pipeline. Its sole job is to take a list of financial instrument symbols (ETFs, stocks, mutual funds) and enrich them with structured metadata — instrument type, current price, and three allocation breakdowns (asset class, region, sector) — then persist that data to Supabase.

It is invoked by the Planner before downstream agents (Reporter, Charter, Retirement) run, ensuring every instrument in the portfolio is classified before analysis begins.

---

## What it does

1. Receives a list of instrument dicts (`symbol`, `name`, optional `instrument_type`) via a direct Lambda invocation
2. Sends each instrument to the LLM (Bedrock via LiteLLM) asking for a structured `InstrumentClassification`
3. Validates that each of the three allocation categories sums to 100%
4. Upserts the result into the `instruments` table in Supabase

---

## System position

```mermaid
flowchart TD
    PL[Planner Lambda] -->|invoke| TAG[Tagger Lambda]
    TAG --> LLM[Bedrock LLM]
    LLM --> TAG
    TAG --> DB[(Supabase instruments table)]
    PL -->|reads classifications| DB
```

---

## Lambda entry point

[lambda_handler.py](../../backend/tagger/lambda_handler.py) is invoked directly by the Planner (not via SQS). It expects the event shape:

```json
{
  "instruments": [
    { "symbol": "VTI", "name": "Vanguard Total Stock Market ETF" }
  ]
}
```

```mermaid
flowchart TD
    EV[Lambda Event] --> CHK{instruments present?}
    CHK -->|no| E400[400 Bad Request]
    CHK -->|yes| OBS[observe context manager]
    OBS --> PROC[process_instruments async]
    PROC --> TAG_FN[tag_instruments]
    TAG_FN --> DB_UPS[upsert each classification to Supabase]
    DB_UPS --> R200[200 OK with results]
    OBS -->|exception| R500[500 error]
```

The `observe()` context manager wraps the entire execution. If `LANGFUSE_SECRET_KEY` is set, it configures logfire + LangFuse and flushes traces on exit (including a 10-second wait to survive Lambda's rapid shutdown).

---

## Classification flow

The core logic lives in [agent.py](../../backend/tagger/agent.py). `tag_instruments` iterates over the list, calling `classify_instrument` for each one sequentially (with a 0.5-second delay between calls to avoid rate limits).

```mermaid
flowchart TD
    TI[tag_instruments list] --> LOOP{for each instrument}
    LOOP --> DELAY[sleep 0.5s if not first]
    DELAY --> RETRY[classify_with_retry]
    RETRY --> CI[classify_instrument]
    CI --> MODEL[LiteLLM bedrock model]
    MODEL --> AGENT[OpenAI Agents SDK Runner.run]
    AGENT -->|structured output| IC[InstrumentClassification]
    IC --> RESULTS[append to results]
    RETRY -->|RateLimitError| BACKOFF[exponential backoff up to 5 attempts]
    BACKOFF --> CI
    LOOP -->|all done| FILTER[filter out None failures]
    FILTER --> RETURN[return classifications list]
```

`classify_instrument` builds the prompt, creates a single-turn `Agent` with no tools (structured output only), and calls `Runner.run` with `max_turns=5`. It extracts the result with `result.final_output_as(InstrumentClassification)`.

---

## Structured output model

The LLM must return a fully validated `InstrumentClassification` Pydantic object. Three nested models carry the allocation data, each with its own `@field_validator` that enforces the 100% sum rule (±3% tolerance for floating-point rounding).

```mermaid
classDiagram
    class InstrumentClassification {
        +str symbol
        +str name
        +str instrument_type
        +float current_price
        +AllocationBreakdown allocation_asset_class
        +RegionAllocation allocation_regions
        +SectorAllocation allocation_sectors
        +validate_asset_class_sum()
        +validate_regions_sum()
        +validate_sectors_sum()
    }
    class AllocationBreakdown {
        +float equity
        +float fixed_income
        +float real_estate
        +float commodities
        +float cash
        +float alternatives
    }
    class RegionAllocation {
        +float north_america
        +float europe
        +float asia
        +float latin_america
        +float africa
        +float middle_east
        +float oceania
        +float global_
        +float international
    }
    class SectorAllocation {
        +float technology
        +float healthcare
        +float financials
        +float consumer_discretionary
        +float energy
        +float utilities
        +float treasury
        +float corporate
        +float other
    }
    InstrumentClassification --> AllocationBreakdown
    InstrumentClassification --> RegionAllocation
    InstrumentClassification --> SectorAllocation
```

All three allocation models use `extra="forbid"` so unexpected fields from the LLM are rejected immediately.

---

## Database upsert logic

After classification, `process_instruments` in [lambda_handler.py](../../backend/tagger/lambda_handler.py) checks whether each symbol already exists in Supabase. If it does, it updates the row; if not, it creates a new one via `db.instruments.create_instrument`.

```mermaid
flowchart TD
    CL[InstrumentClassification] --> FMT[classification_to_db_format]
    FMT --> STRIP[strip zero-value allocation fields]
    STRIP --> IC[InstrumentCreate]
    IC --> FIND{instrument exists in DB?}
    FIND -->|yes| UPD[db.client.update instruments]
    FIND -->|no| CRE[db.instruments.create_instrument]
    UPD --> OK[append symbol to updated list]
    CRE --> OK
    OK --> ERR{exception?}
    ERR -->|yes| ERRL[append to errors list]
    ERR -->|no| NEXT[next instrument]
```

`classification_to_db_format` in [agent.py](../../backend/tagger/agent.py) converts the nested Pydantic models into plain dicts and strips zero-value keys before writing to the database — keeping rows lean.

---

## Retry strategy

Rate limit handling uses `tenacity`:

| Parameter       | Value                        |
| --------------- | ---------------------------- |
| Retry condition | `RateLimitError` only        |
| Max attempts    | 5                            |
| Backoff         | Exponential, 4s min, 60s max |
| On each sleep   | Log the wait time            |

Non-rate-limit errors propagate immediately and are caught by the per-instrument try/except in `tag_instruments`, which logs the failure and appends `None` (later filtered out).

---

## Prompt design

The agent uses two templates from [templates.py](../../backend/tagger/templates.py):

**`TAGGER_INSTRUCTIONS`** (system prompt) — establishes the role as a financial instrument classifier, explains the three allocation categories, requires each to sum to 100%, and gives concrete examples (SPY, BND, AAPL, VTI, VXUS).

**`CLASSIFICATION_PROMPT`** (user turn) — fills in `{symbol}`, `{name}`, and `{instrument_type}`, then explicitly lists every valid field name in each allocation category so the LLM knows the exact schema.

The agent has `tools=[]` — no tool calls, pure structured output. This is intentional: the OpenAI Agents SDK via LiteLLM+Bedrock does not support both structured outputs and tool calling simultaneously.

---

## Key dependencies

| Package                  | Role                                                 |
| ------------------------ | ---------------------------------------------------- |
| `openai-agents[litellm]` | Agent runner + LiteLLM Bedrock bridge                |
| `pydantic`               | Structured output validation                         |
| `tenacity`               | Retry with exponential backoff                       |
| `alex-database`          | Shared Supabase database client (editable local dep) |
| `langfuse` + `logfire`   | Optional trace export                                |

Model is configured via environment variables:

| Env var            | Default                                                        |
| ------------------ | -------------------------------------------------------------- |
| `BEDROCK_MODEL_ID` | `us.anthropic.claude-3-7-sonnet-20250219-v1:0`                 |
| `BEDROCK_REGION`   | `us-west-2`                                                    |
| `AWS_REGION_NAME`  | Set at runtime to match `BEDROCK_REGION` (required by LiteLLM) |

---

## Testing

[test_simple.py](../../backend/tagger/test_simple.py) invokes `lambda_handler` directly with a single instrument (VTI) and prints the classification result. Run it with:

```bash
uv run test_simple.py
```

No mock flag is needed — the tagger always calls Bedrock directly; there is no mock mode.
