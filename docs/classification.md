---
ai-generated: true
human-review: false
created: 2026-09-27
---

# classification

`classify_type` decides whether a page is in scope and which credit product it is about. It is
the only node that assigns types; `product_page` carries none. The judgment basis is the
`Rubrics` section of `design.md`.

## The three steps

The prompt forces the order, and a "no" stops the remaining steps from being answered.

1. Is this a page about a single product?
2. Is it a card company's own credit product or service?
3. Which of the five product types is it?

Each step answers with a quote from the page, a reason built on that quote, and the verdict.
A quote must be the text a reader sees, copied unchanged — `check_answer` rejects an answer
whose quote cannot be located in the page's visible text, ignoring whitespace.

## Why a quote is required at every step

The answer is only usable if it can be traced back to the page. So `check_answer` rejects an
answer that is missing a quote or a reason, that fills the later steps after a "no", or whose
quote is not on the page. One retry is allowed, with the problems fed back; a second failure
ends the review with `판정 불가`.

A "no" at step 1 or 2 is then verified by a second, independent call that sees only the
question, the page subject and a 600-character excerpt around the quote. If that call
disagrees, the result is `판정 불가` carrying both reasons — a disagreement is a signal for a
human, not something to resolve automatically.

## Results

| `product_type` | `page_type` | Meaning |
|---|---|---|
| 신용카드, 장기카드대출, 할부금융·리스 | 상품광고 | reviewable |
| 단기카드대출, 리볼빙 | 업무광고 | reviewable |
| 범위 밖 | None | step 1 or 2 answered no, and the verification agreed |
| 판정 불가 | None | validation failed twice, or the verification disagreed |

`범위 밖` and `판정 불가` both end the graph at `route_after_classify`. That is a normal result:
the caller reads `classification.reason`, which names the step and the grounds. Only system
errors raise.

## Test scenarios

Fixtures live in `tests/fixtures/classify/<case>.json` as `{url, product, html, expected}`.
Their html is the `content_llm.html` of the earlier `financial-product-disclosure-and-plain-language`
project, so it may differ in shape from what `preprocess_product_page` produces today — S-15
below keeps that gap on the record.

| case | product_type | page_type |
|---|---|---|
| lottecard-loca-professional | 신용카드 | 상품광고 |
| lottecard-card-loan | 장기카드대출 | 상품광고 |
| lottecard-auto-installment | 할부금융·리스 | 상품광고 |
| lottecard-revolving | 리볼빙 | 업무광고 |
| samsungfire-direct-auto-insurance | 범위 밖 (step 2) | None |
| kakaobank-fixed-deposit | 범위 밖 (step 2) | None |

### A. Faked model — free, in the default `pytest` run

| ID | Scenario | Expected | Where |
|---|---|---|---|
| S-01 | all six fixtures answered as expected | the table's types, a non-empty reason | `tests/domain/classification/test_classify.py` |
| S-02 | the out-of-scope fixtures | reason starts with `2단계`; calls are classify then verify | same |
| S-03 | a quote that is not on the page | one retry, then `판정 불가` / `판정 근거 부족` | same |
| S-04 | a missing reason | as S-03 | same |
| S-05 | a bad first answer, a good retry | the retry's result is used | same |
| S-06 | step 2 no, verification says yes | `판정 불가` / `판정 불일치`, carrying both reasons | same |
| S-07 | a quote differing only in whitespace | accepted | same |
| S-08 | step 1 no | `범위 밖`, reason starts with `1단계` | same |
| S-09 | `route_after_classify` with 범위 밖, 판정 불가 | END | `tests/graph/test_routes.py` |
| S-10 | `route_after_classify` with the five reviewable types | `judge_display_method` | same |
| S-11 | `classify_type` on a normal page | a `classification` slice, no exception | `tests/graph/test_nodes.py` |
| S-12 | `classify_type` on an empty `product_page` | `판정 불가` / `입력 없음`, no model call | same |

### B. Real model — paid, only with `-m use_llm`

| ID | Scenario | Checks | State |
|---|---|---|---|
| S-13 | the two sample URLs from preprocess through the graph | 신용카드 / 상품광고, every quote present | ran 2026-09-27, both as expected (gpt-5-mini) |
| S-14 | the six fixtures against a real model | expected vs actual, quotes present | ran 2026-09-27, all six as expected (gpt-5-mini, in=52,983 out=13,471, about $0.04). Now `tests/domain/classification/test_classify_llm.py` |
| S-15 | rebuild the fixtures from preprocess output and compare with S-14 | whether the snapshot-based result agrees | not run. S-13 and S-14 use different URLs, so this needs preprocessing run afresh on the fixtures' own URLs (four Lotte Card pages, Kakao Bank, Samsung Fire). None has a cached site rule, so each site may take the full 20-turn discovery loop — measure the cost on one fixture and get approval before running all six. |

### C. Risks that are not covered by a test

| ID | Item | Why |
|---|---|---|
| R-01 | the short-term-loan pitch at the end of a revolving page | S-14 classified `lottecard-revolving` correctly with a real model, so common rule 2 (another product's name in a pitch is not the subject) holds for that one fixture. Other combinations of pitch wording are unchecked. |
| R-02 | event, bundle and list pages | there is no fixture for the step-1 "no" path against a real model |
| R-03 | a real case where the verification call answers yes | knowing how often a mismatch happens needs many pages |
| R-04 | a cap on the number of calls | the worst case is three calls per page (two classify, one verify). Nothing in the code caps the calls or tokens of a whole run. |

## How to run the scenarios

- S-01 to S-12: `uv run pytest tests/classification tests/graph`.
- S-13 and S-14: `uv run pytest -m use_llm` (S-13 also needs `use_network`). Both cost money, so
  ask 영태 first.
- Every scenario shares one condition: `classify_page` and `classify_type` never raise.

## Follow-up candidates

- Run S-15, after measuring the site-rule discovery cost on a single fixture and getting approval.
- Add an event or list page fixture for R-02.
- Cap the calls and tokens of a whole run (R-04).
