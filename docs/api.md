# HTTP API

This page describes how to submit a review over HTTP, poll it, and read the result.

The gateway (`api`) accepts and tracks jobs; the worker (`agent`) runs the graph. Only the gateway is public.

```text
caller → Cloudflare tunnel → api:8000 → agent:8100 → LangGraph
                              │              │
                        data/jobs.sqlite  data/checkpoints.sqlite
```

The generated [OpenAPI document](openapi.yaml) is the complete request and response contract. Regenerate it with `uv run python -m financial_disclosure_review.serving.openapi`.

## Authentication

Every `/v1` route requires a bearer token. The health endpoints stay open for container probes.

```text
Authorization: Bearer fdr_<token>
```

- Issue a token with `uv run python -m financial_disclosure_review.serving.token` and set it as `FDR_API_TOKEN`.
- The gateway refuses to start when `FDR_API_TOKEN` is unset.
- A comma-separated value accepts two tokens at once, for rotation.

## Endpoints

| Method | Path | Result |
|---|---|---|
| `GET` | `/healthz` | Gateway liveness; no authentication |
| `GET` | `/readyz` | Gateway and worker readiness; no authentication |
| `POST` | `/v1/reviews` | Queue a URL review; returns `202` |
| `POST` | `/v1/reruns` | Resume a thread from a node; returns `202` |
| `GET` | `/v1/reviews` | List recent jobs (`limit`, `status`) |
| `GET` | `/v1/reviews/{job_id}` | Get a job and, after success, its result |
| `GET` | `/v1/reviews/{job_id}/report.md` | Download the reviewer report |

## Submit and poll

Only `url` is required. `detail` defaults to `summary`; `max_calls` and `max_usd` cap one run.

1. Submit a review.

    ```bash
    # bash/zsh
    BASE=http://localhost:8000
    TOKEN=fdr_...

    job=$(curl -sS -X POST "$BASE/v1/reviews" \
      -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" \
      -d '{
        "url": "https://www.example-card.co.kr/product/credit/apply",
        "persona": {"request": "70대 은퇴자이고 카드론을 처음 알아보는 사람입니다.", "uuid": null, "attributes": null}
      }' \
      | python3 -c 'import json,sys; print(json.load(sys.stdin)["job_id"])')
    ```

    ```powershell
    # PowerShell
    $BASE = "http://localhost:8000"
    $TOKEN = "fdr_..."
    $headers = @{ Authorization = "Bearer $TOKEN" }

    $body = @{
        url     = "https://www.example-card.co.kr/product/credit/apply"
        persona = @{ request = "70대 은퇴자이고 카드론을 처음 알아보는 사람입니다."; uuid = $null; attributes = $null }
    } | ConvertTo-Json

    $job = (Invoke-RestMethod -Method Post -Uri "$BASE/v1/reviews" -Headers $headers `
        -ContentType "application/json; charset=utf-8" -Body $body).job_id
    ```

1. Poll the job until its status leaves `queued` or `running`.

    ```bash
    # bash/zsh
    curl -sS -H "Authorization: Bearer $TOKEN" "$BASE/v1/reviews/$job"
    ```

    ```powershell
    # PowerShell
    Invoke-RestMethod -Uri "$BASE/v1/reviews/$job" -Headers $headers
    ```

1. Download the report.

    ```bash
    # bash/zsh
    curl -sS -H "Authorization: Bearer $TOKEN" "$BASE/v1/reviews/$job/report.md"
    ```

    ```powershell
    # PowerShell
    Invoke-RestMethod -Uri "$BASE/v1/reviews/$job/report.md" -Headers $headers
    ```

A job ends as `succeeded`, `failed`, or `interrupted`. `interrupted` means the gateway stopped mid-run; the checkpoint remains, so `POST /v1/reruns` with its `thread_id` resumes the run.

## Reader information

`persona` is optional user information that picks the reader of the plain-language advice (쉬운말 확인 권고). It does not identify the API caller. A normal UI sends only `persona.request`.

| Field | Type | Use |
|---|---|---|
| `persona` | object \| `null` | Omit or send `null` when the UI collected nothing |
| `persona.request` | string \| `null` | The usual input: one or two sentences, up to 300 characters, about who the user is and how familiar they are with the product |
| `persona.uuid` | string \| `null` | Advanced: one exact dataset row, 32 lowercase hexadecimal characters |
| `persona.attributes` | object \| `null` | Advanced: dataset filters `age_min`, `age_max`, `sex`, `education_level`, `occupation_contains`, `province`, `family_type`, `housing_type`, `marital_status` |

Rules:

- Precedence is `uuid` → `attributes` → `request`.
- An omitted key, `null`, an empty string, or an empty or all-`null` `attributes` object means "not given". With nothing given, the run uses the product type's default reader.
- A small bounded agent turns free text into dataset filters and a financial-familiarity hint. Useful details are age band, education, occupation, region, household type, and phrases such as "처음 알아보는" or "금융권 종사자". Income, credit standing, and suitability are never inferred.
- An unusable filter, an unmatched value, or free text with no usable condition does not fail the job. The run falls back to a default reader and records the reason in the report.
- Request-shape errors return FastAPI's standard `422` before a job exists: `request` over 300 characters, a non-string `request` or `uuid`, a non-object `persona` or `attributes`, or a nonempty `uuid` that is not 32 lowercase hex characters. `detail[].loc` names the field, for example `['body', 'persona', 'request']`.
- The reader changes only the advice's wording and which items it recommends, never a compliance verdict.

> **Important:** `persona.request` is sent to the model provider. Collect only a demographic sketch and a familiarity level. Never send names, contact details, account or card numbers, resident-registration numbers, credentials, or other identifying data.

## Responses

A successful result contains the checkpoint `thread_id`, reviewer status and decision, summary, report, cost, and elapsed time. Raw source HTML and snapshots never leave the API.

| `detail` | Adds |
|---|---|
| `summary` (default) | `result.summary.persona_explanation.reader_chosen_by`: `agent` (free text), `default` (nothing supplied), `fallback` (input unusable), `uuid`, or `attributes` |
| `full` | Per-item judgments, evidence cards, the page agent's trace, the advice HTML, text and `advice_codes`, the reader `selection` (filters, match count, trace, fallback reason), and `ad_disclosure_check` rows with the `deferred` explanation-duty items |

## Limits

- The worker runs up to `FDR_AGENT_CONCURRENCY` reviews at once (2 in the compose file). Each run meters its own budget and starts its own Chromium, so raise the value only with memory to spare.
- A run takes about 8–11 minutes. Extra submissions stay `queued` until a slot frees, so `started_at` can be unset for that long.
- See [Operations](operations.md) for budgets and service safeguards.
