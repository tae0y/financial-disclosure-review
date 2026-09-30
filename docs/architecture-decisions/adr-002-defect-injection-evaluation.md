---
ai-generated: true
human-review: false
created: 2026-09-28
updated: 2026-09-30
---

# ADR-002 — Measure the disclosure check by deleting disclosures, not by an answer key

- **Status:** Accepted, 2026-09-27

## Context

Unit tests show that modules are wired correctly, not that their judgments are right. A human answer key costs the very thing the project is meant to save: one labelled page is 17 legal judgments by a person, and labels written by the prompt's author are not independent.

## Decision

Make the label true by construction, on real pages:

1. Judge the page once per arm and keep the items every arm judged 적합, with the quotes each arm gave that are on the page.
1. For each target, delete those quoted sentences and confirm from the rendered text that they are gone. A deletion that did not land is excluded.
1. Judge the edited page again. The item turning 부적합 is a detection; no person is needed because the sentence provably left the page.
1. Delete one long sentence no arm cited, as a control. No item may turn 부적합.
1. Run the same deletions through an ablation arm — one call, no quote check, no condition step, no retry — so the difference measured is this project's engineering, not the model's general ability.

Answers are recorded in a cassette, so every number can be replayed for free.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Human answer key per page | 17 legal judgments per page; author-dependent. |
| A model grading the judgments | The grader shares the judged model's blind spots; no ground truth. |
| Synthetic pages written for the test | Tests the writer's phrasing, not real card-company pages. |

## Consequences

- On five pages with 33 deletions and 10 controls, both arms caught 20/33. The pipeline's quotes were all on the page (574/574) against 529/743 for the ablation; it flipped 3/10 controls against 1/10. See [Evaluation](../evaluation.md).
- A miss can be the label's fault: when the page states a fact twice, the check can pass the item on the remaining sentence. Such misses are reported separately (`missed_with_evidence_on_page`); targets should be facts the page states once.
- Only the deletion direction is measured, not adding a missing disclosure.
- Display items cannot be tested this way, because deleting text reflows the page; see [ADR-005](adr-005-display-flip-evaluation.md).
