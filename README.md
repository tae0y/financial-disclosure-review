# Financial Disclosure Review

Korean financial-product pages are reviewed for disclosure, display, and plain-language issues.
The LangGraph workflow produces a reviewer report; it does not provide a legal opinion or publish
content automatically.

## Quick start

```bash
cp .env.example .env                 # set OPENAI_API_KEY
uv sync --extra dev
uv run playwright install chromium
uv run python -m financial_disclosure_review build-db
uv run python -m financial_disclosure_review review "https://<product-page>"
```

The command writes `data/reports/<thread>.md`. Start with [the architecture guide](docs/design.md)
for the workflow and its limits.

## Commands

| Goal | Command | Notes |
|---|---|---|
| Build the rubric DB | `uv run python -m financial_disclosure_review build-db` | Offline and free. Run after changing a rubric. |
| Build the case-search DB | `uv run python -m financial_disclosure_review build-cases` | Calls an embedding model; use `--dry-run` to inspect first. |
| Review a page | `uv run python -m financial_disclosure_review review "<url>"` | Model calls may incur cost. |
| Resume a review | `uv run python -m financial_disclosure_review rerun --thread <id> --from-node <node>` | Uses the saved checkpoint. |
| Evaluate | `uv run python -m financial_disclosure_review evaluate --ablation` | Replays the recorded cassette by default. |

`review` accepts `--model`, `--data-dir`, `--db-path`, `--checkpoints`, `--max-calls`, and
`--max-usd`. The last two are checked before each model call; exceeding either raises
`BudgetError`.

## Test

```bash
uv run pytest
uv run ruff check src tests
uv run pyright
```

Tests marked `use_llm` or `use_network` are excluded by default because they can spend money or
visit external sites. Run them explicitly only when intended.

## Serve the API

```bash
cp .env.example .env                 # set OPENAI_API_KEY and FDR_API_TOKEN
uv run python -m financial_disclosure_review.serving.token
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml up --build
```

Submit with `POST /v1/reviews`, then poll the returned job URL. All `/v1` routes require a bearer
token. Local setup, deployment, and the complete endpoint contract are in [the serving docs](docs/api.md).

## Documentation

Start at [docs/README.md](docs/README.md). It separates how to run the system, how it makes a
judgment, and the evidence behind its evaluations.

## License and source material

Project code and documentation are MIT-licensed; see `LICENSE`. Regulatory sources, product
pages, names, and marks remain subject to their own terms; see `THIRD_PARTY_NOTICES.md`.
