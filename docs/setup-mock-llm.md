# Run an end-to-end check without model cost

`docker/docker-compose.mock.yml` runs the real gateway and worker images with every model call
answered by a local mock of the OpenAI API. A review goes through the HTTP API, the job store,
the browser and every graph node, and nothing is billed.

Use it to check plumbing: that a request field reaches the node that reads it, that the graph
runs to the report, that the API contract holds. It does not measure judgment quality — the mock
is not a model.

## What the mock answers

`financial_disclosure_review.llm.mock_server` answers the two shapes `llm/client.py` sends,
Responses structured output and Chat Completions tool calls:

| Call | Answer |
|---|---|
| Structured output (`/v1/responses` with a JSON schema) | The smallest schema-valid instance. Quote fields are copied from the page text, `items` carry the codes the caller asked about, and a verdict enum answers `판정 불가`. |
| Classification (`ClassifyAnswer`) | A single `신용카드` product, so every later node runs. |
| Persona selection tool loop (`choose`) | Filters read from the free-text reader by rules: age decade (`70대`), `사회초년생`, a province name, and `처음`/`금융권` for the familiarity hint. |
| Page agent tool loop | No tool call. The page agent is not mocked. |
| Image call | `{}`. |

Every call is appended to `data/mock/mock-calls.jsonl`.

## Prerequisites

- `data/personas/` — the persona dataset (`uv run python -m financial_disclosure_review
  fetch-personas`). Without it the reader falls back to the checked-in profiles.
- A stored site rule in `data/site_rules/` for the URL under review. Because the page agent is not
  mocked, a URL without a rule fails at collection. The default URL of the smoke script has one
  once a real review of it has run.

Both folders are mounted read-only. Everything the stack writes — jobs, checkpoints, snapshots,
the reference DB, the call log — goes to `data/mock/`, which is gitignored.

## Run

```bash
docker compose -f docker/docker-compose.mock.yml up -d --build
sh docker/mock-e2e.sh
```

The smoke script submits a review with a free-text reader, polls it, and exits non-zero unless the
job succeeds and the reader was chosen from that text:

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

Pass another reader or URL as arguments: `sh docker/mock-e2e.sh "서울에 사는 20대 사회초년생" <url>`.
The gateway listens on `localhost:18000` with the token `fdr_mock_local_test`; set
`FDR_MOCK_API_TOKEN` before `up` to change it.

Stop:

```bash
docker compose -f docker/docker-compose.mock.yml down
```

## Isolation

The stack has its own Compose project name, network, port and data folder, so it runs next to the
production stack without touching it. It does not read `.env`: the worker's key is a fixed fake
value and its `OPENAI_BASE_URL` points at the mock, so no call can reach the real API.

The meter still counts calls and tokens (one each per mock call), so budget caps behave as in a
real run; the reported dollar figure is not a charge.

## In tests

`tests/llm/test_mock_server.py` starts the same server in-process and drives the real `ask` and
`ToolChat` against it. A test that uses its `mock_api` fixture is exempt from the
guards in `tests/conftest.py` that stop free tests from reaching a paid model.
