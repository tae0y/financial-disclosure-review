---
ai-generated: true
human-review: false
created: 2026-09-28
---

# ADR-005 — Measure the display-method check by mutating rendered measurements

- **Status:** Accepted 2026-09-28

## Context

ADR-002 left the display-method items (E-group: size, contrast, separation, hiding) out of the
evaluation. Their evidence is the rendered page — computed font size, colours, bounds — and
deleting a sentence reflows everything after it, so a deletion does not produce a clean label.
Leaving one of the three core functions unmeasured was the largest gap in the evaluation.

## Decision

Change the measurement, not the page text. From two real reviews of 2026-09-28 the captured
product page (snapshots with computed styles) is exported to `eval/fixtures/display_*.json`.
For one block at a time the style rows are changed:

- `shrink`: font-size 9px, which is 6.75pt, under the rubric's 8pt (E02);
- `fade`: text colour rgb(204,204,204) on white, about 1.6:1, under WCAG AA 4.5:1 (E04).

A case is a mandatory disclosure chosen from the rubric's required wording (A01 설명서·약관 권유,
A11 신용평점 하락 경고, A13 원리금 변제 의무 경고), not from the model's labels. The watched item must
turn 부적합 **and cite that block**. A control applies the same change to marketing copy that is not a
mandatory disclosure; the check must not blame it. A `rules` arm applies the thresholds with no
notion of which text is mandatory.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Edit the HTML/CSS and re-render in a browser | Real, but re-rendering changes other measurements and needs the site's assets; slower and less controlled. A next step, not the first measure. |
| Human-labelled display verdicts | Same cost and independence problem as ADR-002. |
| Unit tests with synthetic pages only | Already exist (`tests/domain/display_check/`); they check the code, not the judgment on a real page. |

## Consequences

- The label is true by construction for the measurement; that the block is a mandatory
  disclosure rests on the rubric item named in `eval/cases/display_flip.json`, which a person can
  check in one look.
- It measures the chain the pipeline adds — labelling which text is mandatory, then applying the
  threshold — not the browser capture. Crops were not exported, so image-backed blocks stay
  unresolved in both arms.
- Two pages, four injected cases and two controls: a direction, not a rate.
