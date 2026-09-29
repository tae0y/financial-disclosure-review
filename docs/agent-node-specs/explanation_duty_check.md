---
ai-generated: true
human-review: false
created: 2026-09-27
---

# explanation_duty_check

`judge_explanation_duty` judges the explanation-duty criteria twice — once against the original
page, once against the plain-language rewrite — and records where the two answers differ. The
original side reads only the page, so on a first round `judge_explanation_original` judges it in
the same graph step as the persona explanation and `judge_explanation_duty` reuses those rows;
without them (a rerun from an older checkpoint) it judges the original side itself. A judgment
whose check rejects only some codes asks again for those codes alone and merges the answer. The
input is a public 상품광고/업무광고 page, not a 청약 단계 설명화면, so every criterion here is
applied by analogy (준용), per [Rubrics and scope](../README.md#rubrics-and-scope).

## Two rubrics, one code axis each

`load_explanation_items` reads the `설명의무` group of `plain_service_rubric` and the `F` group of
`card_guardrail_rubric` and keeps both, each with its own codes and its own `rubric` field. The
two lists carry the same duties on different code axes; merging them would lose the citation, so
each code is judged independently. A code appearing in both files raises.

## What code rules out and what the model decides

| Done by code | Done by the model |
|---|---|
| `applies_to` mismatch, an `applies_condition` that only ever holds on a 신청·가입·발급 화면, reusing the original side on a retry, picking the fidelity candidates, checking every quote against the real text | whether a remaining condition holds, the verdict per criterion, and how the two sides differ |

`explanation_scope` excludes an item without a model call in two cases:

- `product_type` is not in the item's `applies_to`.
- the item's `applies_condition` names a 신청 화면, 가입 화면 or 발급 화면. This graph's input can
  never be one of those screens, so the condition cannot hold.

A `targets`/`page_types` value of 설명화면 or 권유·설명화면 is **not** an exclusion by itself —
that is exactly what 준용 means here.

## Condition, then criterion

The model answers `condition_status` before `verdict`. `불명확` is a first-class answer: when the
page does not say whether the condition holds, the item stays `applied: true` with
`condition_status: 불명확`, `verdict: 판정 불가` and no quote, and the same row is reused on the
plain side without a second call. Only `불성립` drops an item out of `original`.

`_quote_ok` rejects a `적합` with no quote and any quote that cannot be located in the text it was
supposed to come from. A second answer that still fails is salvaged row by row — only the named
codes are downgraded to `판정 불가`; a mismatch in the set of codes raises.

## Fidelity

`fidelity_candidates` sends to the model only the codes whose verdict or quote differs between
the two sides, and `변화없음` answers are dropped from the result. `추가` is not a fix: the task
text says outright that a plain-language rewrite filling a gap the original left does not resolve
the original's `부적합`.

Each returned row now carries both quotes (`original_quote`, and `quote` from the explanation
side). `ledger.map_rubric_fidelity` ties the row to persona units: a unit matches when the
explanation-side quote lies in the unit's text, or the original-side quote overlaps the unit's
`exact_fact` (whitespace-insensitive containment either way, at least 6 characters). A row tied
to an accepted unit gets that unit's `source_ids` and `informational: false`, so
`verify_answer` fails `persona_explanation` and the retry regenerates that unit. A row tied to
no unit, or only to reverted units, or whose kind is `판정 불가`, stays informational. This closes
the 2026-09-29 live-run gap where 설명06 (the explanation changed a warning's cause from 사용액
과다 to 다수의 카드 발급) passed because rubric rows had no source line; replayed on that
checkpoint, 설명06 maps to unit `u21`.

## Fact ledger scope

`check_ledger` checks each fact inside its own scope: the text (`exact_fact`, `explanation`,
`analogy`) of its accepted units. A fact none of whose units was accepted is shown in its original
line, so its scope is the whole explanation page. The model call (`LedgerSemantics`) receives each
pending fact's `scope_text` and must quote from it. Before this, the page-wide check let a value
dropped from one unit count as preserved when another line repeated it (LOCA ledger mutations:
1/4 detected).

## Retry

When the node is called again with the previous `items` and `original`, it reuses both and
recomputes only `plain` and `fidelity`. The original page did not change, so re-judging it would
spend money to produce a possibly different answer. `tests/domain/explanation_duty_check/`
asserts that no `ExplanationJudgments` call is made on that path.
