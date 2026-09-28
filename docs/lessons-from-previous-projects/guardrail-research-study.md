---
ai-generated: true
human-review: false
created: 2026-09-28
updated: 2026-09-28
---

# Guardrail research study

**Period:** 2026-08 to 2026-09. **What it was:** a multi-month research study into LLM guardrail
evaluation methodology — reproducing and extending QGuard (ACL 2025 WOAH) — carried out as
academic work, independent of any implementation of this review task. No file in
`financial_disclosure_review` cites this study directly and its terminology does not appear in
the source tree; what carries over is the evaluation methodology itself, applied here to a
different problem.

The study went well beyond a single experiment: reproducing the baseline guard, diagnosing where
it failed, designing a targeted fix and a control to prove the fix was not a coincidence, running
a follow-up experiment on a different axis of guardrail behavior, and then a full pre-submission
rigor pass that re-checked every claim against what the underlying data actually supported. Four
of the methodological habits formed during that work are now load-bearing parts of this agent's
evaluation design.

## Methodologies reflected in this agent's architecture

### 1. Ground truth by construction, not by subjective label

**In the study:** QGuard's own reported recall numbers rest on a labeled dataset. Reproducing it
required understanding what made a label trustworthy in the first place — recall is only as good
as knowing, independent of the guard being tested, which prompts truly needed a block.

**In this agent:** [ADR-002](../architecture-decisions/adr-002-defect-injection-evaluation.md)
applies the same standard to the explanation-duty check: rather than asking a person to label 39
items per page (39 legal judgments, and author-dependent even then), the label is constructed by
deleting a disclosure that was confirmed present on the rendered page. The check either catches
the now-missing disclosure or it does not — the ground truth needs no human judgment call, only
proof the deletion landed.

### 2. A minimal, targeted intervention validated against a control

**In the study:** diagnosing QGuard's recall drop on finance-related prompts led to one targeted
addition to its question set. That fix was checked against a content-matched control — not just a
count-matched one — to confirm the recall gain came from the targeted change and not from adding
more questions generally. The fix recovered the gap with no side effects on other categories.

**In this agent:** the same shape appears twice. ADR-002's control deletion removes a sentence no
arm's judgment cited, to confirm nothing flips without cause. [ADR-005](../architecture-decisions/adr-005-display-flip-evaluation.md)'s
`rules` arm and ablation comparisons isolate what the model-based check adds over a
threshold-only baseline, the same way the content-matched control isolated what the targeted
guard question added over a generic one.

### 3. Verbatim grounding over the model's own summary

**In the study:** a follow-up experiment found that a guardrail's response probability shifts with
the surface form of a request — an imperative instruction versus an advisory framing — even when
the underlying content asked about is identical. A judgment that trusts how a request is phrased,
rather than what it actually asks, is exploitable by phrasing alone.

**In this agent:** every judgment in `financial_disclosure_review` is required to quote the exact
page text it is judging, and that quote is checked against the rendered page rather than trusted
from the model's own paraphrase (see the quote-match checks referenced throughout
[evaluation.md](../evaluation.md)). This is a direct application of the study's finding: a
judgment grounded in the model's own account of the input inherits that account's blind spots,
just as a guardrail's decision grounded in surface phrasing inherits phrasing-based blind spots.

### 4. Independent per-item checks over one aggregate judgment

**In the study:** guardrail failures were most visible at the level of individual probes, not in
an aggregate pass/fail score — a single-probe sensitivity could be invisible in a rolled-up
recall number.

**In this agent:** explanation-duty and display judgments are chunked and checked item by item
rather than resolved as one aggregate call per page (see the chunking rationale in
`financial-product-disclosure-and-plain-language.md`'s Round 2 and 3). A single item's failure is
caught and retried on its own, not averaged away inside a page-level score.

## What did not carry over directly

The study's pre-submission rigor pass — reversing a probability-scale finding by re-checking it on
the logit scale, and validating a small-sample threshold against a second, literature-backed
criterion before trusting it — is a habit of distrust toward any number until it is independently
checked. `financial_disclosure_review`'s display-flip check uses fixed rendered-measurement
thresholds rather than a statistically fit one, so that specific technique was not reused as-is;
what carried over is the underlying stance — a measurement is not trusted until it has been
checked against a second, independent basis — which is why [evaluation.md](../evaluation.md)
insists every reported number be re-derivable from a replay rather than asserted.
