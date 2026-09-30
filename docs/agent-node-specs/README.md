---
ai-generated: true
human-review: false
created: 2026-09-30
---

# Agent node specs

One review is one run of a fixed LangGraph graph (`graph/build.py`). This page is the map: what
each node does, what it reads and writes, and how the run flows from a URL to the report. Each
node's own page has the detail.

## Workflow

```text
START
  └→ preprocess_product_page*            page agent: collect the product's own content
       ├─ no html ──────────────────────────────────────────────────────────→ end_report
       └→ classify_type                  in scope? which of five product types?
            ├─ 범위 밖 / 판정 불가 ─────────────────────────────────────────→ end_report
            └→ extract_evidence_cards    fact-shaped cards from the page text
                 └→ judge_display_method size, contrast, separation, hiding (E group)
                      ├→ generate_persona_explanation*   plain overview for one reader ─┐
                      └→ judge_disclosure_original       A·B·C on the page only ─────────┤
                                                                                         ↓
                                          judge_ad_disclosure   A·B·C on the overview, differences
                                                └→ verify_answer   cross-checks, no model call
                                                     ├─ passed / nothing retryable / 2 rounds → end_report
                                                     └→ retry_dispatch
                                                          ├→ generate_persona_explanation (overview asked to change)
                                                          └→ judge_ad_disclosure (a quote asked to change)
end_report → END

* bounded tool-calling agents; every other step is at most a few structured model calls or code.
```

The two middle branches run in the same LangGraph step: the overview and the original side of
the disclosure check both read only the page and the cards, so neither waits for the other.
`judge_ad_disclosure` runs once both are done. A retry re-enters at one node and follows the
edges from there; it never re-collects, re-classifies, re-extracts or re-measures the page.

## Nodes

| Node | Spec | Reads | Writes | What it does | Model use |
|---|---|---|---|---|---|
| `preprocess_product_page` | [product_page](product_page.md) | `product_page.url` | `product_page` | Opens the page in Chromium, finds the product's own content (expanding tabs and accordions), stores snapshots with computed styles, and saves a reusable rule per page family. Open evidence gaps are recorded, not hidden. | Tool-calling agent with a turn budget and stop reasons; none when a saved rule replays |
| `classify_type` | [classification](classification.md) | `product_page` | `classification` | Three quoted steps: single product? card company's own credit product? which of 신용카드, 단기카드대출, 장기카드대출, 리볼빙, 할부금융·리스? The page type follows from the product type in code (상품광고 for 신용카드·장기카드대출·할부금융·리스, 업무광고 for 단기카드대출·리볼빙). `범위 밖`·`판정 불가` end the review with a report. | 1–2 structured calls plus one verification call |
| `extract_evidence_cards` | [evidence_cards](evidence_cards.md) | `product_page`, `classification` | `evidence_cards` | Turns page text lines into cards (claim, conditions, exceptions, numbers, quote, source line); code keeps only cards whose quote is really on the page and records coverage gaps. | One structured call, one retry |
| `judge_display_method` | [display_check](display_check.md) | `product_page`, `classification`, `evidence_cards` | `display_check` | Judges the E-group display rules. Code measures font size, contrast and visibility and decides E02/E04/E05; the model labels which blocks are mandatory disclosures and judges the qualitative items. | Structured calls (labels, verdicts), optional image crops |
| `generate_persona_explanation` | [persona_explanation](persona_explanation.md) | `evidence_cards`, `classification`, `verification.feedback` | `persona_explanation` | Chooses one reader (free text, dataset uuid or attributes, or the product-type default) and writes a one- or two-paragraph plain overview shown beside the page. Code checks length, numbers, absolutes and verdict words; a failing draft is held back. | Reader-selection agent when the reader is given in free text; one drafting call |
| `judge_disclosure_original` | [ad_disclosure_check](ad_disclosure_check.md) | `product_page`, `classification` | `ad_disclosure_check` (original side) | Judges the in-scope mandatory ad disclosures (A·B·C of `card_guardrail_rubric`) on the page, condition first, with quotes checked against the page. Lists the 설명의무 items for the product type as `deferred`, unjudged. | One structured call |
| `judge_ad_disclosure` | [ad_disclosure_check](ad_disclosure_check.md) | `product_page`, `persona_explanation`, `ad_disclosure_check`, `verification.feedback` | `ad_disclosure_check` | Judges the overview by the same items, then asks the model where the two sides differ (누락, 변경, 추가). On a retry it re-judges only the codes it was asked about. | Two structured calls |
| `verify_answer` | [verification](verification.md) | every module key | `verification` | Cross-checks quotes, ids and measurements against the page, turns 판정 불가 into failures, and writes concrete requests for the next round. | None |
| `retry_dispatch` | [verification](verification.md) | `verification` | `verification` (retry fields) | Picks the earliest node that can act on the requests. | None |
| `end_report` | [report](report.md) | every module key | `report` | Maps the results to a status and publish decision, the reviewer's actions, findings, limits and cost, and a short markdown for the requester. | None |

`plain_language` is the pre-2026-09-29 line-by-line rewrite. The graph no longer calls it; it is
kept for the `plain-contract` evaluation suite ([plain_language](plain_language.md)).

## Rules every node follows

- A node writes only its own State key (`core/state.py`); settings travel in `Context`.
- Every quote a model gives is located in the text it claims to come from; a quote that is not
  there is rejected or turns the item into `판정 불가`.
- `판정 불가` is never a pass. It becomes a reviewer task in the report.
- Every model call is metered against the run's call and cost caps (`core/usage.py`); a cap hit
  after collection still ends in a `판정 불가` report naming the interrupted node.
- Legal criteria come from the rubric DB built from `assets/*.yaml`; a node never invents a
  criterion. Which criteria apply is decided by code from the classified product and page type.
