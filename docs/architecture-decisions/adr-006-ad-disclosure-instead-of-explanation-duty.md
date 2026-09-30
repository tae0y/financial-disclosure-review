---
ai-generated: true
human-review: false
created: 2026-09-30
updated: 2026-09-30
---

# ADR-006 — Judge an ad page by the mandatory ad disclosures, not the explanation duty

- **Status:** Accepted, 2026-09-30

## Context

The pages under review are public card-company advertisements. Two rule sets could be applied:

- **Mandatory ad disclosures** (A·B·C groups of `card_guardrail_rubric`, from 금소법 제22조 and the 여신협회 광고규정·세부지침) bind an advertisement directly, with a product mapping that fits each card product.
- **Explanation duty** (`plain_service_rubric`, 금소법 제19조) binds the contract-stage product document. Items such as 청약철회, 해지·해제, 계약기간 and 분쟁조정 belong in that document, and some do not fit every product (a credit card has no 중도상환수수료). Judging an ad against them marks nearly every card ad 부적합 on duties it does not carry.

## Decision

1. `judge_ad_disclosure` judges the in-scope A·B·C items on the page. Code decides scope from `applies_to` and `page_types`; the model judges a remaining applicability condition first, then the verdict, and every 적합 must quote the page.
1. Explanation-duty items for the product type are not judged. They are listed in the report as items to confirm in the product document, leaving out those that apply only on an application screen.
1. A 부적합 on an A·B·C item is reported as a direct 위반 (binding: 법령).

## Alternatives considered

| Alternative | Why not |
|---|---|
| Apply the explanation duty to ads by analogy, tagging each item as ad-relevant or not | Keeps a weak legal premise and needs about 50 hand classifications, while the right criteria already exist. |
| Fetch the linked product-document PDF and judge the explanation duty there | Faithful to the statute, but needs PDF collection, parsing and a new evaluation set. A later step. |
| Add a `해당없음` verdict to the explanation-duty judgment | Fixes product mismatches only; the ad versus contract-stage mismatch remains. |

## Consequences

- Findings read as breaches of rules that actually bind the page, so a reviewer can act on them.
- The explanation-duty items still reach the reader: the reader advice picks the ones to ask about ([ADR-007](adr-007-advice-only.md)).
- Whether the product document itself meets the explanation duty is out of scope.
