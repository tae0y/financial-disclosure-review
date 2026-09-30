---
ai-generated: true
human-review: false
created: 2026-09-28
updated: 2026-09-30
---

# Lessons from the Guardrail Research Study

This page describes which evaluation habits from an earlier guardrail research study carry over to this project's evaluation design.

The study (2026-08 to 2026-09) reproduced and extended QGuard (ACL 2025 WOAH), an LLM guardrail, as academic work. It diagnosed where the baseline guard failed, tested a targeted fix against a content-matched control, and re-checked every claim against the underlying data before submission. No code or terminology from the study appears in this repository; what carries over is the evaluation method.

## Where the lessons show here

| Lesson from the study | Where it shows in this project |
|---|---|
| Recall is only as good as a label that is independent of the system under test | The disclosure check is measured by deleting a disclosure confirmed present on the page, so the label needs no human judgment ([ADR-002](../architecture-decisions/adr-002-defect-injection-evaluation.md)) |
| A fix must beat a matched control, not only a baseline | Each defect-injection run deletes an unrelated sentence as a control; the display evaluation runs a `rules` arm and shrinks or fades marketing copy as controls ([ADR-005](../architecture-decisions/adr-005-display-flip-evaluation.md)) |
| A judgment grounded in the model's own account of the input inherits that account's blind spots | Every verdict quotes the page, and code locates the quote in the visible text before accepting it ([architecture](../architecture.md#rules-every-node-follows)) |
| Failures show at the level of single items, not in an aggregate score | Answers are checked and re-asked per rubric code, and results report per-item verdicts and per-item stability ([evaluation](../evaluation.md)) |
| Distrust a number until a second, independent check confirms it | Every reported figure is re-derivable for free from a recorded cassette (`evaluate --ablation`) |

The study's statistical techniques (re-checking a finding on the logit scale, validating a small-sample threshold against a literature criterion) were not reused: the display check uses fixed rubric and WCAG thresholds rather than a fitted one.
