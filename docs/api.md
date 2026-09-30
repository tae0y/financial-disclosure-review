# HTTP API

The gateway accepts and tracks jobs; the worker runs the graph. Only the gateway is public.

```
caller → Cloudflare tunnel → api:8000 → agent:8100 → LangGraph
                              │              │
                        data/jobs.sqlite  data/checkpoints.sqlite
```

## Authentication

Every `/v1` route requires a bearer token. Health endpoints remain open for container probes.

```text
Authorization: Bearer fdr_<token>
```

Generate a token with `uv run python -m financial_disclosure_review.serving.token` and set it as
`FDR_API_TOKEN`. The gateway fails closed when the variable is absent. A comma-separated value
temporarily accepts both tokens during rotation.

## Endpoints

| Method | Path | Result |
|---|---|---|
| `GET` | `/healthz` | Gateway liveness; no authentication. |
| `GET` | `/readyz` | Gateway and worker readiness; no authentication. |
| `POST` | `/v1/reviews` | Queue a URL review; returns `202`. |
| `POST` | `/v1/reruns` | Resume a thread from a node; returns `202`. |
| `GET` | `/v1/reviews` | List recent jobs (`limit`, `status`). |
| `GET` | `/v1/reviews/{job_id}` | Get a job and, after success, its result. |
| `GET` | `/v1/reviews/{job_id}/report.md` | Download the reviewer report. |

The generated [OpenAPI document](openapi.yaml) is the complete request/response contract. Regenerate
it with `uv run python -m financial_disclosure_review.serving.openapi`.

## Submit and poll

Only `url` is required. `detail` defaults to `summary`; `max_calls` and `max_usd` cap one run.

### Reader information for the easy-language overview

`persona` carries the user information used to choose the reader of the plain-language overview
(쉬운말 개요, one or two paragraphs shown beside the page). It does not identify the API caller. A normal UI sends the text the
user entered in `persona.request`:

```json
{
  "url": "https://www.example-card.co.kr/product/credit/apply",
  "persona": {
    "request": "70대 은퇴자이고 카드론을 처음 알아보는 사람입니다.",
    "uuid": null,
    "attributes": null
  }
}
```

| Field | Type | Use |
|---|---|---|
| `persona` | object \| `null` | Optional user information. Omit it or send `null` when the UI collected none. |
| `persona.request` | string \| `null` | The usual input: one or two sentences, up to 300 characters. State who the user is and how familiar they are with the product. |
| `persona.uuid` | string \| `null` | Advanced use: one exact dataset row, as 32 lowercase hexadecimal characters. |
| `persona.attributes` | object \| `null` | Advanced use: dataset filters supplied directly. |

Free text is turned into dataset filters and a financial-familiarity hint by a small bounded
agent. Useful details are age band, education, occupation, region, household type, and phrases
such as "처음 알아보는" or "금융권 종사자". Income, credit standing, suitability, and other
facts that the dataset does not contain are not inferred or used. The selected persona only
changes the overview's wording; it never changes a compliance verdict.

Treat `persona.request` as model input. Collect only the demographic sketch and level of financial
familiarity needed for the overview; do not send a name, contact details, account or card
numbers, resident-registration numbers, credentials, or other identifying or sensitive data.

The advanced `attributes` form accepts the filters `age_min`, `age_max`, `sex`,
`education_level`, `occupation_contains`, `province`, `family_type`, `housing_type`, and
`marital_status`. When more than one form has a value, precedence is `uuid` → `attributes` →
`request`. For ordinary screen integration, populate only `request` and leave the other two
fields `null`.

Every persona field is nullable, and so is `persona` itself. For `request` and `uuid`, an omitted
key, `null`, or an empty string means "not given". For `attributes`, an omitted key, `null`, an
empty object, or an object whose values are all `null` has the same meaning. If every form is
empty, the run uses the product type's default reader. An unusable filter, unmatched value, or
free-text request from which no supported condition can be obtained does not fail the job: the
run falls back to a default reader and records the reason in the report.

Request-shape validation still happens before a job is created. A `request` longer than 300
characters, a non-string `request` or `uuid`, a non-object `persona` or `attributes`, or a nonempty
`uuid` other than 32 lowercase hexadecimal characters returns FastAPI's standard `422` response.
Invalid keys or values *inside* the free-form `attributes` object instead fall back during the
run. A `422` response's `detail[].loc` identifies the field, for example
`['body', 'persona', 'request']`.

```bash
BASE=http://localhost:8000
TOKEN=fdr_...

job=$(curl -sS -X POST "$BASE/v1/reviews" \
  -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" \
  -d '{
    "url":"https://www.example-card.co.kr/product/credit/apply",
    "persona":{
      "request":"70대 은퇴자이고 카드론을 처음 알아보는 사람입니다.",
      "uuid":null,
      "attributes":null
    }
  }' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["job_id"])')

curl -sS -H "Authorization: Bearer $TOKEN" "$BASE/v1/reviews/$job"
curl -sS -H "Authorization: Bearer $TOKEN" "$BASE/v1/reviews/$job/report.md"
```

Poll until the status leaves `queued` or `running`. A job ends as `succeeded`, `failed`, or
`interrupted`. `interrupted` means the gateway stopped mid-run; its checkpoint remains available
for `/v1/reruns`.

With `detail=summary`, `result.summary.persona_explanation.reader_chosen_by` is `agent` for a
free-text choice, `default` when nothing was supplied, `fallback` when the input could not be
used, or `uuid`/`attributes` for either advanced form. With `detail=full`,
`result.summary.persona_explanation.selection` also contains the applied filters, match count,
selection trace, and fallback reason.

## Responses and limits

Successful results contain the checkpoint `thread_id`, reviewer status and decision, summary,
report, cost, and elapsed time. `detail=full` additionally includes per-item judgments, evidence cards,
the page agent's trace, the overview HTML and paragraphs with the reader selection, and under
`ad_disclosure_check` the ad-disclosure rows for the page and the overview, their differences, and
the explanation-duty items left to the product document (`deferred`). Raw source HTML and snapshots never leave the API.

The worker runs up to `FDR_AGENT_CONCURRENCY` reviews at once (2 in the compose file); each run
meters its own budget. Extra submissions stay `queued` until a slot frees, and a run takes about
8–11 minutes, so a queued job can wait that long before `started_at` is set. Each run starts its
own Chromium, so raise the setting only with memory to spare. See [operations](operations.md) for
budgets and service safeguards.
