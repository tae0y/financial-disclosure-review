---
ai-generated: true
human-review: false
created: 2026-09-27
---

# plain_language

`generate_plain_lang` rewrites the product page's own sentences in plain Korean, one visual line
at a time. The model writes; code decides what may be kept. A block whose rewrite fails a check
is not retried a third time — it is replaced by the original sentence, and the failure stays in
`contract_errors` for `verify_answer` to read.

## Blocks

`plain_blocks` splits the LLM-facing html at block elements and `<br>`, drops a line it cannot
locate again in the page text, and merges repeated lines into one. Ids are positional (`b0`,
`b1`, …), so the same html always produces the same ids and the same `data-source-id` attributes
in the generated html. Both `verify_answer` and the fidelity rows address blocks by those ids.

## What code checks and what the model decides

| Done by code | Done by the model |
|---|---|
| splitting the page into blocks, numbers present in the source quote, added absolute/superlative phrasing, a hedge turned into a certainty, dropped condition keywords, which glossed terms are really in the quote | the plain wording of each block, and which terms it glossed |

The model gets the mandatory-disclosure criteria (`A·B·C` groups of the card guardrail rubric)
as context so it does not drop them, and the previous round's `verification.feedback` addressed
to `generate_plain_lang`. It never gets the rubric's plain-language items: the node reports on
those itself.

`contract.py` holds the checks. Every one of them is decidable from the two strings, so none of
them needs a model call:

- a number in the rewrite that the source quote does not have, or one of its numbers missing
- an absolute or superlative phrase (`누구나`, `무조건`, `최고`, …) the source quote did not use
- a source quote that hedges (`~할 수 있습니다`, `심사 결과에 따라`) rewritten without any hedge
- a condition or penalty keyword (`제외`, `한도`, `위약금`, `연체`, …) present in the quote and
  absent from the rewrite

The last one is deliberately blunt: it reports "누락 가능", not a proven omission, and its cost is
that the block falls back to the original wording.

## What the node reports about the rubric, and what it does not

`plain_items_report` answers per `쉬운말서비스` item, but only as far as this node actually
checked:

| Item | Verdict | Why |
|---|---|---|
| `쉬운말01` | always `판정 불가` | whether a mandatory disclosure survived is `judge_explanation_duty`'s answer, not this node's |
| `쉬운말08`, `쉬운말10` | `적용` when any term was glossed, else `해당없음` | the node can show `term_refs`, not judge whether a gloss changed the concept |
| `쉬운말11`, `14`, `15`, `17`–`22` | always `판정 불가` | sentence complexity, block ordering, UI elements and pre-publication human review are outside what this node produces |
| the rest | `위반 발견` when a matching contract error fired, else `적용` | the item is mapped to the error markers it corresponds to |

`plain_scope` rather than `knowledge.rubrics.item_scope` decides which items apply, because
`plain_service_rubric` lists its screens under `targets`, not `page_types`.

## Assumptions 영태 has not yet confirmed

- The mapping from rubric item to contract-error marker (`PLAIN_ITEM_ERROR_MARKERS`) is this
  node's reading of each item, not something the rubric states.
- `쉬운말20` is reported as out of scope while its "replace a failed block with the original"
  half is in fact implemented. The reason string says so.
