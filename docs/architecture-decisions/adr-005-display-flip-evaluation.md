---
ai-generated: true
human-review: false
created: 2026-09-28
updated: 2026-09-30
---

# ADR-005 — Measure the display-method check by mutating rendered measurements

- **Status:** Accepted, 2026-09-28

## Context

Display-method items (E group: size, contrast, separation, hiding) are judged from the rendered page: computed font size, colours and bounds. Deleting a sentence reflows everything after it, so the deletion method of [ADR-002](adr-002-defect-injection-evaluation.md) does not give a clean label here.

## Decision

Change the measurement, not the page text. From two real reviews, export the captured page (snapshots with computed styles) and change one block at a time:

- `shrink`: font size 9px, which is 6.75pt, under the rubric's 8pt (E02).
- `fade`: text colour rgb(204,204,204) on white, about 1.6:1, under WCAG AA 4.5:1 (E04).

Targets are mandatory disclosures chosen from the rubric's required wording (A01, A11, A13), not from the model's labels. The item must turn 부적합 and cite that block. A control applies the same change to marketing copy, which must not be blamed. A `rules` arm applies the thresholds with no notion of which text is mandatory.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Edit the HTML/CSS and re-render in a browser | Re-rendering changes other measurements and needs the site's assets. A later step. |
| Human-labelled display verdicts | Same cost and independence problem as ADR-002. |
| Synthetic pages only | Already covered by unit tests; they check the code, not the judgment on a real page. |

## Consequences

- The pipeline caught 4/4 injected defects and blamed 0/2 controls; the `rules` arm also caught 4/4 but blamed 2/2 controls. What the pipeline adds is telling mandatory disclosures from other text.
- It measures labelling plus thresholds, not the browser capture. Image-backed text stays unresolved in both arms.
- Two pages, four injections and two controls give a direction, not a rate.
