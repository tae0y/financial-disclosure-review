# Operations

This page records the operational boundaries of the review service. A completed review is evidence
for a person to assess, not an automatic legal conclusion.

## Escalation and retries

| Situation | System behaviour |
|---|---|
| Out of scope or classification cannot be established | Stop and report the reason. |
| A display or explanation item is uncertain | Add it to the reviewer actions; never treat it as a pass. |
| Verification fails | Retry at most twice when the failed node can use the feedback. |
| Display check fails verification | Escalate directly; repeating identical measurements is not useful. |
| Retry budget is exhausted | Keep the original wording and block automatic publication. |

Only `검토 완료` permits “담당자 확인 후 독자 맞춤 설명 게시 가능.” That still leaves the release
decision to the named reviewer.

## Cost controls

The run meter records token use, elapsed time, derived USD/KRW cost, and the active limits in the
report. `--max-calls` (default 60) and `--max-usd` (default 1.0) are enforced before each model
call; `0` disables a limit. Page discovery is also bounded by turns, page visits, display-model
calls, and visual crops.

Costs depend on the page, model, and retry path. Use the report's measured cost rather than a
planning estimate. Evaluation commands replay cassettes by default; recording new answers or
running `use_llm` tests can incur cost.

## Data and access

- Fetch public, unauthenticated product pages only. Discovery tools cannot type, fill forms,
  evaluate page scripts, or download files.
- Treat `data/checkpoints.sqlite`, snapshots, site rules, and generated reports as internal:
  they contain the page content under review and model output.
- Keep API keys and tokens in ignored environment files. Generated reports retain
  `ai-generated: true` and `human-review: false` frontmatter.

## Service abuse controls

The gateway accepts only valid public HTTP(S) URLs. It rejects credentials in a URL, unresolved
hosts, loopback/private/link-local addresses, and the worker service name before a job exists.
`FDR_ALLOWED_HOSTS` can further restrict a deployment to selected domains and subdomains.

All `/v1` routes require `FDR_API_TOKEN`, and the gateway refuses to start without it. The worker
is not publicly exposed. See [API](api.md) for the job model and [Docker setup](setup-docker.md)
for deployment details.
