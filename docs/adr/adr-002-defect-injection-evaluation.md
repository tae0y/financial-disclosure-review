---
ai-generated: true
human-review: false
created: 2026-09-28
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

1. Run the check once and keep the items judged 적합 whose quote is really on the page.
2. For each of up to three of them, delete the quoted sentence (`remove_quote`) and confirm from
   the rendered text that it is gone; a deletion that did not land is excluded, never counted.
3. Judge the variant again. The item turning 부적합 is a detection; the label needs no person
   because the sentence provably left the page.
4. Delete one long sentence that no judgment cited (`longest_unused_sentence`) as a control: no
   item may turn 부적합 when an unrelated sentence leaves.
5. Run the same variants through an ablation arm — the same items in one call with no quote
   check, no condition step and no retry — so the difference measured is this project's
   engineering, not the model's general ability.

Answers are recorded in a cassette so every number can be replayed for free.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Human answer key per page | 39 judgments per page; the resource the project saves; author-dependent. |
| Model-graded judgments (LLM as judge) | The grader shares the judged model's blind spots; no ground truth. |
| Synthetic pages written for the test | Would test the writer's phrasing, not real card-company pages. |

## Consequences

- Measured 2026-09-27: pipeline 2/3 detected, ablation 1/3; quotes found on the page 66/66 against
  66/156. Source: `eval/results/260927-175540-duty-flip-record.*`.
- A miss can be the method's fault: F15's fact was stated twice on the page, so deleting one
  sentence left the ground intact. Targets should be topics the page states once.
- The control turned F13·설명13 부적합 although their quote stayed. The three-round stability
  measurement of 2026-09-28 (`--suite stability`) found 11 of the 39 items changing between
  identical runs of the unchanged page (F05, F09, F11, F12, F14, 설명05, 설명09, 설명11, 설명14,
  설명21, 설명22), but
  F13 and 설명13 were steady there. Their flip is therefore a reaction to the page changing (a
  shorter prompt tipping a borderline 적합), not run-to-run noise — which is what the control is
  there to expose.
- Only the deletion direction is measured; adding a missing disclosure is not.
- Rendered-layout items (display method) cannot be tested this way — deleting text reflows the
  page. They got their own design in ADR-005.
