---
ai-generated: true
human-review: false
created: 2026-09-30
---

# ADR-007 — Keep only the reader-tailored advice; drop the page summary

- **Status:** Accepted 2026-09-30 (영태). Supersedes the summary paragraph of ADR-006.

## Context

After ADR-006 the plain-language output had two paragraphs: a summary of the ad page, judged
against the same mandatory ad disclosures as the page, and advice on which explanation-duty items
the reader should check in the product document. On the sample report of 2026-09-30 (롯데
디지로카 Las Vegas, `data/live6/`):

- the summary failed six disclosure items and stated that the page had no 이자율 or 경고문구,
  which was false — the evidence cards of that run had missed them, and the summary saw only the
  lines cards cited;
- the advice picked four items that fit a 70대, low-familiarity reader (상환방법별 부담, 연체
  불이익, 연회비 반환, 신용평점 영향) and gave reasons in the reader's terms.

A summary restates what the page already says, so every error in it is a new misstatement and it
needs the whole disclosure comparison to police it. The advice adds what the ad is not required
to say and the reader most needs to ask. 영태 judged the advice "최고의 MVP".

## Decision

1. `persona_explanation` writes one paragraph of advice only (`advice`, `advice_codes`): 2–5
   explanation-duty items the page does not explain and that matter to this reader, named in
   words, with why for this reader, never with the answer.
2. The model sees every page line, not only the lines cards cite, so it does not recommend what
   the page already explains.
3. Code checks the codes (2–5, from the product type's checklist), length (≤ 700 characters), no
   rubric code in the text, no number the page lacks, no absolute the page lacks, no verdict word.
4. `ad_disclosure_check` judges the page only: the overview-side judgment, the fidelity step and
   `OVERVIEW_REQUIRED` are removed. It runs in the same step as the advice; both feed
   verification, and a retry sends every failed node back at once.

## Consequences

- **Breaking:** `persona_explanation.overview` → `advice` (+ `advice_codes`);
  `ad_disclosure_check.overview`/`fidelity` removed; node `judge_disclosure_original` removed;
  report summary `advice_items`/`advice_withheld` replace the overview and fidelity counts.
- One model call fewer per round for the disclosure check (no overview judgment, no fidelity), and
  the advice is one call.
- The advice is not judged against the ad disclosures; its guard is the code checks and the human
  review sheet (`eval/review_sheet.py`: 적절성, 이해도, 지어낸 답).
- The report stars the advised items in the product-document checklist, so a reviewer sees what
  the reader was told to ask next to the full list.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Keep the summary and feed it every page line | Still restates the page; each restatement is a new place to be wrong and needs the comparison machinery. |
| Advice without reader tailoring (fixed list per product type) | The list already exists in the report; the value is choosing and explaining for this reader. |
