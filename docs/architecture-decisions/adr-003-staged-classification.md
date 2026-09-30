---
ai-generated: true
human-review: false
created: 2026-09-28
updated: 2026-09-30
---

# ADR-003 — Classify the product with a quoted, staged model judgment

- **Status:** Accepted, 2026-09-17

## Context

The product type decides which rubric items apply, so a wrong type silently applies the wrong law. The scope is five card-company credit products (신용카드, 단기카드대출, 장기카드대출, 리볼빙, 할부금융·리스). No labelled data covers them, and 금소법 제3조 lets one product belong to several types, which a single-label classifier cannot express.

## Decision

- Three stages, each answered with a quote from the page: (1) is this one product's page, (2) is it a card company's credit product, (3) which of the five types.
- A "no" at stage 1 or 2 is re-checked by a second call on the text around the quote. If the two disagree, the page goes to a person as `판정 불가`.
- The page type follows from the product type through a fixed mapping (`PAGE_TYPE_BY_PRODUCT`), not from a second model guess.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Keyword rules | Brittle to renamed products and paraphrase. Kept as a measured baseline. |
| Fine-tuned BERT classifier | No labelled data for the five types; single-label output contradicts 제3조. |
| Embedding similarity to type definitions | Cannot say why a page is a type. |
| One unstaged model call | Nothing to check a "no" against, and no quote to show a reviewer. |

## Consequences

- On six captured pages gpt-5-mini scored 6/6 with a reason for every page (8 calls, $0.035). gpt-5 scored 5/6 and gpt-5-nano 4/6; both rejected an in-scope page, the costliest error because that page is never reviewed.
- The keyword baseline also scored 6/6, because each page names its type in the title. Showing where keywords break needs pages that mention several products or hide the type.
- Three repeated rounds gave the same type on all six pages.
