---
ai-generated: true
human-review: false
created: 2026-09-28
updated: 2026-09-28
---

# ADR-002 — Measure the explanation-duty check by deleting disclosures, not by an answer key

- **Status:** Accepted, 2026-09-27
- **Recorded here:** 2026-09-28. The first copy lived in `localdocs/adr/` (gitignored, local only);
  this repository copy is rewritten from `docs/evaluation.md` and
  `src/financial_disclosure_review/evaluation/defects.py`, written with the decision.

## Context

Unit tests showed that the modules were wired correctly, not that their judgments were right.
The obvious measure — a human answer key — costs the very thing the project is meant to save: a
product page carries 39 applicable explanation-duty items, so one labelled page is 39 legal
judgments by a person, and labels written by the prompt's author would not be independent anyway.

## Decision

Make the label true by construction. On a real page (`eval/fixtures/product_page_lotte.html`):

1. Run the check once per arm and keep the items every arm judged 적합, with the quotes each
   arm gave that are really on the page.
2. For each of up to three of them, delete those quoted sentences (`remove_quote`) and confirm from
   the rendered text that they are gone; a deletion that did not land is excluded, never counted.
   An item whose sentence an earlier target already removed is skipped, so no deletion is
   counted twice under two item codes (`shared_targets`).
3. Judge the variant again. The item turning 부적합 is a detection; the label needs no person
   because the sentence provably left the page.
4. Delete one long sentence that no arm's judgment cited (`longest_unused_sentence`) as a
   control: no item may turn 부적합 when an unrelated sentence leaves.
5. Run the same variants through an ablation arm — the same items in one call with no quote
   check, no condition step and no retry — so the difference measured is this project's
   engineering, not the model's general ability. Because step 1 already needs both arms, a run
   with one arm tests exactly the variants a run with both would.

Answers are recorded in a cassette so every number can be replayed for free.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Human answer key per page | 39 judgments per page; the resource the project saves; author-dependent. |
| Model-graded judgments (LLM as judge) | The grader shares the judged model's blind spots; no ground truth. |
| Synthetic pages written for the test | Would test the writer's phrasing, not real card-company pages. |

## Consequences

- Measured 2026-09-28 on the same deletions (F07, F15, 설명12): pipeline 1/3, ablation 1/3, both
  catching F07; quotes found on the page 67/67 against 45/156. Source:
  `eval/results/260928-201247-duty-flip-record.*`.
- Superseded 2026-09-28: the first rule let each arm pick deletions from its own answers, and the
  2026-09-27 result (pipeline 2/3, ablation 1/3; `260927-175540-duty-flip-record.*`) compared
  different deletions and counted one deleted sentence twice in each arm. Step 1 and step 2 above
  are the corrected rule (`9101c9a`).
- A miss can be the label's fault: after F15's and 설명12's sentences left, the pipeline cited
  another sentence that is on the edited page, because the page states those facts more than
  once. Such misses are listed as `missed_with_evidence_on_page`. Targets should be topics the page
  states once, or the deletion should take every sentence that carries the fact.
- The control turned F13·설명13 부적합 although their quote stayed. The three-round stability
  measurement of 2026-09-28 (`--suite stability`) found 11 of the 39 items changing between
  identical runs of the unchanged page (F05, F09, F11, F12, F14, 설명05, 설명09, 설명11, 설명14,
  설명21, 설명22), but
  F13 and 설명13 were steady there. Their flip is therefore a reaction to the page changing (a
  shorter prompt tipping a borderline 적합), not run-to-run noise — which is what the control is
  there to expose. The ablation arm flipped nothing on the same control.
- Only the deletion direction is measured; adding a missing disclosure is not.
- Rendered-layout items (display method) cannot be tested this way — deleting text reflows the
  page. They got their own design in ADR-005.
