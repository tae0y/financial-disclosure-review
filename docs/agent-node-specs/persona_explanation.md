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
| `profile` | the result of `choose_profile` (see below), used as is; a retry keeps the same reader |
| profile fallback | without `profile`: `profile_id`, else `Context.persona_profile`, else the yaml's `default` |

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

A profile is chosen once per review by `choose_profile(ctx, *, product_type, cards, data_dir,
rubric_dir, chat=None, ask=None) -> {profile, selection}` (in `selection.py`). The graph node is
expected to call it once, store both results in State, and pass `profile` to
`generate_persona_explanation(..., profile=...)`, which then uses it without re-resolving.

Every profile has the shape `{id, version, source, review_status, status: 적용 | 무효, reason,
attributes}`. `attributes` holds `reading_preference`, `financial_familiarity` (낮음/보통/높음),
3–5 `likely_questions`, `prohibited_assumptions`, `analogy_policy` (`none` or `benefit_only`) and,
for dataset profiles, `reader`.

### Dataset: pinned, downloaded once

The full `nvidia/Nemotron-Personas-Korea` dataset (CC-BY-4.0, 1,000,000 synthetic rows) is used
from local disk. `dataset.py` pins revision `ada0f5b53a38bb5a30cce09358adde883c1ab63a` and the
sha256 of each of its 9 parquet shards (`data/train-0000N-of-00009.parquet`, about 220MB each).

- Location: `<data_dir>/personas/<revision>/train-0000N-of-00009.parquet` (`dataset_dir`).
- `python -m financial_disclosure_review fetch-personas [--data-dir] [--if-missing]` downloads
  every missing or hash-mismatched shard to `<shard>.part`, verifies the sha256, then renames it.
  A failed shard is reported and leaves no file; the command exits 1. `--if-missing` returns at
  once when every shard file exists (existence only; hashing 2GB is left to a full run).
- Docker: `docker/entrypoint-agent.sh` runs `fetch-personas --if-missing` into the data volume on
  every boot, so only the first boot downloads. A failed download is a warning; the node then
  uses the fallback below.
- Nothing is downloaded while a review runs. `PersonaStore` reads the shards with DuckDB
  (`read_parquet` over the folder); every query is parameterized.

### Selection precedence

`select_persona(request, ctx, *, product_type, cards_summary, store, chat=None, ask=None)`
returns `{uuid, decided_by, filters, match_count, seed, stop_reason, trace, reason}`.

1. `Context.persona_uuid` names one row → `decided_by: uuid`. An unknown uuid falls to the
   product-type defaults with `decided_by: fallback` and the reason.
2. `Context.persona_attributes` (a `Filters` dict) → validated, then code picks → `attributes`.
   Unknown keys or values outside the dataset vocabulary fall to the defaults (`fallback`).
3. `Context.persona_request` (free text, e.g. "70대 은퇴자, 카드론을 처음 알아보는 사람") → the
   tool loop below → `agent`.
4. Nothing given → `default`: the product type's `default_filters` from
   `assets/persona_template.yaml` (신용카드 and unknown types: age 20+; 장기카드대출,
   단기카드대출, 리볼빙, 할부금융·리스: ages 30–59).

`Filters` fields are restricted to real columns: `age_min`, `age_max`, `sex`,
`education_level[]`, `occupation_contains[]` (1–2 substrings, a row matches any one),
`province[]`, `family_type[]`, `housing_type[]`, `marital_status[]`. `validate_filters` rejects
any value that is not in the dataset's own vocabulary (and occupation substrings that match no
occupation), so neither a model nor a caller can filter on something the dataset does not hold.

The row is picked by code: `ORDER BY md5(uuid || seed)` over the matching rows, with the fixed
seed `fdr-persona-v1`, so a rerun picks the same person for the same filters.

When filters match no row, `relax` drops them one at a time in the fixed order
`occupation_contains, housing_type, family_type, marital_status, province, education_level, sex,
age` until at least one row matches. Each drop is a `{"step": "relax"}` trace entry, the reason
lists the dropped filters, and `decided_by` becomes `fallback`.

### The selection tool loop

Free text goes through one `ToolChat` conversation (meter label `persona_select`, at most 6 model
turns), in the style of the product-page discovery loop:

- `list_values(field)`: the 30 most frequent values of a categorical field with row counts.
- `count_matches(filters)`: rows matching the filters.
- `choose(filters, rationale)`: final filters; refused when a value is invalid or nothing matches.

Code validates every call; an invalid call comes back `refused` with the reason and is traced
(`{turn, tool, args, result, refused, reason}`). The model sees the request, the product type
and up to 15 `kind: subject` lines of the page's cards; it never sees rows and never picks the
person. Stop reasons:

| stop_reason | When | Then |
|---|---|---|
| `chosen` | an accepted `choose` | code picks from those filters (`agent`) |
| `no_match` | a second `choose` that matches nothing | relax the last proposed filters |
| `max_turns` | 6 turns without an accepted `choose` | relax the last validated filters, else the defaults |
| `budget_exhausted` | `BudgetError` from the run meter | same; the error never propagates |
| `model_error` | any other model or network failure, or the chat cannot be built | same |
| `no_model` | `ask` given without `chat` (an offline run) | defaults; no model call |

### Template: derived reading profile

`template.py` derives the profile from the chosen row by fixed rules in
`assets/persona_template.yaml` (`version`, `ai_drafted: true`, `human_review: false`):

- `financial_familiarity`: 높음 when the occupation contains a finance term (금융, 회계, 보험,
  은행, 증권, 세무, 재무, 투자, 대출, 신용, 경리); else 낮음 when `education_level` is 무학,
  초등학교 or 중학교, or age is 70+; else 보통.
- `reading_preference` and `analogy_policy` by familiarity (높음 → `none`, else `benefit_only`).
- `likely_questions`: 3–5 per product type × familiarity (`default` for unknown types).
- `prohibited_assumptions`: one fixed list for every reader.
- `reader`: `"{age}세 {sex} · 학력 {education_level} · 직업 {occupation} · {province} 거주 ·
  가구 {family_type}"`, a newline, then the row's `persona` sentence verbatim (CC-BY data).

`resolve_dataset_profile(row, product_type, template_path)` returns id `nemotron:<uuid>`,
version `t<TEMPLATE_VERSION>@<revision[:7]>`, source `nvidia/Nemotron-Personas-Korea rev=<7>
uuid=<uuid> (CC-BY-4.0)` and `review_status: ai-drafted`. `TEMPLATE_VERSION` pins the template
file the way `PROFILE_ALLOWLIST` pins the yaml profiles: a file of another version, a schema
error, an unreadable file or a row without a proper uuid gives a `무효` profile, and the node then
makes no model call and keeps every line original.

The prompt passes `profile.reader` and tells the model to use it only for register, wording
level and examples. The forbidden-assumption rules still apply: the reader sketch is never
grounds for the reader's eligibility, income, credit or whether the product suits them.

### Fallback: checked-in profiles

When any pinned shard file is missing, when DuckDB cannot read the shards, or when no row can be
picked, `choose_profile` uses the legacy profile (`Context.persona_profile`, else the yaml's
`default`) with `selection.decided_by: fallback` and a Korean reason (`페르소나 데이터셋 없음: …`
or `페르소나 데이터셋을 읽을 수 없음: …`). `Context.persona_profile` is consulted only here.

`assets/persona_profiles.yaml` holds three AI-drafted profiles, each derived from one row
(pinned by uuid) of the dataset. Only derived reading attributes are stored. `PROFILE_ALLOWLIST`
in `profiles.py` pins `{id: version}`. An unknown id, a version mismatch, a duplicated id, a
schema error or an unreadable file makes the profile `무효`.

| id | source uuid | familiarity | analogy policy |
|---|---|---|---|
| `nemotron-ko-70s-lowfin` (default) | `766224c2c1dd49dda886d82e67b917f9` | 낮음 | `benefit_only` |
| `nemotron-ko-20s-firstcard` | `a83e31fb286640f9b86e922c29c34d1f` | 보통 | `benefit_only` |
| `nemotron-ko-40s-loanfamiliar` | `2c30571d3af64e19baac9135d37c31f6` | 높음 | `none` |

### Provisional: selection from user input

How a reviewer's wish becomes a reader is an open design question. The tool loop above is a
first version, kept small and fully validated so it can be replaced. Alternatives considered:

- Questionnaire → attributes: a short form (age band, schooling, occupation group, region)
  maps straight to `persona_attributes`; no model call, fully reproducible.
- Reviewer picks from a shortlist: code draws 3–5 rows for the product-type defaults and the
  reviewer picks one uuid (`persona_uuid`); the choice is a human decision on record.
- Page-driven target reader: derive the filters from the page's own stated target (e.g. an age
  or occupation condition in an eligibility card), with the reviewer's text only as a tiebreak.
- Several readers per page: explain for 2–3 contrasting rows (low and high familiarity) and
  report the differences, at 2–3 times the drafting cost.

CLI: `review --persona "<free text>"`, `--persona-uuid <uuid>`, `--persona-attr key=value`
(repeatable; list fields take comma-separated values, e.g. `province=서울,경기`).

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

## Familiarity stated by the reviewer

A reader's familiarity with finance is not a dataset field. When the free-text request states it
("리볼빙을 처음 알아보는" → 낮음, "금융권 종사자" → 높음), the selection agent passes it as
`choose.familiarity_hint`; `derive_profile` then uses it instead of the row-based estimate and
records `familiarity_source: request` (else `row`). Added after the 2026-09-29 F1 run where the
agent added an occupation filter the request never named, drew a 회계 사무원, and the row rule
made a first-time revolving reader 높음. The prompt now also forbids occupation filters the
request does not name.

## HTML

Every source appears once, in page order. The first source (in page order) of each accepted unit
is replaced by `<section data-unit-id data-source-ids><p data-role="exact-fact">…</p>
<p data-role="explanation">…</p>[<p data-role="analogy">…</p>]</section>`; every other source,
including the unit's other sources, stays `<p data-source-id>original</p>`. All text is escaped.

Mandatory disclosures stay emphasised (audit P2-12). The graph node flags a source `mandatory`
when its text contains, or is contained in, a block `display_check` labelled `mandatory` (at least
6 normalised characters). Such a line renders as `<p data-source-id data-mandatory="true">
<strong>…</strong></p>`, and a unit covering a mandatory line carries `data-mandatory="true"` with
its `exact_fact` in `<strong>`. The emphasis is markup only; it adds no text, so the ledger and
fidelity checks read the same words.

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
- Persona selection (dataset, precedence, tool loop, template rules, default filters) is
  provisional; see "Provisional: selection from user input".
