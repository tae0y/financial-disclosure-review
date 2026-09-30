---
ai-generated: true
human-review: false
created: 2026-09-30
updated: 2026-09-30
---

# ADR-007 — Give the reader advice on what to ask, not a summary of the page

- **Status:** Accepted, 2026-09-30

## Context

The plain-language output could either restate the ad page in easier words or tell a specific reader what the ad does not explain and they should ask before signing.

- A summary restates what the page already says. Every restatement is a new place to be wrong, and policing it needs the full disclosure comparison run a second time. When the evidence cards miss a line, the summary can state that the page lacks something it has.
- Advice adds what the ad is not required to say: the explanation-duty items ([ADR-006](adr-006-ad-disclosure-instead-of-explanation-duty.md)) that matter most to this reader.

## Decision

1. `generate_persona_explanation` writes one paragraph of advice: 2–5 explanation-duty items the page does not explain and that matter to the chosen reader, named in plain words, with why for this reader, never with the answer.
1. The model sees every page line, so it does not recommend what the page already explains.
1. Code checks the advice: 2–5 codes from the product type's checklist, at most 700 characters, no rubric code in the text, no number or absolute the page lacks, no verdict word. A failing draft is asked again once, then held back.
1. The report stars the advised items in the product-document checklist, so a reviewer sees what the reader was told to ask next to the full list.

## Alternatives considered

| Alternative | Why not |
|---|---|
| A page summary fed every page line | Still restates the page and needs the comparison machinery to stay correct. |
| A fixed list per product type | The list is already in the report; the value is choosing and explaining for this reader. |

## Consequences

- One drafting call per round, and no second disclosure judgment.
- The advice is guarded by code checks, not judged against the ad disclosures. On two pages it passed its checks in every round and rejected 10/10 injected defects.
- Which items the advice picks varies between runs, and no person has yet scored whether it helps the reader. A review sheet for that is in `eval/review_sheet.py`.
