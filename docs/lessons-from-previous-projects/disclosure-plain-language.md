---
ai-generated: true
human-review: false
created: 2026-09-28
updated: 2026-09-28
---

# `financial-product-disclosure-and-plain-language`

**Period:** 2026-09-13 to 2026-09-26. **What it was:** an earlier implementation of the same
review task `financial_disclosure_review` now performs — a LangGraph pipeline judging a
card-company product page against explanation-duty and plain-language rules. Three rounds of work
in that project produced the insights this agent's graph design is built on.

## Round 1: closing the gap between requirements and what was actually wired

**What was done:** the running graph was compared against the project's own requirements
document. **Insight gained:** several guardrails were specified but not wired into the live call
path — no retry policy on LLM nodes, no closed judgment schema, and a failed call left no trace at
all, so a silent failure and a successful "nothing to report" looked identical afterward
(`docs/design-implementation-gap-20260914.md` in that project). **What changed:** a
`RetryPolicy(max_attempts=2, retry_on=retry_on_schema_error)` was added per LLM node, structured
output was made strict, and every call — successful or failed — was written to a per-call ledger
(`docs/gap-remediation-20260915.md`, commits `7fd3400` and `804aa94` in that project).

**Reflected here:** `financial_disclosure_review` records every call, successful or failed, in its
usage ledger (see [evaluation.md](../evaluation.md)), and every LLM node carries a retry policy
rather than assuming the first response is well-formed.

## Round 2: one call judging many items is one point of failure

**What was done:** a trial ran a smaller model (gpt-5-nano) judging all 34 explanation-duty items
for a page in a single call. **Insight gained:** the single call omitted and duplicated items on
two consecutive attempts, and because the whole page's judgment lived in that one call, exhausting
the schema retry budget lost every item's result — not just the ones that had gone wrong
(`docs/gpt-5-nano-trial-20260915.md` in that project). The same trial also showed that "the item
has no applicable condition, so it doesn't apply" is a rule a prompt alone cannot guarantee — the
model returned "not applicable" for an item with no `applies_condition` defined, honoring the
prompt's phrasing rather than a hard constraint.

**Reflected here:** `financial_disclosure_review` chunks judgment calls into small groups of
items rather than one call per page, so an omission or schema failure costs only the affected
chunk (see the verification design in [ADR-002](../architecture-decisions/adr-002-defect-injection-evaluation.md)).
The "not applicable" rule for an item without a defined condition is enforced in code, not only
requested in the prompt.

## Round 3: the verification design

**What was done:** the graph was rewritten as an explicit LangGraph skeleton, and the remaining
verification questions were worked through as a set of numbered decisions
(`notebooks/langgraph_skeleton_worklog.md` in that project, commit `4d62f64`). **Insight gained,**
recorded as decisions D3–D8:

| Decision | Insight |
|---|---|
| D3 | The judgment against the original page text only needs to run once; re-running it every retry round re-litigates a question retrying was not meant to reopen. |
| D4 | A retry should restart only the failed branch and the nodes after it — restarting the whole graph repeats work that already passed. |
| D5 | A retry should fire only for a judgment-quality problem (schema, citation, fidelity) — a legitimate FAIL is a result, not a defect to retry away. |
| D6 | Splitting LLM calls into small chunks, each checked for omitted, duplicated, or extra items, catches Round 2's failure mode directly. |
| D7 | Verification is more reliable when it uses a different-tier model from the judgment it checks, rather than the same model checking itself. |
| D8 | A contract as specific as "no condition means the item can't be marked not-applicable" belongs in code, where it cannot be talked around by phrasing. |

**Reflected here:** `src/financial_disclosure_review/graph/retry.py` implements D4 and D5 directly.
`should_retry` only fires when a failed module has "a concrete requested_change to act on," retries
are capped at two rounds, and `display_check` is deliberately excluded from the retryable set
because its judgment takes no feedback to act on — re-running it would repeat the same call over
the same measurement, which D5's reasoning rules out. Failures that are not retryable are escalated
to a reviewer with a stated reason (`escalation()` in the same file) rather than retried
indefinitely or silently accepted.
