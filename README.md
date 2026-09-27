# Financial Disclosure Review

Reviews a Korean financial-product web page for the explanation duty and the display method,
converts its explanation into plain Korean, and writes one report for a compliance reviewer — as
one LangGraph app.

Every module is built: product page, classification, display method, plain language, explanation
duty, verification with a two-round retry loop, and the report.

## Install

```bash
cp .env.example .env   # then set OPENAI_API_KEY
uv sync --extra dev
uv run playwright install chromium
```

Pinned by design: Python 3.12 (`.python-version`), the dependency versions in `pyproject.toml` /
`uv.lock`, and the model in `core/context.py` (`gpt-5-mini`). The rubric the app judges by is the
DB built in the next step, not the yaml — rebuild it after any rubric change.

## Run

```bash
uv run python -m financial_disclosure_review build-db
uv run python -m financial_disclosure_review build-cases          # costs ~$0.0002
uv run python -m financial_disclosure_review review "https://<product page>"
uv run python -m financial_disclosure_review rerun --thread review-260927-101500 \
    --from-node judge_explanation_duty
```

`build-db` loads the rubric yaml and stays free and offline. `build-cases` embeds the case
corpus into the same DB, so it is a separate command and calls a paid model; `--dry-run` prints
what would be embedded and spends nothing. `docs/cases.md` has the corpus and the search.

`review` prints a summary, writes the report to `data/reports/<thread>.md`, and prints what the
run cost. `--model`, `--data-dir`, `--db-path` and `--checkpoints` override the defaults in
`core/context.py`. `--max-calls` (default 60) and `--max-usd` (default 1.0) cap a run: the cap is
checked before each call, and hitting it raises `BudgetError` rather than spending on.

## Evaluate

```bash
uv run python -m financial_disclosure_review evaluate                       # free: replays the cassette
uv run python -m financial_disclosure_review evaluate --suite plain-contract # free: no model at all
uv run python -m financial_disclosure_review evaluate --live --record --ablation
```

The default run replays recorded model answers from `eval/cassettes/`, so the numbers in
`docs/evaluation.md` can be re-derived without paying. `--live --record` calls the real model and
writes the answers down. Results land in `eval/results/` as both `.json` and `.md`.

## Serve

The same graph behind an HTTP API: a FastAPI gateway, the LangGraph worker in its own container,
and a Cloudflare tunnel in front.

```bash
cp .env.example .env   # set OPENAI_API_KEY, and FDR_API_TOKEN from the command below
uv run python -m financial_disclosure_review.serving.token
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml up --build
curl -s localhost:8000/readyz | python3 -m json.tool
open http://localhost:8000/docs
```

A review takes minutes, so submitting returns a job id to poll:

```bash
curl -sS -X POST localhost:8000/v1/reviews \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $FDR_API_TOKEN" \
  -d '{"url":"https://<product page>"}'
# {"job_id":"9f2c…","status":"queued","poll":"/v1/reviews/9f2c…"}

AUTH="Authorization: Bearer $FDR_API_TOKEN"
curl -sS -H "$AUTH" localhost:8000/v1/reviews/9f2c…
curl -sS -H "$AUTH" localhost:8000/v1/reviews/9f2c…/report.md
```

Every `/v1` route needs the issued token and the gateway refuses to start without one, so there is
no unauthenticated mode to forget about. `docs/api.md` has the full surface and
`docs/openapi.yaml` the generated spec.

## Test

```bash
uv run pytest                                # free checks only
uv run pytest -m "use_llm or use_network"    # paid model calls and live sites
uv run ruff check src tests && uv run pyright
```

`use_llm` costs money and `use_network` opens external sites, so both are excluded by default.
The browser test in `tests/domain/product_page/test_session.py` carries no marker: it renders a
local HTML fixture and reaches no network.

## Docs

- `docs/design.md` — principles, package layout, input, graph, State, rubrics, checkpoints, caps
- `docs/cases.md` — the sanction/dispute case corpus, sqlite-vec, and the `search_cases` node
- `docs/evaluation.md` — evaluation design, gold labels, measured results, failure analysis
- `docs/operations.md` — escalation, retry policy, cost caps, information protection, constraints
- `docs/product_page.md`, `docs/classification.md`, `docs/display_check.md`,
  `docs/plain_language.md`, `docs/explanation_duty_check.md`, `docs/report.md` — per-domain rules
- `docs/api.md` — the HTTP surface, the job model, `detail` levels, concurrency and cost
- `docs/team-usage-guide.md` — calling the deployed instance: base URL, auth, submit/poll example
- `docs/openapi.yaml` — the OpenAPI 3.1 document, generated from the app; regenerate with
  `uv run python -m financial_disclosure_review.serving.openapi`
- `docs/setup-docker.md`, `docs/setup-cloudflare.md` — the two containers and the tunnel
- `docs/agent-prompt-serving.md` — a task prompt for reproducing this serving pattern elsewhere
- `docs/src-layout-migration.md` — what moved out of the notebook, and what changed with it
- `localdocs/` — plans, worklog and ADRs (local only)
