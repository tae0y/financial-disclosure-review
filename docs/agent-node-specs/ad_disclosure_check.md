---
ai-generated: true
human-review: false
created: 2026-09-27
updated: 2026-09-30
---

# Ad Disclosure Check (`judge_ad_disclosure`)

This page describes how `judge_ad_disclosure` judges the mandatory ad disclosures on the page and lists the 설명의무 items the reviewer must confirm in the product document.

It runs in the same graph step as the reader advice and does not read it. Why an ad page is judged by ad rules rather than 설명의무 is recorded in [ADR-006](../architecture-decisions/adr-006-ad-disclosure-instead-of-explanation-duty.md).

## Input and output

| | Content |
|---|---|
| Reads | `product_page`, `classification`, its own previous rows, `verification.feedback` for this module |
| Writes | `ad_disclosure_check`: `{items, original, deferred}` |
| Model use | one structured call per round |

## Judged items and listed items

- **Judged:** the A·B·C groups of `card_guardrail_rubric` — 광고 공통 의무표시 (A), 대출조건 (B), 상품별 의무표시 (C), from 금소법 제22조 and the 여신협회 광고규정·세부지침. These bind an advertisement directly, so a `부적합` reads as 위반 in the report.
- **Listed, not judged (`deferred`):** the 설명의무 items of `plain_service_rubric` that apply to the product type, as `{code, question, applies_condition}`. 설명의무 (금소법 제19조) binds the contract-stage product document, not an ad. Items that hold only on an application screen (설명19, 25–28) are left out. The report lists the rest, and the reader advice picks the ones this reader should ask about.

## How it works

| Done by code | Done by the model |
|---|---|
| dropping items whose `applies_to` or `page_types` do not match; checking every quote against the page; keeping previous rows on a retry | whether a remaining `applies_condition` holds, then the verdict per item |

The model answers the condition before the verdict. `불명확` is a valid answer: the item stays applied with `판정 불가` and no quote. Only `불성립` removes an item.

Code rejects a `적합` without a quote and any quote not found on the page. After a second failing answer, only the named codes are downgraded to `판정 불가`; a mismatch in the set of codes raises.

## Retry

A verification request addressed to this module names a code. The retry re-judges only that code, with the request as feedback, and keeps every other row. A retry with no such request makes no call. `deferred` is written on the first round only.

Tests: `tests/domain/ad_disclosure_check/`.
