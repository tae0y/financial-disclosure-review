---
ai-generated: true
human-review: false
created: 2026-09-27
updated: 2026-09-30
---

# ad_disclosure_check

`judge_ad_disclosure` judges the mandatory ad disclosures twice — once against the original page,
once against the plain-language overview — and records where the two answers differ. The original
side reads only the page, so on a first round `judge_disclosure_original` judges it in the same
graph step as the overview and `judge_ad_disclosure` reuses those rows; without them (a rerun from
an older checkpoint) it judges the original side itself. A judgment whose check rejects only some
codes asks again for those codes alone and merges the answer.

Until 2026-09-30 this node was `explanation_duty_check` and judged the 설명의무 items by analogy
(준용). That premise was wrong for an ad page; see
[ADR-006](../architecture-decisions/adr-006-ad-disclosure-instead-of-explanation-duty.md).

## Which items, and which are only listed

`load_disclosure_items` reads the A·B·C groups of `card_guardrail_rubric`: 광고 공통 의무표시 (A),
대출조건 (B) and 상품별 의무표시 (C), from 금소법 제22조 and the 여신협회 광고규정·세부지침. These
bind an advertisement directly, so a 부적합 reads as 위반 in the report.

`deferred_explanation_items` returns the 설명의무 items of `plain_service_rubric` whose
`applies_to` includes the product type, as `{code, question, applies_condition}`, leaving out the
items whose condition holds only on a 신청·가입·발급 화면 (설명19·25–28): neither an ad nor its
product document is that screen. They are not
judged: 설명의무 (금소법 제19조) binds the contract-stage product document, which an ad page is not.
The report lists them for the reviewer to confirm in the 상품설명서. The F group of
`card_guardrail_rubric` repeats these duties and is neither judged nor listed.

## What code rules out and what the model decides

| Done by code | Done by the model |
|---|---|
| `applies_to` and `page_types` mismatch (`knowledge.rubrics.item_scope`), reusing the original side on a retry, picking the fidelity candidates, checking every quote against the real text | whether a remaining `applies_condition` holds, the verdict per criterion, and how the two sides differ |

## Condition, then criterion

The model answers `condition_status` before `verdict`. `불명확` is a first-class answer: when the
page does not say whether the condition holds, the item stays `applied: true` with
`condition_status: 불명확`, `verdict: 판정 불가` and no quote, and the same row is reused on the
overview side without a second call. Only `불성립` drops an item out of `original`.

`_quote_ok` rejects a `적합` with no quote and any quote that cannot be located in the text it was
supposed to come from. A second answer that still fails is salvaged row by row — only the named
codes are downgraded to `판정 불가`; a mismatch in the set of codes raises.

## Overview side and fidelity

The overview is judged by the same procedure, looking only at the overview, but only on the
items it must carry (`OVERVIEW_REQUIRED` in `rubric.py`): 이자율·수수료 (A04·A05), 부가서비스 조건
(A10), 경고문구 (A11–A13), 상환방법 (B02) and the product-specific disclosures (C01–C08). Page
metadata — 설명서 권유, 회사명, 상품명, 설명받을 권리, 심의필 번호·유효기간, 통계 출처, 발급 기준 —
stays on the page the overview sits beside and is not asked of it (영태, 2026-09-30, after the
first live run failed an overview for leaving out 심의필 번호).

`fidelity_candidates` sends to the model only the codes whose verdict or quote differs between the
two sides, and `변화없음` answers are dropped. Each item goes with its `criterion`, and the task
compares only what the criterion asks about: two quotes that differ on something else are no
difference (the first live run called A02 변경 because the page quote was about L.POINT and the
overview quote about 할인 혜택). Detail a summary drops — 구간별 할인율, 기본·제휴 연회비 내역 — is
`변화없음` when the criterion's content is still there.

Each row carries `original_quote`, `quote` (overview side) and `informational`. A `변경` or `추가`,
or a `누락` where the overview does not carry the item at all (its own verdict is not 적합), fails
`persona_explanation` in `verify_answer` with a request naming the code, so the next round redraws
the overview. A `누락` on an item the overview still carries is informational: lost detail. `추가` is not a fix: an overview that fills a gap the page left does
not resolve the page's `부적합`. A `판정 불가` comparison is informational.

## Output

`{items, original, overview, fidelity, deferred}`. `deferred` is written on the first round only;
a retry leaves it as it was in State.

## Retry

When the node is called again with the previous `items` and `original`, it reuses both and
recomputes only `overview` and `fidelity`. A request addressed to the original side
(`target: original`, with a code) re-judges that code alone. The page did not change, so
re-judging it would spend money to produce a possibly different answer.
`tests/domain/ad_disclosure_check/` asserts that no `DisclosureJudgments` call is made on the
plain retry path.
