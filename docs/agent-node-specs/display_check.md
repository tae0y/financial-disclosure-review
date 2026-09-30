---
ai-generated: true
human-review: false
created: 2026-09-27
updated: 2026-09-30
---

# Display Method Check (`judge_display_method`)

This page describes how `judge_display_method` judges the E-group (표시방법) rubric items: whether mandatory disclosures are large enough, distinguishable from their background, separated, and not hidden behind a control.

## Input and output

| | Content |
|---|---|
| Reads | `product_page` (render snapshots), `classification`, `evidence_cards` |
| Writes | `display_check`: block table, per-item verdicts, stated assumptions |
| Model use | structured calls for labelling and verdicts, optional vision call on image crops |

## How it works

Code measures; the model labels and judges only what cannot be measured.

| Done by code | Done by the model |
|---|---|
| joining rendered rows to the page text, font size in pt, contrast ratio, visibility per state, line layout, per-group minima, threshold violations | which blocks are mandatory disclosures, and the verdict of every qualitative item (E01, E03, E06, E07, E08, ...) |
| the verdicts of E02 (size), E04 and E05 (contrast) | — |

For the code-decided items, a threshold violation is `부적합` citing exactly the violating blocks. A pass requires every labelled block to have been visible and measured.

The model never computes a number. Code rejects a model verdict that contradicts the measurements: `적합` while a threshold violation exists, or `부적합` that cites no violating block. After a second failing answer, only the named items are downgraded to `판정 불가`.

## When a block cannot be measured

Unmeasurable evidence never becomes a pass.

- **Image-backed text.** A block over a CSS background image or overlapping an `img` is `visual_risk`. Its flat-colour contrast is ignored and a saved crop goes to a vision call. A missing or uncertain crop leaves it unresolved, and E04/E05 become `판정 불가`.
- **Disclosure inside an image.** An image whose alt text names a mandatory disclosure topic blocks every pass except E07. The flag is kept only when the quoted alt phrase really occurs in the alt text and in the rubric criteria.
- **Undrawn text.** Text set below 1px (image replacement) gets no size. E02 cannot cite it for `부적합`, and while it stands an E02 `적합` becomes `판정 불가`.
- **Never-visible blocks.** A block never visible in any capture proves nothing. An E07 `부적합` must cite a block revealed by a user action.
- **Legacy capture.** A snapshot without rendered crops makes E04/E05 `판정 불가`; the page must be collected again.

## Assumptions not yet confirmed by a reviewer

Both are written into `judgments["assumptions"]` on every run.

- **Size (E02).** The rubric requires 8pt on A4 paper. A web page has no paper size, so the node uses computed CSS px × 0.75 ≥ 8pt at the captured viewport. The threshold is read from the rubric at run time.
- **Contrast (E04/E05).** The rubric names no ratio. The node uses WCAG 2.1 AA: 4.5:1 for normal text, 3.0:1 for large text (≥ 24px, or ≥ 18.66px bold).

## Caps and retry

`display_max_model_calls` (default 5) bounds every call in the node, checked before each call. `display_max_visual_crops` (default 12) bounds the crops sent. The node takes no verification feedback, so verification never retries it; its failures go to a person.

Tests: `tests/domain/display_check/`.
