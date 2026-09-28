# HTTP API

The review runs as two processes. The gateway takes the request; the worker holds the graph.

```
caller ──► Cloudflare tunnel ──► api:8000 ──► agent:8100 ──► LangGraph ──► OpenAI
                                    │                         │
                              data/jobs.sqlite        data/{reference,checkpoints}.sqlite
                                                      data/{snapshots,site_rules}/
```

Only `api` is on the tunnel's path. `agent` publishes no port outside the compose network.

## Why submission does not return the result

A review renders the page with a real browser and then makes a series of model calls. It takes
minutes. Cloudflare closes a response that has produced nothing for about 100 seconds, so a
synchronous endpoint would fail on exactly the runs that worked.

Submitting therefore returns `202` with a job id, and the caller polls. The job row lives in
SQLite rather than memory, so a gateway restart does not lose the record of what was asked.

## Authentication

One fixed token, issued once and sent as a bearer credential:

```
Authorization: Bearer fdr_<token>
```

Every `/v1/*` route requires it. `/healthz` and `/readyz` are always open, so a container probe
needs no credential.

**There is no unauthenticated mode.** The gateway reads the token from `FDR_API_TOKEN` and
refuses to start without it, exiting with code 3 rather than serving openly — a forgotten variable
cannot publish a credit-spending API by accident.

Issue a token with:

```bash
uv run python -m financial_disclosure_review.serving.token
# fdr_<generated-token>
```

The `fdr_` prefix lets secret scanners recognise a leaked token and lets you trace it back here.

`FDR_API_TOKEN` accepts a comma-separated list, which exists for one purpose: during a rotation
both the old and the new token are live, so callers can move over before the old one is withdrawn.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/healthz` | Gateway liveness. No dependency check. |
| `GET` | `/readyz` | Gateway plus worker: reference DB, writable data dir, model key. |
| `POST` | `/v1/reviews` | Queue a review of one URL. `202`. |
| `POST` | `/v1/reruns` | Queue a re-run of a recorded thread from one node. `202`. |
| `GET` | `/v1/reviews` | Recent jobs, newest first. `limit`, `status`. |
| `GET` | `/v1/reviews/{job_id}` | One job; `result` appears once it has succeeded. |
| `GET` | `/v1/reviews/{job_id}/report.md` | The reviewer-facing report as Markdown. |
| `GET` | `/docs` | Interactive OpenAPI. |

The machine-readable document is committed at [openapi.yaml](openapi.yaml) — OpenAPI 3.1, generated
from the app, so a client can be generated without standing the service up. Regenerate it with
`uv run python -m financial_disclosure_review.serving.openapi`; a test fails if it drifts.

### POST /v1/reviews

```json
{
  "url": "https://www.example-card.co.kr/product/credit/apply",
  "model": "gpt-5-mini",
  "thread_id": null,
  "detail": "summary",
  "max_calls": 60,
  "max_usd": 1.0
}
```

Only `url` is required. `thread_id` names the checkpoint thread — omit it and a timestamped one
with a random tail is generated, which is what makes two submissions in the same millisecond safe.
`detail` chooses how much of the finished State comes back (see below). `max_calls` and `max_usd`
cap one run; it raises `BudgetExceeded` rather than spending past them.

```json
{ "job_id": "9f2c…", "status": "queued", "poll": "/v1/reviews/9f2c…" }
```

### GET /v1/reviews/{job_id}

`status` moves through `queued` → `running` → one of `succeeded`, `failed`, `interrupted`.

- `failed` — the worker raised. `error` holds the type and message.
- `interrupted` — the gateway restarted or shut down mid-run. Submit it again; the checkpoints
  from the partial run are still on disk, so `/v1/reruns` can resume instead.

`result` is filled only on `succeeded`:

| Field | Holds |
|---|---|
| `thread_id` | The checkpoint thread, for a later re-run |
| `status` | `report.status` — `검토 완료`, `사람 검토 필요`, `검토 대상 아님`, `판정 불가` |
| `decision` | Whether the plain-language version may be published |
| `summary` | Per-module counts and verdicts |
| `report` | The full report, including `markdown` |
| `cost` | Token counts, USD and KRW, and the caps that applied |
| `elapsed_seconds` | Wall clock for the run |

### `detail`: what comes back

The graph's State holds the rendered page, which runs to hundreds of kilobytes. It is never in a
response. It stays on disk under `data/` and in the thread's checkpoints.

- `summary` (default) — counts, verdicts and page sizes. What a poller needs.
- `full` — adds the per-item judgment rows and the plain-language HTML, which is the artifact a
  reviewer edits. Still no source page HTML and no snapshot list.

## Calling it

```bash
BASE=http://localhost:8000          # or https://your-hostname
TOKEN=fdr_...                       # the issued token

job=$(curl -sS -X POST "$BASE/v1/reviews" \
        -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" \
        -d '{"url":"https://www.example-card.co.kr/product/credit/apply"}' \
      | python3 -c 'import json,sys; print(json.load(sys.stdin)["job_id"])')

# Poll until it leaves queued/running.
while :; do
  status=$(curl -sS -H "Authorization: Bearer $TOKEN" "$BASE/v1/reviews/$job" \
           | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])')
  echo "$status"
  case "$status" in succeeded|failed|interrupted) break ;; esac
  sleep 10
done

curl -sS -H "Authorization: Bearer $TOKEN" "$BASE/v1/reviews/$job/report.md"
```

## Concurrency and cost

One run at a time, by default. `core/usage.py` keeps the run meter in a module-level global, so two
runs in one worker process would share a single budget and trip each other's cap. The gateway holds
a matching semaphore, which means extra submissions wait as `queued` rather than piling up inside
an HTTP call.

To run more in parallel, add worker replicas rather than raising `FDR_AGENT_CONCURRENCY` — separate
processes get separate meters.

Every finished job reports what it spent. `cost.caps` records the caps that were in force, so a run
that stopped early can be told apart from one that finished cheaply.


