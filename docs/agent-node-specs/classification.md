---
ai-generated: true
human-review: false
created: 2026-09-27
updated: 2026-09-30
---

# Classification (`classify_type`)

This page describes how `classify_type` decides whether a page is in scope and which card-company credit product it advertises.

It is the only node that assigns types. Which rubric items apply follows from its result; see [Rubrics and scope](../architecture.md#rubrics-and-scope).

## Input and output

| | Content |
|---|---|
| Reads | `product_page` |
| Writes | `classification`: `product_type`, `page_type`, reason, quotes per step |
| Model use | 1–2 structured calls, plus one verification call after a "no" |

## Three quoted steps

The prompt forces the order, and a "no" stops the remaining steps.

1. Is this a page about a single product?
1. Is it a card company's own credit product or service?
1. Which of the five product types is it?

Each step answers with a quote from the page, a reason built on that quote, and a verdict. Code rejects an answer that lacks a quote or reason, fills later steps after a "no", or quotes text that is not in the page's visible text (whitespace ignored). One retry is allowed with the problems fed back.

A "no" at step 1 or 2 is re-checked by a second, independent call that sees only the question, the page subject from the first answer and 600 characters around the quote. If it disagrees, the result is `판정 불가` carrying both reasons.

## Results

The page type follows from the product type in code, not from a second model guess.

| `product_type` | `page_type` | Meaning |
|---|---|---|
| 신용카드, 장기카드대출, 할부금융·리스 | 상품광고 | reviewable |
| 단기카드대출, 리볼빙 | 업무광고 | reviewable |
| 범위 밖 | none | step 1 or 2 answered no, and the verification call agreed |
| 판정 불가 | none | validation failed twice, the verification call disagreed, or there was no page content |

`범위 밖` and `판정 불가` skip every check and go straight to `end_report`. The requester still receives a report naming the step and its grounds (`검토 대상 아님` or `판정 불가`). Only system errors raise.

## Limits

- The six evaluation pages all name their product type in the title, so a keyword baseline also scores 6/6. Pages that paraphrase or mention several products are not yet tested.
- No real-model case exists yet for the step-1 "no" path (event, bundle or list pages).

Tests: `tests/domain/classification/` (free, faked model) and `tests/domain/classification/test_classify_llm.py` (paid, `-m use_llm`).
