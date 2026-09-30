---
ai-generated: true
human-review: false
created: 2026-09-28
updated: 2026-09-30
---

# Lessons from `financial-product-disclosure-and-plain-language`

This page describes what an earlier implementation of the same review task taught, and where each lesson shows in this project.

The earlier project (2026-09-13 to 2026-09-26) was a LangGraph pipeline that judged a card-company product page against explanation-duty and plain-language rules. Three rounds of work produced the lessons below.

## What went wrong there

- **Specified guardrails were not wired in.** The running graph had no retry on model nodes and no closed judgment schema, and a failed call left no trace, so a silent failure looked like "nothing to report".
- **One call for every item was one point of failure.** A small model judging all 34 explanation-duty items at once omitted and duplicated items twice in a row, and exhausting the retry lost every item's result.
- **A prompt could not enforce a rule.** The model marked an item "not applicable" although the item had no applicability condition, following the prompt's wording rather than a hard constraint.

## Where the lessons show here

| Lesson | Where it shows in this project |
|---|---|
| Meter and bound every model call | Every call goes through the run meter (`core/usage.py`), which checks the call and cost caps before each call and reports usage per step |
| Check the answer's item set in code | `call_ask` (`llm/client.py`) checks each answer; the ad-disclosure check rejects an answer whose codes differ from the requested set, and a code the model still omits becomes `판정 불가` |
| Retry only what failed | A rejected answer is asked again once for the rejected codes only; a second failure downgrades those codes to `판정 불가` instead of losing the whole call |
| Put contracts in code, not in the prompt | `domain/ad_disclosure_check/check.py` rejects any condition status other than `해당없음` for an item without `applies_condition` |
| Judge the original once; retry only the failed branch | A retry re-enters only the failed node (`retry_targets` in `graph/retry.py`) and never re-collects, re-classifies, or re-measures the page |
| A legitimate FAIL is a result, not a defect | `should_retry` fires only when a failed module has a concrete requested change, and stops at `MAX_LOOPS = 2` |
| Do not retry what cannot change | `display_check` is not retryable: its judgment takes no feedback, so a rerun repeats the same measurements. Non-retryable failures go to a reviewer through `escalation()` |

One earlier decision was not adopted: verifying a judgment with a model of a different tier. Classification's second call on a "no" answer uses the same model.

See [verification and retry](../agent-node-specs/verification.md) for the current design.
