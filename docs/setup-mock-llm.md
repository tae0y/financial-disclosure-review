# Run an End-to-End Check without Model Cost

This page describes how to run a review through the real gateway and worker images with every model call answered by a local mock of the OpenAI API.

A review goes through the HTTP API, the job store, the browser, and every graph node, and nothing is billed. Use it to check plumbing: that a request field reaches the node that reads it, that the graph runs to the report, and that the API contract holds. It does not measure judgment quality.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine with the Compose plugin)
- A POSIX shell for `docker/mock-e2e.sh` (Git Bash on Windows)
- The persona dataset in `data/personas/` (`uv run python -m financial_disclosure_review fetch-personas`)
  - Without it the reader falls back to the checked-in profiles.
- A stored site rule in `data/site_rules/` for the URL under review
  - The page agent is not mocked, so a URL without a rule fails at collection. The smoke script's default URL has a rule once a real review of it has run.

## What the mock answers

`financial_disclosure_review.llm.mock_server` answers the two shapes `llm/client.py` sends: Responses structured output and Chat Completions tool calls.

| Call | Answer |
|---|---|
| Structured output (`/v1/responses` with a JSON schema) | The smallest schema-valid instance. Quotes are copied from the page text, `items` carry the requested codes, and verdicts are `판정 불가` |
| Classification (`ClassifyAnswer`) | A single `신용카드` product, so every later node runs |
| Persona selection tool loop (`choose`) | Filters read from the free text by rules: age decade (`70대`), `사회초년생`, a province name, and `처음`/`금융권` for the familiarity hint |
| Page agent tool loop | No tool call; the page agent is not mocked |
| Image call | `{}` |

Every call is appended to `data/mock/mock-calls.jsonl`.

## Run the check

1. Start the mock stack.

    ```bash
    docker compose -f docker/docker-compose.mock.yml up -d --build
    ```

1. Run the smoke script. It submits a review with a free-text reader, polls it, and exits non-zero unless the job succeeds and the reader was chosen from that text.

    ```bash
    sh docker/mock-e2e.sh
    ```

   To pass another reader or URL: `sh docker/mock-e2e.sh "서울에 사는 20대 사회초년생" <url>`.

1. Confirm the output shows `status succeeded` and `reader_chosen_by agent`.

    ```text
    job 5f0c…
    status succeeded
    reader_chosen_by agent
    profile nemotron:f469e0eb4bbe4efb9118e2b0b4c62169
    filters {"age_min": 70, "age_max": 79}
    match_count 96558
    familiarity_hint 낮음
    metered_usd 1.4e-05 (mock tokens; nothing was billed)
    ```

The gateway listens on `localhost:18000` with the token `fdr_mock_local_test`. Set `FDR_MOCK_API_TOKEN` before `up` to change it.

## Isolation

- The stack has its own Compose project name, network, port, and data folder, so it runs next to the production stack without touching it.
- It does not read `.env`. The worker's key is a fixed fake value and `OPENAI_BASE_URL` points at the mock, so no call can reach the real API.
- `data/personas/` and `data/site_rules/` are mounted read-only. Everything the stack writes goes to `data/mock/`, which is gitignored.
- The meter still counts calls and tokens, so budget caps behave as in a real run. The reported dollar figure is not a charge.

## Use in tests

`tests/llm/test_mock_server.py` starts the same server in-process and drives the real `ask` and `ToolChat` against it. A test that uses its `mock_api` fixture is exempt from the guards in `tests/conftest.py` that stop free tests from reaching a paid model.

## Remove

1. Stop the mock stack.

    ```bash
    docker compose -f docker/docker-compose.mock.yml down
    ```
