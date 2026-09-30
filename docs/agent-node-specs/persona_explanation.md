---
ai-generated: true
human-review: false
created: 2026-09-29
updated: 2026-09-30
---

# Reader Advice (`generate_persona_explanation`)

This page describes how `generate_persona_explanation` chooses one reader and writes the reader advice (쉬운말 확인 권고).

The advice is one paragraph shown beside the page. It tells the reader which 설명의무 items the ad does not explain and that they should check in the product document or with a consultant before signing, and why each matters to them. It names what to ask, never the answer, and it issues no compliance verdict ([ADR-007](../architecture-decisions/adr-007-advice-only.md)).

## Input and output

| | Content |
|---|---|
| Reads | `evidence_cards` (every source line and card), `classification`, `verification.feedback` for this module |
| Writes | `persona_explanation`: `{status, reason, profile, advice, advice_codes, problems, html, controls, selection}` |
| Model use | reader-selection agent (only for free-text input), then one drafting call |

| `status` | When |
|---|---|
| `완료` | the advice passed its code checks and is shown |
| `원문 대체` | invalid profile, no checklist for the product type, or a draft that failed its checks twice; only the original page is shown |
| `판정 불가` | no source lines at all |

A held-back draft stays in `advice` with its `problems`, so a reviewer can see it. `html` is `<section data-role="advice">` when shown, else empty.

## Choosing the reader

The reader comes from `nvidia/Nemotron-Personas-Korea` (CC-BY-4.0, 1,000,000 synthetic rows), pinned to one revision with a sha256 per shard. `fetch-personas` downloads it once (about 2 GB); nothing is downloaded during a review. DuckDB reads the shards with parameterized queries.

Input precedence, from the API's `persona` object ([API](../api.md)):

1. `uuid` names one row → `decided_by: uuid`.
1. `attributes` (dataset filters) → validated, then code picks a row → `attributes`.
1. `request` (free text) → the selection agent below → `agent`.
1. Nothing given → the product type's default filters → `default`.

Filters are limited to real dataset columns (age range, sex, education, occupation substring, province, family type, housing type, marital status), and every value must exist in the dataset vocabulary. Code picks the row deterministically (`ORDER BY md5(uuid || seed)`), so the same filters always give the same person. When filters match nothing, they are dropped one at a time in a fixed order and `decided_by` becomes `fallback`. An unknown uuid or invalid filter also falls back; the job never fails for it.

**Selection agent.** Free text goes to a tool loop of at most 6 turns with three tools: `list_values(field)`, `count_matches(filters)` and `choose(filters, rationale)`. Code validates every call. The model never sees rows and never picks the person. It may pass a familiarity hint when the request states one ("처음 알아보는" → 낮음, "금융권 종사자" → 높음), and it may not add occupation filters the request does not name.

| `stop_reason` | Then |
|---|---|
| `chosen` | code picks from the accepted filters |
| `no_match`, `max_turns` | relax the last valid filters, else use the defaults |
| `budget_exhausted`, `model_error` | same; the error never propagates |
| `no_model` | defaults, no model call |

**Reading profile.** Fixed rules in `assets/persona_template.yaml` derive the profile from the row: financial familiarity (높음 for a finance occupation; 낮음 for little schooling or age 70+; else 보통, unless the request stated it), reading preference, analogy policy, 3–5 likely questions, and a fixed list of prohibited assumptions. The reader sketch shapes wording only; it is never grounds for eligibility, income, credit or suitability.

If the dataset is missing or unreadable, one of three checked-in profiles in `assets/persona_profiles.yaml` is used (default `nemotron-ko-70s-lowfin`) and the reason is recorded.

## Drafting the advice

The model gets the product type, the reader profile, every page line (so it does not recommend what the page already explains), the cards, and the product type's 설명의무 checklist (the same `deferred` list the ad-disclosure check produces). It picks 2–5 items that the page does not explain and that matter to this reader, names them in plain words, and says why.

Code then checks the draft:

- one non-empty paragraph of at most 700 characters;
- 2–5 `advice_codes`, each from the checklist;
- no rubric code in the text (`설명16`, `A04`, ...);
- no number that is not on the page;
- no absolute or superlative phrase the page lacks, and no verdict word (적합, 부적합, 위반, 합법, 불법, 문제없).

A failing draft is asked again once with the problems. A second failure is held back (`원문 대체`), and verification sends its `problems` back as the request for the next round. A retry keeps the same reader.

## Limits and assumptions

- Reader selection from free text is a first version. Alternatives under consideration: a short questionnaire, a reviewer picking from a shortlist, filters from the page's own target reader, and advice for several contrasting readers.
- The 700-character cap and the 2–5 item range are this node's reading of "one paragraph".
- Verdict words are rejected even when the page uses them; a false hold-back only costs the advice for that round.
- No person has yet scored whether the advice suits its reader.

Tests: `tests/domain/persona_explanation/`.
