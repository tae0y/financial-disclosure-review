---
ai-generated: true
human-review: false
created: 2026-09-27
---

# Operations

What this app does with uncertainty, money, and data — the parts a compliance team has to accept
before it runs on a real product page.

## Uncertainty always ends at a person

The app never converts "could not decide" into "fine". Three places produce that answer and all
three route to a human through the report:

| Where | Answer | What the report does |
|---|---|---|
| `classify_type` | `범위 밖` / `판정 불가` | ends the run, prints the step and the grounds, asks a person to confirm the product type |
| `judge_display_method`, `judge_explanation_duty` | `판정 불가` per item | lists the item under 확인이 필요한 항목 and adds a 사람 확인 action |
| `verify_answer` | `passed: False` after the retries | status becomes 사람 검토 필요 and the plain-language output is blocked from publication |

`report.status` has four values: `검토 완료`, `사람 검토 필요`, `검토 대상 아님`, `판정 불가`.
Only `검토 완료` carries `담당자 확인 후 쉬운말 게시 가능`, and even that one still names the
person as the decider. A pass is never a legal opinion: `docs/design.md` scopes the
explanation-duty items as 준용 quality criteria on an ad page, and the report repeats that in its
한계와 가정 section every time.

## The retry loop, and what it refuses to retry

The plan left one decision open — what happens when the verification loop runs out. It is now
settled in `graph/retry.py`:

- At most `MAX_LOOPS = 2` verification rounds.
- A module is retried only when `verify_answer` produced a `requested_change` it can act on.
- `display_check` is never retried. `judge_display` takes no feedback, so a second call would
  repeat the first on the same measurements; its failures are escalated instead.
- When the loop is exhausted, the original wording stays and the plain-language output is not
  published. Nothing is discarded automatically and nothing is published automatically.

`retry_history` in State records each round's failed modules and target, so a reviewer can see how
many rounds were spent and on what.

## Cost and the caps that stop a runaway

`core/usage.py` meters every model call: tokens per call and per step, the derived cost, the
elapsed time, and the caps in force. The report prints all of it, so "이 검토에 얼마 들었나"
is answered per run rather than estimated once in a plan.

- Tokens are facts read from the API response. Money is derived from `PRICES`, an assumption
  dated 2026-09-27 with an assumed 1,400 KRW/USD; both the token counts and the rate are printed
  so a reader can re-derive the figure at a different rate.
- Two caps, checked **before** each call, not after: `--max-calls` (default 60) and `--max-usd`
  (default 1.0). Hitting either raises `BudgetError` naming the step it stopped at. `0` disables
  a cap.
- `display_max_model_calls` (default 5) additionally bounds the display node, and
  `display_max_visual_crops` bounds how many rendered crops a vision call may carry.
- `max_turns` (20) and `max_visits` (3) bound the page-discovery agent.

Measured, not assumed. Three reviews run end to end on 2026-09-28 cost **$0.148–$0.193 (median
$0.184, about 258원), 20–24 calls, 513–723 seconds** each, including two verification rounds and,
on a site seen for the first time, 6–10 page-discovery calls
(`eval/results/260928-191135-cost-ledger.md`, copied out of the checkpoint DB by
`eval/cost_ledger.py`). The representative one is `data/reports/demo-260928.md` (22 calls,
$0.1844, 723 s) with its terminal transcript in `eval/results/260928-demo-review-run.txt`; its
report can be rebuilt for free with `eval/demo_report.py`. At 20 reviews a month that is about
$3.7 (5,200원). Regenerating the report alone from a checkpoint costs 0 calls and now carries the
review's recorded cost forward (`docs/report.md` §Cost). Six classification pages: $0.035, 8
calls. The evaluation's per-suite figures are in `docs/evaluation.md`.

## Information protection

- Only public product pages are fetched. No customer data, no authenticated session, no form
  filling — the discovery tools have no `fill`, `type`, `evaluate` or download tool at all
  (`docs/product_page.md`).
- The API key lives in `.env`, which is git-ignored; `.env.example` carries the key names only.
- Checkpoints (`data/checkpoints.sqlite`) hold the whole State, which means page HTML and
  judgments. That is public page content plus model output, so the file needs no personal-data
  handling — but it does hold the product wording under review, so treat it as internal.
- Reports are written to `data/reports/<thread>.md` with `ai-generated: true` and
  `human-review: false` in their frontmatter, so a generated document cannot be mistaken for a
  reviewed one.
- The evaluation cassettes hold model answers about public pages only.

## Misuse of the service itself

A review opens whatever URL it is given in a real browser, so the service has to refuse being
used to reach what only the server can reach.

- `core/urls.py:url_problem` refuses a scheme other than http(s), credentials inside the URL, a
  host that does not resolve, and any host that resolves to a non-public address — loopback,
  private and shared ranges, link-local (169.254.169.254, where cloud metadata answers), and the
  compose service name of the worker. The gateway answers 422 before a job exists
  (`tests/serving/test_api.py`), and `fetch_product_page` refuses again before a browser starts,
  so the CLI and a worker reached some other way are covered too (`tests/core/test_urls.py`,
  `tests/domain/product_page/test_fetch_failures.py`).
- `FDR_ALLOWED_HOSTS` narrows accepted hosts to given domains and their subdomains — for a
  deployment that serves one card company, its own domains.
- Every `/v1` route needs the issued bearer token and the gateway refuses to start without one
  (fail closed). Tokens are compared in constant time.
- The discovery agent has no typing, form-filling, script-evaluation or download tool; a click
  that would leave the page's host is refused and reported back to it; turns (20) and page visits
  (3) are capped.
- What is not covered: the check resolves the name when the job is submitted and again before the
  browser starts, but the browser resolves it once more itself, and a redirect from a public page
  to an internal address is not intercepted. A deployment that must rule these out adds an egress
  firewall on the worker container.

## Operating constraints

- `SqliteSaver` serializes writes to one file. Fine for one reviewer at a time; a concurrent
  service needs a Postgres saver (`docs/design.md`).
- Playwright's sync API binds objects to their thread, so a whole review runs in one worker
  thread. Two reviews in one process would need separate threads and separate meters — the run
  meter in `core/usage.py` is process-wide by design, started once per run.
- Rate limits and transient errors. Structured calls (`ask` in `llm/client.py`) and the
  site-exploration tool calls (`ToolChat`) use the OpenAI SDK with `max_retries=3`, which backs
  off and retries on rate limits (429), timeouts and server errors; embeddings use
  `max_retries=2` with a 60-second timeout. The vision call (`ask_images`) does not retry
  (`max_retries=0`, 90-second timeout): when it fails, rate limit included, the image-text blocks
  stay in `unresolved_ids` and those items end as 판정 불가 instead of failing the review. The run
  meter counts a call once, when its answer arrives; `call_ask`'s second attempt after an invalid
  answer is a new call and counts against the caps. The worker runs one review at a time by
  default (`FDR_AGENT_CONCURRENCY=1`), so a deployment sends one review's calls at a time;
  raising it multiplies the request rate against the same OpenAI account limit.
- The rubric DB has to be rebuilt (`build-db`) whenever a rubric yaml changes; the app reads the
  DB, not the yaml, so a stale DB silently judges by old criteria. `data/reference.sqlite` is the
  versioned artifact to watch.
- Model and prompts are pinned by the `--model` default (`gpt-5-mini`) and by the prompt text in
  each domain's `prompts.py`. Changing either invalidates the recorded evaluation cassette, which
  is exactly why the cassette key includes the model name and the task text.
