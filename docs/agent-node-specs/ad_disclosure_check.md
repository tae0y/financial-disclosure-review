---
ai-generated: true
human-review: false
created: 2026-09-27
updated: 2026-09-30
---

# ad_disclosure_check

`judge_ad_disclosure` judges the mandatory ad disclosures on the page, and lists the
explanation-duty items the reviewer has to confirm in the product document. It runs in the same
graph step as the reader advice, which it does not read. On a retry it keeps its previous rows
and re-judges only the codes verification flagged.

Until 2026-09-30 this node was `explanation_duty_check` and judged the 설명의무 items by analogy
(준용); that premise was wrong for an ad page
([ADR-006](../architecture-decisions/adr-006-ad-disclosure-instead-of-explanation-duty.md)). For
part of the same day it also judged a plain-language summary of the page against the same items
and compared the two; the summary was removed and that comparison with it
([ADR-007](../architecture-decisions/adr-007-advice-only.md)).

## Which items, and which are only listed

`load_disclosure_items` reads the A·B·C groups of `card_guardrail_rubric`: 광고 공통 의무표시 (A),
대출조건 (B) and 상품별 의무표시 (C), from 금소법 제22조 and the 여신협회 광고규정·세부지침. These
bind an advertisement directly, so a 부적합 reads as 위반 in the report.

`deferred_explanation_items` returns the 설명의무 items of `plain_service_rubric` whose
`applies_to` includes the product type, as `{code, question, applies_condition}`, leaving out the
items whose condition holds only on a 신청·가입·발급 화면 (설명19·25–28): neither an ad nor its
product document is that screen. They are not judged: 설명의무 (금소법 제19조) binds the
contract-stage product document, which an ad page is not. The report lists them, and the reader
advice picks the ones this reader should ask about. The F group of `card_guardrail_rubric` repeats
these duties and is neither judged nor listed.

## What code rules out and what the model decides

| Done by code | Done by the model |
|---|---|
| `applies_to` and `page_types` mismatch (`knowledge.rubrics.item_scope`), keeping the previous rows on a retry, checking every quote against the page | whether a remaining `applies_condition` holds, and the verdict per criterion |

## Condition, then criterion

The model answers `condition_status` before `verdict`. `불명확` is a first-class answer: when the
page does not say whether the condition holds, the item stays `applied: true` with
`condition_status: 불명확`, `verdict: 판정 불가` and no quote. Only `불성립` drops an item out of
`original`.

`_quote_ok` rejects a `적합` with no quote and any quote that cannot be located in the page. A
second answer that still fails is salvaged row by row — only the named codes are downgraded to
`판정 불가`; a mismatch in the set of codes raises.

## Output

`{items, original, deferred}`. `deferred` is written on the first round only; a retry leaves it as
it was in State.

## Retry

A request addressed to this module (`target: original`, with a code) re-judges that code alone,
with the request passed as `previous_feedback`; every other row is kept. A retry with no such
request makes no call. The page did not change, so re-judging it all would spend money to
produce a possibly different answer.
