---
ai-generated: true
human-review: false
created: 2026-09-29
---

# persona_explanation

`generate_persona_explanation` writes a supplementary explanation of the page's evidence cards
for one reviewed reader profile. It is not a legal rewrite and issues no compliance verdict. The
model drafts units; code keeps only the units it can trace back to the page, and every other
line stays in its original wording. `check_ledger` (in `explanation_duty_check/ledger.py`) then
compares the fact ledger against the assembled explanation.

## Inputs and output

| Input | Shape |
|---|---|
| `sources` | `[{source_id: "dom-N", text, visibility}]` in page order (from `evidence_cards`) |
| `cards` | `[{id, kind, subject, claim, qualifiers, exceptions, numbers, quote, source_id, visibility}]` |
| `feedback` | verification entries; only `module == "persona_explanation"` reaches the prompt |
| profile | `profile_id`, else `Context.persona_profile`, else the yaml's `default` |

The result is `{status, reason, profile, fact_ledger, units, html, controls}`.

- `status`: `완료` (at least one unit accepted), `원문 대체` (invalid profile, no cards, or every
  unit reverted), `판정 불가` (no sources at all).
- `profile`: `{id, version, source, review_status, status: 적용 | 무효, reason, attributes}`.
- `fact_ledger`: `[{fact_id, card_id, source_id, kind, value, unit_ids}]`.
- `units`: `[{unit_id, card_ids, source_ids, replaces, exact_fact, explanation, analogy,
  persona_question_answered, status: accepted | reverted, problems}]`.
- `controls`: a static list of UI controls (AI 생성 고지, 원문 보기 전환, 오류 신고) and governance
  controls (사람 승인, 변경 관리, 프로필 검토). They are documented for the report, not judged.

## Profiles

`assets/persona_profiles.yaml` holds three AI-drafted profiles, each derived from one row
(pinned by uuid) of the local `nvidia/Nemotron-Personas-Korea` sample (CC-BY-4.0). Only derived
reading attributes are stored: reading preference, financial familiarity, 3–5 likely questions,
prohibited assumptions and an analogy policy (`none` or `benefit_only`). `PROFILE_ALLOWLIST` in
`profiles.py` pins `{id: version}`. An unknown id, a version mismatch, a duplicated id, a schema
error or an unreadable file makes the profile `무효`; the node then makes no model call and keeps
every line original. Nothing is downloaded at request time.

| id | source uuid | familiarity | analogy policy |
|---|---|---|---|
| `nemotron-ko-70s-lowfin` (default) | `766224c2c1dd49dda886d82e67b917f9` | 낮음 | `benefit_only` |
| `nemotron-ko-20s-firstcard` | `a83e31fb286640f9b86e922c29c34d1f` | 보통 | `benefit_only` |
| `nemotron-ko-40s-loanfamiliar` | `2c30571d3af64e19baac9135d37c31f6` | 높음 | `none` |

## Fact ledger

`build_fact_ledger(cards)` is pure code. Per card, in card order: each `numbers` string becomes
`period` (unit 개월·년·일·주·회차·시간·영업일), `limit` (최대 or 한도 within 4 characters before, or
한도 right after) or `number`; each qualifier becomes `condition`; each exception becomes
`exception`; an `eligibility` card adds a `target` (its claim when literally in the quote, else
the quote); a `warning` card adds a `penalty` holding its quote. Values are literal source
strings, never normalised numbers.

## What code checks per unit

A unit that fails any check is `reverted`: its draft stays in `units` for audit, but the page
shows the original line.

- `card_ids` non-empty and known; `source_ids` non-empty, known, and a subset of the cited cards'
  sources.
- `exact_fact` locatable (whitespace-insensitive) in the joined text of the unit's sources.
- No number in `explanation`/`analogy` that the unit's source text lacks (`number_set`, minus the
  `counter_ones` exception shared with `plain_language`).
- Every ledger value of the cited cards, and of every card on the line the unit replaces, is in
  `exact_fact` or `explanation` (whitespace-normalised substring).
- No absolute/superlative phrase the source lacks (`has_phrase`); no verdict word
  (적합|부적합|위반|합법|불법|문제없) in `explanation`/`analogy`.
- Two units may not replace the same line; the later one is reverted.

Analogies are dropped, not reverted, and the drop is recorded as `analogy_dropped: <why>`: when
the profile's policy is `none`, when a cited card is `rate_claim`/`fee_claim`/`warning`, when the
unit's text mentions 리볼빙|금리|이자|연체|위약금|수수료|이월, or when the policy is `benefit_only` and
a cited card is not a `benefit_claim`. The drop happens before the number/phrase checks, so a
risky analogy never reverts an otherwise sound unit.

The model call goes through `call_ask`. Only structural problems (no units, empty fields, ids
that do not exist) trigger the single retry; a second broken answer is kept as is and the unit
checks revert what cannot be traced, so the graph never stops here.

## HTML

Every source appears once, in page order. The first source (in page order) of each accepted unit
is replaced by `<section data-unit-id data-source-ids><p data-role="exact-fact">…</p>
<p data-role="explanation">…</p>[<p data-role="analogy">…</p>]</section>`; every other source,
including the unit's other sources, stays `<p data-source-id>original</p>`. All text is escaped.

## check_ledger

`check_ledger(fact_ledger, units, original_text, explanation_text, model, ask)` returns
`{"ledger": rows, "fidelity": rows}`.

- A value literally present in `explanation_text` is `보존`, `decided_by: code`.
- All absent values go to one model call (`LedgerSemantics`: `보존 | 누락 | 약화`, with a quote
  that must be locatable in the explanation unless `누락`). A broken answer is retried once, then
  salvaged to `판정 불가`; it never raises.
- A number in the explanation that the original lacks is a code-decided `추가` row (`code: NUM`).
- Fidelity rows: `{code, kind: 누락 | 약화 | 추가 | 판정 불가, source_ids, unit_ids, quote, reason,
  decided_by, informational}`. `source_ids` is never empty (fact source, else its units' sources,
  else `unmapped`). `informational` is true when every related unit was reverted (or there is
  none) — the reader then sees the original line; an added number with no owning unit is not
  informational.

## Decisions taken without a reviewer

- Required ledger coverage extends to every card on the replaced line, not only the cited ones,
  because the section hides that whole line.
- Verdict words are rejected even when the source uses them (e.g. 약관 위반): a false revert only
  costs the original wording.
- `benefit_only` allows an analogy only when all cited cards are `benefit_claim`.
- Non-card text on a replaced line is not checked: an `exact_fact` shorter than its line can drop
  it. The design example itself uses a partial `exact_fact`, so the node does not require the
  whole line; Stage 4 evaluation should measure this.
- The default profiles path is `default_rubric_dir()/persona_profiles.yaml`. The Docker image
  mounts rubrics at `/app/rubrics`, so the graph node has to pass `profiles_path` from
  `serving.settings.rubric_dir` (or `Context` needs a path field) before this runs in Docker.
