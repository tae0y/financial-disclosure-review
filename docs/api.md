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
`persona` chooses the reader of the reader-tailored explanation (독자 맞춤 설명) from the
synthetic Nemotron-Personas-Korea dataset. The usual input is `{"request": "70대 은퇴자, 카드론을
처음 알아보는 사람"}`: one or two sentences of free text (up to 300 characters) that a small
bounded agent turns into dataset filters and a financial-familiarity hint. Two exact forms also
exist: `{"uuid": "<32 hex>"}` for one dataset row, and `{"attributes": {"age_min": 70,
"education_level": ["초등학교"]}}` for the filters themselves. The first one given wins; nothing
given uses the product type's default reader.

Every persona field is nullable, and so is `persona` itself. `null`, an omitted key, an empty
string and an `attributes` object whose values are all `null` all mean "not given", so a form can
send `{"request": "...", "uuid": null, "attributes": null}`. Only an over-long `request` or a
`uuid` that is not 32 hex characters is rejected with `422`; any other invalid value never fails
the run — the report states how the reader was chosen and what was used instead. The persona only
shapes the explanation's wording; it never changes a compliance verdict.

```bash
BASE=http://localhost:8000
TOKEN=fdr_...

job=$(curl -sS -X POST "$BASE/v1/reviews" \
  -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" \
  -d '{"url":"https://www.example-card.co.kr/product/credit/apply"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["job_id"])')

curl -sS -H "Authorization: Bearer $TOKEN" "$BASE/v1/reviews/$job"
curl -sS -H "Authorization: Bearer $TOKEN" "$BASE/v1/reviews/$job/report.md"
```

Poll until the status leaves `queued` or `running`. A job ends as `succeeded`, `failed`, or
`interrupted`. `interrupted` means the gateway stopped mid-run; its checkpoint remains available
for `/v1/reruns`.

## Responses and limits

Successful results contain the checkpoint `thread_id`, reviewer status and decision, summary,
report, cost, and elapsed time. `detail=full` additionally includes per-item judgments, evidence cards,
reference-case links, the page agent's trace, and the reader-tailored explanation HTML with its
units, fact ledger and reader selection. Raw source HTML and snapshots never leave the API.

The current worker processes one run at a time because its usage meter is process-global. Extra
submissions remain queued. Scale through worker replicas, not a higher in-process concurrency
setting. See [operations](operations.md) for budgets and service safeguards.
