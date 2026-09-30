---
ai-generated: true
human-review: false
created: 2026-09-27
---

# plain_language

`generate_plain_lang` rewrites the product page's own sentences in plain Korean, one visual line
at a time. The model writes; code decides what may be kept — except for one check that a
mechanical rule cannot make, which a second, narrower model call judges qualitatively. A block
whose rewrite fails a check is not retried a third time — it is replaced by the original
sentence, and the failure stays in `contract_errors` for `verify_answer` to read.

## Blocks

`plain_blocks` splits the LLM-facing html at block elements and `<br>`, drops a line it cannot
locate again in the page text, and merges repeated lines into one. Ids are positional (`b0`,
`b1`, …), so the same html always produces the same ids and the same `data-source-id` attributes
in the generated html. Both `verify_answer` and the fidelity rows address blocks by those ids.

## What code checks, what the model decides, and what the model judges

| Done by code (`contract.py`, no model call) | Done by the drafting model | Judged qualitatively by a second model call (`judge.py`) |
|---|---|---|
| splitting the page into blocks, numbers present in the source quote, added absolute/superlative phrasing, a hedge turned into a certainty, which glossed terms are really in the quote | the plain wording of each block, and which terms it glossed | whether a condition, exception, limit, or penalty survived *in meaning* |

The drafting model gets the mandatory-disclosure criteria (`A·B·C` groups of the card guardrail
rubric) as context so it does not drop them, and the previous round's `verification.feedback`
addressed to `generate_plain_lang`. It never gets the rubric's plain-language items: the node
reports on those itself.

`contract.py` holds the checks that are decidable from the two strings alone, so none of them
needs a model call:

- a number in the rewrite that the source quote does not have, or one of its numbers missing
- an absolute or superlative phrase (`누구나`, `무조건`, `최고`, …) the source quote did not use
- a source quote that hedges (`~할 수 있습니다`, `심사 결과에 따라`) rewritten without any hedge

Whether a condition/exception/limit/penalty (`이상`, `제외`, `한도`, `위약금`, `연체`, …)
*survived in meaning* used to be a keyword-presence check in `contract.py`: if the literal word
disappeared from the rewrite, the block was reverted. That punished normal plain-language
rewriting, because several of those words (`하락`, `해지`, `변동`, `설명서`, `책임`, …) are exactly
the jargon `PLAIN_TASK` tells the model to gloss into easier wording — a correct synonym swap and
a real omission look identical to a substring scan. `judge_condition_preservation` (`judge.py`)
replaces that keyword scan with a second model call, given `CONDITION_TASK`'s rules, that reads
the quote/rewrite pair and judges meaning preservation rather than literal survival. It runs once
per generation, batched over every block that already passed the mechanical checks above. A
`판정 불가` (genuinely unclear) verdict is treated as passing, not as a drop — `CONDITION_TASK`
tells the model to prefer `판정 불가` over a confident-sounding `누락 가능` when the evidence is
thin, so defaulting the unclear case to "revert" would recreate the same over-reversion problem
under a different name.

Only the last check (`누락 가능`) is deliberately reported as a guess, not a proven omission: its
cost is that the block falls back to the original wording, same as before.

## What the node reports about the rubric, and what it does not

`plain_items_report` answers per `쉬운말서비스` item, but only as far as this node actually
checked:

| Item | Verdict | Why |
|---|---|---|
| `쉬운말01` | always `판정 불가` | whether a mandatory disclosure survived is `judge_ad_disclosure`'s answer, not this node's |
| `쉬운말08`, `쉬운말10` | `적용` when any term was glossed, else `해당없음` | the node can show `term_refs`, not judge whether a gloss changed the concept |
| `쉬운말11`, `14`, `15`, `17`–`22` | always `판정 불가` | sentence complexity, block ordering, UI elements and pre-publication human review are outside what this node produces |
| the rest | `위반 발견` when a matching contract error fired, else `적용` | the item is mapped to the error markers it corresponds to |

`plain_scope` rather than `knowledge.rubrics.item_scope` decides which items apply, because
`plain_service_rubric` lists its screens under `targets`, not `page_types`.

## Assumptions 영태 has not yet confirmed

- The mapping from rubric item to contract-error marker (`PLAIN_ITEM_ERROR_MARKERS`) is this
  node's reading of each item, not something the rubric states. One remaining side-effect of that
  mapping: `쉬운말06`, `07`, `09` all key off the same `누락 가능` marker, so a single
  `judge_condition_preservation` hit on one block is reported as `위반 발견` on all three items
  even when only one of them is actually about that block's condition. Narrowing this to one
  item per marker is a follow-up, not done here.
- `쉬운말20` is reported as out of scope while its "replace a failed block with the original"
  half is in fact implemented. The reason string says so.
- Condition/exception/limit/penalty preservation moved from a keyword scan to a qualitative
  model judgment (`judge.py`, 2026-09-28) because the keyword scan flagged legitimate synonym
  rewrites of jargon (`하락`→`떨어짐`, `해지`→`그만둠`, …) as omissions and reverted the block —
  directly undoing the plain-language rewrite the node exists to produce. This trades a free,
  deterministic check for a second model call per generation; `eval/cases/plain_contract.json`'s
  `condition_dropped` cases now need a cassette (see `../evaluation.md`) instead of running for
  $0.
