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
report, cost, and elapsed time. `detail=full` additionally includes per-item judgments and the
plain-language HTML. Raw source HTML and snapshots never leave the API.

The current worker processes one run at a time because its usage meter is process-global. Extra
submissions remain queued. Scale through worker replicas, not a higher in-process concurrency
setting. See [operations](operations.md) for budgets and service safeguards.
