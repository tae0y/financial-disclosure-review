---
ai-generated: true
human-review: false
created: 2026-09-30
---

# ADR-006 — Judge an ad page by the mandatory ad disclosures; write a short overview beside it

- **Status:** Accepted 2026-09-30 (영태). Supersedes the 준용 premise of the explanation-duty
  node, and the unit-by-unit reader explanation.

## Context

The explanation-duty node judged every public card-company page against the 설명의무 items of
`plain_service_rubric` (and their F-group twins), "applied by analogy" (준용). Two things went
wrong on a real credit-card ad (롯데카드 디지로카 Las Vegas, `data/live5/reports/demo-260930.md`):

- 설명01 asks for 금리·변동 여부·중도상환수수료. Its `applies_to` listed 신용카드 because the
  statute (금소법 제19조제1항제1호라목) covers every 대출성 상품, but a credit card has no
  중도상환수수료. The model followed the criterion literally and marked the page 부적합.
- 청약철회(설명16), 해지·해제(설명05), 계약기간(설명08), 분쟁조정(설명17) belong in the
  contract-stage product document. An ad page does not carry them, so nearly every card ad came
  out 부적합 on them, and 설명18 ("중요사항 누락") counted the same gaps again.

The root cause is the premise: 설명의무 binds the contract-stage explanation, not an ad. The rules
that bind an ad were already in the project — the A·B·C groups of `card_guardrail_rubric`
(금소법 제22조, 여신협회 광고규정·세부지침), whose product mapping is right (중도상환수수료 is
C05, 카드대출 only) — but no node judged whether those disclosures were on the page; they were
used only to label blocks for the display check.

Separately, the reader explanation rewrote the page one line (evidence card) at a time, and the
checks were built around that 1:1 shape (fact ledger per unit, fidelity tied to units). 영태's
intent was a plain overview of one or two paragraphs shown beside the page.

## Decision

1. `ad_disclosure_check` (was `explanation_duty_check`) judges the in-scope A·B·C items on the
   page. Scope is code-only (`applies_to` and `page_types`); a remaining `applies_condition` is
   judged by the model first, as before.
2. Explanation-duty items for the product type are **not judged**. They are returned as
   `deferred` and listed in the report as "상품설명서에서 확인할 설명의무 항목".
3. 설명01 and F01 no longer list 신용카드 in `applies_to`.
4. `persona_explanation` writes one or two paragraphs (≤ 1,200 characters) for the chosen
   reader, shown beside the page, never in place of it. Code checks: paragraph count, length,
   numbers not on the page, new absolutes, verdict words. A failing draft is asked again once;
   a second failure is held back with its `problems`, which verification sends back as the
   request for the next round.
5. The overview goes through the same A·B·C judgment as the page (영태, 2026-09-30). A
   difference (`누락`·`변경`·`추가`) fails the overview and asks for a new draft naming the
   code; a `판정 불가` comparison stays informational.

## Consequences

- **Breaking:** State and API keys change — `explanation_duty_check` → `ad_disclosure_check`
  (`plain` → `overview`, `ledger` removed, `deferred` added); `persona_explanation` drops
  `units`/`fact_ledger` for `overview`/`problems`; nodes `judge_explanation_original` →
  `judge_disclosure_original`, `judge_explanation_duty` → `judge_ad_disclosure`. Old
  checkpoints still produce a report but show no overview.
- The F↔설명 twin merge (`core/duty_codes.py`) is gone; nothing judged has twins any more.
- A 부적합 on an A·B·C item is a direct 위반 (binding 법령), not a 권고 미충족 by analogy.
- Evaluation: `duty-flip` becomes `disclosure-flip` (`eval/cases/disclosure_flip.json` v2).
  Prompts and items changed, so the recorded cassettes no longer match and must be re-recorded
  with paid calls before the suites replay. Earlier results in `docs/evaluation.md` were
  measured under the explanation-duty criteria and stay as history.
- Open: because the overview is judged like the page, a page-level disclosure the original
  carries (e.g. 심의필 번호 A07, 카드사 명칭 A02) is a `누락` if the overview leaves it out. If this
  makes overviews fail repeatedly on the paid re-measurement, the next decision is which A·B·C
  items an overview must carry.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Keep 준용 and tag each 설명 item as 광고 필수/품질/범위 밖 | Keeps the weak premise and needs ~50 hand classifications; the right criteria already exist. |
| Fetch the linked 상품설명서 PDF and judge 설명의무 there | Faithful to the statute, but needs collection, PDF parsing and a new evaluation set. A later step. |
| Add a `해당없음` verdict to the explanation-duty judgment | Fixes 설명01-style cases only; the ad/contract-stage mismatch remains. |
