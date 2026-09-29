---
ai-generated: true
human-review: false
created: 2026-09-27
---

# display_check

`judge_display_method` judges the `E. 표시방법` items of the card guardrail rubric: whether the
mandatory disclosures are large enough, distinguishable enough from their background, separated
from each other, and not hidden behind a control. Code measures; the model labels and judges.

## What code measures and what the model decides

| Done by code | Done by the model |
|---|---|
| joining snapshot rows to the LLM-facing html, font size in pt, contrast ratio, visibility per state, markers and line boundaries, per-group minima and threshold lists, and the verdicts of E02, E04 and E05 | which group each block belongs to, and the verdict of every qualitative item (E01, E03, E06, E07, E08, …) |

**Code-decided items (`CODE_DECIDED` = E02 size, E04/E05 contrast).** Their verdict follows
from the measurements, so `code_verdict` sets it and they are never sent to `judge_items`
(`judgments.code_decided` lists them). A measured threshold violation is `부적합` citing exactly
the violating blocks. A pass needs every labelled block of the item to have been visible and
measured, with nothing unresolved: a labelled block never visible, undrawn text (`size_unmeasured`,
E02), image-backed text without a readable crop (`visual_unresolved`), unmeasured contrast, a
legacy capture (E04/E05) or disclosure text inside an image each make it `판정 불가`, and the
reason names what was missing. Backlog E1, 2026-09-29; this changes `judge_items` inputs, so the
display-flip cassette has to be re-recorded.

The model never computes a number. `VERDICT_TASK` says its grounds are the given measures and
block text only, and `check_verdicts` rejects a verdict that contradicts them: `적합` where the
threshold list is non-empty, or `부적합` that cites no block from that list. A second failing
answer is salvaged item by item — only the items named in the problems are downgraded to
`판정 불가`; anything structural raises.

## The block table

`display_blocks` keeps a row only if its normalized text is a text node, or a short run of
adjacent text nodes, of the LLM-facing html. That join is what ties a rendered measurement to
the text the other modules read. For each path it keeps the last state in which the block was
visible, so `default_visible`, `ever_visible` and `revealed_by` describe the same block across
the whole visit.

Flags in the compact line the model reads: `H` never visible in any capture, `D` revealed by a
user action, `M` a marker at the start of its line, `O` alone on its line, `S<n>` sentences in
that line.

## Assumptions 영태 has not yet confirmed

Both are stated in `judgments["assumptions"]` on every run, so a reader sees what was applied.

- **E02, px to pt.** The rubric says 8pt on A4 (여신금융협회 광고규정 세부지침, "A4용지 기준
  8포인트 이상"). A web page has no paper size, so the node uses computed CSS px × 0.75 ≥ 8pt at
  the captured viewport. The threshold is read from the rubric criterion at run time, not
  hard-coded.
- **Contrast threshold.** The rubric names no ratio. The node uses WCAG 2.1 SC 1.4.3 AA: 4.5:1
  for normal text, 3.0:1 for large text (≥ 24px, or ≥ 18.66px and weight ≥ 700).

## What cannot be measured, and why that is never a pass

Text drawn inside an image cannot be measured at all. Three guards keep that gap from turning
into a false `적합`:

- A block over a CSS background image or overlapping an `img` is flagged `visual_risk`. Its
  flat-colour contrast is not used as evidence; a saved rendered crop is sent to the vision call
  instead, and a missing, failed or uncertain crop leaves the block `visual_unresolved`. For
  E04 and E05 an otherwise-passing verdict then becomes `판정 불가`.
- An image whose `alt` names a disclosure topic from the mandatory items is flagged. While any
  such image stands, no item except E07 may pass. The flag is only kept when the quoted
  `alt_phrase` is at least 3 characters, really occurs in that image's alt, and occurs in the
  mandatory items' criteria — otherwise it is dropped and recorded in `dropped_image_flags`.
- A snapshot taken before rendered crops existed is `legacy_capture`: E04 and E05 are
  `판정 불가` and the page has to be preprocessed again.

- Text set below 1px is not drawn at all — the image-replacement pattern, where the words stay
  in the DOM for screen readers and the reader sees a picture of them. Such a block is flagged
  `undrawn_text`, gets no pt value, and is listed in `size_unmeasured`: E02 cannot cite it for a
  `부적합`, and while it stands an E02 `적합` becomes `판정 불가`. Found on 2026-09-28, when a
  LOCA CLASSIC review measured the image-replaced product name as 0pt and failed E02 on it.

`H` blocks prove nothing either. An E07 `부적합` must cite a block revealed by a user action,
because a block that was never visible in any capture says nothing about what a reader could see.

## Caps

`display_max_model_calls` bounds the whole node — two attempts for labelling, two for the
verdicts and one vision call share the same budget, and the cap is checked before each call.
`display_max_visual_crops` bounds how many crops are captured and sent.
