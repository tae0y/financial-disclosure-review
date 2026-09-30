---
ai-generated: true
human-review: false
created: 2026-09-30
updated: 2026-09-30
---

# Verification and Retry (`verify_answer`, `retry_dispatch`)

This page describes how `verify_answer` cross-checks the judging nodes and how `retry_dispatch` decides whether another round can fix what failed.

Neither node calls a model. A pass means the answers are consistent and grounded in the page, not that the page complies with the law; the first reason line of every result says so.

## What is checked

| Module | Fails when | Request for the next round |
|---|---|---|
| `display_check` | status is not `완료`; an item is `판정 불가`; a verdict cites no block or quote; a cited block was never measured; `적합` contradicts a measured violation | none; see below |
| `persona_explanation` | the module is empty; the advice was held back by its code checks; the advice contains a number not on the page | rewrite the advice fixing the listed problems, or drop the numbers |
| `ad_disclosure_check` | the module is empty or has no rows; an item is `판정 불가`; a `적합` has no quote; a quote is not on the page | re-quote, addressed to the item code |

A `부적합` may cite nothing: a missing disclosure cannot be quoted.

## Retry rules

- At most two rounds (`MAX_LOOPS = 2`).
- Only a module that failed and received a concrete requested change is retried. The advice re-enters at `generate_persona_explanation`, the disclosure check at `judge_ad_disclosure`. When both failed, both run in one step, then verification runs again.
- `display_check` is never retried: it takes no feedback, so it would repeat the same call on the same measurements. Its failures go to a person.
- A retried node reads only its own feedback. The advice keeps the same reader; the disclosure check re-judges only the named codes.
- Page collection, classification, card extraction and measurement are never repeated.

`retry_history` records one row per round. When the run stops without passing, `escalation` states why: 재시도 한도 초과, 자동 재시도 불가, or 조치 가능한 피드백 없음.

Tests: `tests/domain/verification/` and `tests/graph/`.
