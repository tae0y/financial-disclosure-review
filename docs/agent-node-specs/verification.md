---
ai-generated: true
human-review: false
created: 2026-09-30
---

# verification and retry

`verify_answer` cross-checks the three judging modules against each other and against the page;
`retry_dispatch` and the routes decide whether another round can fix what failed. Neither makes a
model call. A pass means the answers are internally consistent and grounded in the page — not
that the page complies with the law, and the first reason line says so.

## What `verify` checks (`domain/verification/verify.py`)

| Module | Fails when | Request written for the next round |
|---|---|---|
| `display_check` | status is not `완료`; an item is `판정 불가`; a verdict cites no block or quote; a cited block was never measured; `적합` contradicts a measured threshold violation | re-cite real block ids, or re-judge the contradicted item (not retried, see below) |
| `persona_explanation` | the module is empty; the advice was held back by its code checks (`problems`); a number in the advice is not on the page | "fix these problems and rewrite the advice"; "drop the numbers and say only what to check" |
| `ad_disclosure_check` | the module is empty or has no rows; an item is `판정 불가`; a `적합` has no quote; a quote is not on the page | re-quote, addressed to the code (`target: original`) |

A `부적합` may cite nothing — a missing disclosure cannot be quoted.

## Retry (`graph/retry.py`, `graph/routes.py`)

- At most two rounds (`MAX_LOOPS = 2`).
- Only modules that failed **and** received a concrete `requested_change` are retried:
  `persona_explanation` re-enters at `generate_persona_explanation`, `ad_disclosure_check` at
  `judge_ad_disclosure`. The two are independent, so when both failed both run in one step
  (`retry_targets`) and verification follows.
- `display_check` is never retried: `judge_display` takes no feedback, so it would repeat the same
  call on the same measurements. Its failures go to a person.
- The retried node reads `verification.feedback` for its own module only. The advice keeps the
  same reader; the disclosure check keeps its rows and re-judges only the codes named.
- `retry_history` keeps one row per round (failed modules, retried modules, target), so the report
  can say how many rounds ran and why the run stopped (`escalation`: 재시도 한도 초과, 자동 재시도
  불가, 조치 가능한 피드백 없음).
