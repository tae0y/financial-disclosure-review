# Financial Disclosure Review

Korean card-company advertising pages are reviewed against the mandatory ad disclosures and the
display-method rules, with a short reader-tailored plain-language overview judged by the same
criteria as the page. Explanation-duty items are listed for the product document, not judged.
A fixed LangGraph workflow produces a reviewer report; it does not provide a legal opinion or
publish content automatically. Inside that workflow, two bounded tool-calling agents collect the
page and pick the reader; the review order, routing, retries and verdict rules stay in code.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python package and environment manager
- An OpenAI API key
- [.env.example](.env.example) copied to `.env`

## Getting started

1. Copy the environment file and set `OPENAI_API_KEY`.

    ```bash
    cp .env.example .env
    ```

1. Install dependencies and the Playwright browser.

    ```bash
    uv sync --extra dev
    uv run playwright install chromium
    ```

1. Build the rubric database.

    ```bash
    uv run python -m financial_disclosure_review build-db
    ```

1. Review a page.

    ```bash
    uv run python -m financial_disclosure_review review "https://<product-page>"
    ```

   The command writes `data/reports/<thread>.md`. See [the architecture overview](docs/README.md#architecture)
   for the workflow and its limits.

## Commands

| Goal | Command | Notes |
|---|---|---|
| Build the rubric DB | `uv run python -m financial_disclosure_review build-db` | Offline and free. Run after changing a rubric. |
| Download the reader dataset | `uv run python -m financial_disclosure_review fetch-personas` | nvidia/Nemotron-Personas-Korea at a pinned revision, about 2 GB, sha256-checked; the agent container runs it on first boot. |
| Review a page | `uv run python -m financial_disclosure_review review "<url>"` | Model calls may incur cost. |
| Resume a review | `uv run python -m financial_disclosure_review rerun --thread <id> --from-node <node>` | Uses the saved checkpoint. |
| Evaluate | `uv run python -m financial_disclosure_review evaluate --ablation` | Replays the recorded cassette by default. |

`review` accepts `--model`, `--data-dir`, `--db-path`, `--checkpoints`, `--max-calls`, and
`--max-usd`. The last two are checked before each model call; exceeding either raises
`BudgetError`.

Captured third-party pages and the model answers about them are not in this repository:
`tests/fixtures/classify/`, `eval/fixtures/`, `eval/cassettes/`, `eval/results/` and
`data/reference.sqlite` ship separately as `fdr-reproduction-assets-260929.zip`, unpacked at the
repository root. Without them the tests that need a captured page are skipped and `evaluate`
stops with `no evaluation cases`.

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
token. Optional user information for the easy-language overview is sent as free text in
`persona.request`. Its nullable fields, validation rules, examples, deployment, and the complete
endpoint contract are in [the serving docs](docs/api.md).

## Documentation

Start at [docs/README.md](docs/README.md). It separates how to run the system, how it makes a
judgment, and the evidence behind its evaluations.

## License and source material

Project code and documentation are MIT-licensed; see `LICENSE`. Regulatory sources, product
pages, names, and marks remain subject to their own terms; see `THIRD_PARTY_NOTICES.md`.
