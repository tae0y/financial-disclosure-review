---
ai-generated: true
human-review: false
created: 2026-09-28
---

# ADR-003 — Classify the product with a quoted, staged model judgment

- **Status:** Accepted 2026-09-10 (four legal types, multi-label), revised 2026-09-17 (card-company
  credit products, three stages)
- **Recorded here:** 2026-09-28, from the decision note in the project folder (outside this repository)
  `02 MVP 기능 구현/260910 아키텍처 결정 과정.md` §1 and `docs/classification.md`.

## Context

The product type decides which rubric items apply, so a wrong type silently applies the wrong
law. The data at hand did not support training: the AI Hub financial-product dataset labels only
investment and insurance products, and 금소법 제3조 lets one product belong to several types, which
a single-label softmax cannot express. On 2026-09-17 the scope narrowed to five card-company
credit products (신용카드·단기카드대출·장기카드대출·리볼빙·할부금융·리스), each with its own rules.

## Decision

A three-stage judgment in which every stage must quote the page: (1) is this one product's page;
(2) is it a card company's credit product; (3) which of the five types. A "no" at stage 1 or 2 is
re-checked by a second call on the 600 characters around the quoted sentence; if the two answers
disagree, the page goes to a person. The page type follows from the product type through a fixed
mapping checked against the law (`PAGE_TYPE_BY_PRODUCT`), not from a second model guess.

## Alternatives considered

| Alternative | Decision and reason |
|---|---|
| Keyword rules | Rejected on 2026-09-10 as brittle to renamed products and paraphrase. Kept as a measured baseline since 2026-09-28 (`classification/keyword`). |
| BERT fine-tuning (4-class) | Rejected: no labels for two of the types, single-label output contradicts 제3조. Notebook in the project folder (outside this repository): `관련자료/260910_AI_Hub_금융상품_유형분류_BERT_튜닝.ipynb`. |
| Embedding similarity to type definitions | Kept as a candidate only: fast, but cannot say why a page is a type. |
| One unstaged model call | Rejected: nothing to check a "no" against, no quote to show a reviewer. |

## Consequences

- Measured on six captured pages: gpt-5-mini 6/6 with a reason for every page, 8 calls, $0.035
  (2026-09-27). On the same pages on 2026-09-28, gpt-5 scored 5/6 for $0.190 (it rejected the
  auto-installment page as out of scope) and gpt-5-nano 4/6 for $0.024 (it rejected the card-loan
  page and returned 판정 불가 for the insurance page). Both larger and smaller models dropped an
  in-scope card page, the costliest error: that page would not be reviewed at all.
- The keyword baseline also scored 6/6 on those six pages. The pages are easy for it: each names
  its product repeatedly. The claim that keywords break on paraphrase is therefore untested by
  this suite; showing it needs pages that mention several products or rename them.
- Three repeated rounds gave the same type on all six pages (`--suite stability`).
