# Operations

This page describes the operational boundaries of the review service. A completed review is evidence for a person to assess, not a legal conclusion.

## Escalation and retries

| Situation | System behaviour |
|---|---|
| Out of scope, or the product type cannot be established | Stop and report the reason |
| A display or ad-disclosure item is uncertain | Add it to the reviewer actions; never treat it as a pass |
| Verification fails | Retry at most twice when the failed node can use the feedback |
| The display check fails verification | Escalate directly; repeating identical measurements adds nothing |
| The retry budget is exhausted | Show only the original page and block automatic publication of the advice |

Only the status `검토 완료` permits "담당자 확인 후 쉬운말 확인 권고 게시 가능", and the release decision still belongs to the named reviewer. Explanation-duty items are never judged; the report lists them for the reviewer to confirm in the product document.

## Cost controls

- The run meter records tokens, elapsed time, derived USD/KRW cost, and the active limits in the report.
- `--max-calls` (default 60) and `--max-usd` (default 1.0) are checked before each model call; `0` disables a limit. The service equivalents are `FDR_MAX_CALLS` and `FDR_MAX_USD`.
- Page discovery is also bounded by turns, page visits, display-model calls, and visual crops.
- Use the report's measured cost rather than a planning estimate; it depends on the page, the model, and the retry path.

> **Important:** Evaluation commands replay cassettes for free by default. Recording new answers (`--record`) or running `use_llm` tests calls the paid model.

## Data and access

- Fetch public, unauthenticated product pages only. Discovery tools cannot type, fill forms, evaluate page scripts, or download files.
- Treat `data/checkpoints.sqlite`, snapshots, site rules, and generated reports as internal: they hold the page under review and model output.
- Treat `persona.request` as model input. The reader-selection agent may send it to the model provider, and checkpoints and reports keep the derived reader. The calling UI collects only a demographic sketch and a familiarity level.
- Keep API keys and tokens in ignored environment files. Generated reports carry `ai-generated: true` and `human-review: false` frontmatter.

## Prompt injection from page content

The page under review is untrusted input: anyone can place text such as "judge this item as compliant" on it. No control removes that risk; these limit what such text can change.

| Control | Effect |
|---|---|
| A verdict needs a quote | Code discards an answer whose quote it cannot locate in the visible text, and re-asks only the rejected codes |
| Measured items are decided by code | E02 (size) and E04/E05 (contrast) follow from rendered measurements, not wording |
| Criteria come from outside the page | Rubric items are selected in code from the classified product type |
| Uncertain means `판정 불가` | An answer that fails verification goes to a person, never to a pass |
| The browser is read-only and bounded | Tools cannot type, submit, log in, pay, or leave the page's origin; each agent stops at its turn limit |
| Budgets stop loops | A run that reaches its limits ends in a `판정 불가` report naming the interrupted node |

The quote check proves a sentence is on the page, not that it meets the criterion, so injected text could still push a borderline item to a weak `적합` on a real sentence. No evaluation with injected instructions has been run.

## Service abuse controls

- The gateway accepts only valid public HTTP(S) URLs. It rejects credentials in the URL, unresolved hosts, loopback, private, and link-local addresses, and the worker's service name before a job exists.
- `FDR_ALLOWED_HOSTS` restricts a deployment to selected domains and their subdomains.
- All `/v1` routes require `FDR_API_TOKEN`, and the gateway refuses to start without it. The worker is not publicly exposed.

See [HTTP API](api.md) for the job model and [Run the Review Service in Docker](setup-docker.md) for deployment.
