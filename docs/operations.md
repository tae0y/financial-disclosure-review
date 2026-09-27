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

Measured, not assumed. One real page end to end on 2026-09-27: **$0.1456 (about 204원), 12 calls,
538 seconds**, including one retry round (run log
`eval/results/260927-175600-review-demo-run.log`; the report itself is
`data/reports/demo-260927.md`, whose cost section shows the *last* render of it, which was a free
re-render from the checkpoint). Six classification pages:
$0.035, 8 calls. Regenerating the report alone from its checkpoint: 0 calls, $0. The evaluation's
per-suite figures are in `docs/evaluation.md`.

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

## Operating constraints

- `SqliteSaver` serializes writes to one file. Fine for one reviewer at a time; a concurrent
  service needs a Postgres saver (`docs/design.md`).
- Playwright's sync API binds objects to their thread, so a whole review runs in one worker
  thread. Two reviews in one process would need separate threads and separate meters — the run
  meter in `core/usage.py` is process-wide by design, started once per run.
- The rubric DB has to be rebuilt (`build-db`) whenever a rubric yaml changes; the app reads the
  DB, not the yaml, so a stale DB silently judges by old criteria. `data/reference.sqlite` is the
  versioned artifact to watch.
- Model and prompts are pinned by the `--model` default (`gpt-5-mini`) and by the prompt text in
  each domain's `prompts.py`. Changing either invalidates the recorded evaluation cassette, which
  is exactly why the cassette key includes the model name and the task text.
