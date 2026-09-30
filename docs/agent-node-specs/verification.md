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
| `persona_explanation` | the module is empty; the overview was held back by its code checks (`problems`); a number in the overview is not on the page | "fix these problems and rewrite the overview"; "check these numbers against the page" |
| `ad_disclosure_check` | the module is empty or has no rows; an item is `판정 불가`; a `적합` has no quote; a quote is not in the text it claims (page for `original`, overview for `overview`) | re-quote, addressed to the side (`target: original` or `overview`) and the code |
| overview vs. page (fidelity) | a `변경` or `추가` row, or a `누락` of an item the overview does not carry at all | fails `persona_explanation`: "carry this code's content as the page states it" |

A `부적합` may cite nothing — a missing disclosure cannot be quoted. A `판정 불가` fidelity row, and
a `누락` on an item the overview still carries (detail a summary may drop), is added to the reasons
as `[정보]` and fails nothing.

## Retry (`graph/retry.py`, `graph/routes.py`)

- At most two rounds (`MAX_LOOPS = 2`).
- Only modules that failed **and** received a concrete `requested_change` are retried:
  `persona_explanation` re-enters at `generate_persona_explanation`, `ad_disclosure_check` at
  `judge_ad_disclosure`. When both failed, the earlier node in graph order is the target and the
  rest follows by edges.
- `display_check` is never retried: `judge_display` takes no feedback, so it would repeat the same
  call on the same measurements. Its failures go to a person.
- The retried node reads `verification.feedback` for its own module only. The overview keeps the
  same reader; the disclosure check reuses the page-side rows and re-judges only the codes named.
- `retry_history` keeps one row per round (failed modules, retried modules, target), so the report
  can say how many rounds ran and why the run stopped (`escalation`: 재시도 한도 초과, 자동 재시도
  불가, 조치 가능한 피드백 없음).
