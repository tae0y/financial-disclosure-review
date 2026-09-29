---
ai-generated: true
human-review: false
created: 2026-09-29
---

# reference_cases

Reference cases link a page's evidence cards to published regulator cases (sanctions, supervisory
findings, complaints) that show the same advertising or explanation pattern. Links are report-only:
no judging prompt reads them and they never carry a verdict.

Two entry points share one case source and one BM25 index:

- `knowledge.linking.link_reference_cases(...)` — the linking agent (backlog B3). A bounded tool
  loop in which the model searches, reads and proposes links, and code validates every proposal.
  This is the intended graph step; it is not wired into the graph yet.
- `knowledge.reference.retrieve_reference_cases(...)` — the deterministic retrieval (Stage 2,
  part B, design record `Stage 0 설계 기록.md` §2.3 and §8-13). Kept and exported; its BM25
  scoring is now the agent's `search_cases` tool, and its threshold measurements below are why
  linking moved to an agent.

## Linking agent

```python
def link_reference_cases(
    cards: Sequence[Mapping[str, Any]],
    classification: Mapping[str, Any],
    db_path: str | Path,
    *,
    ctx: Context,
    risk_kinds_path: str | Path | None = None,
    corpus_path: str | Path | None = None,
    embed=None,
    chat=None,
) -> dict[str, Any]:
    ...
```

Returns `{status, reason, method, candidates, links, agent_trace, stop_reason}`: the shape the
report already reads, plus the trace and the stop reason.

- `status`: `건너뜀` (no cards; no model call) | `판정 불가` (case source or risk-kind file
  missing, or the run stopped on its turn limit, budget or a model error before any link) |
  `해당 사례 없음` (no case for the product type, with no model call, or the agent finished
  without a link) | `부분 완료` (links kept from a run that stopped on its turn limit, budget or
  a model error) | `완료` (the agent finished, or hit the link cap, with at least one link).
  Only `finish` or the link cap make a run complete: a run cut short is never read as "no case"
  or as complete (audit 2026-09-29, R5).
- `method`: `{linking: "agent", model, max_turns, searches, reads, cases_from, rerank}`.
- `candidates`: every case any `search_cases` call returned, as `{case_id, score, card_ids}`: its
  best score and the union of the card ids cited in those searches.
- `links`: `{case_id, card_ids, page_quote, case_quote, case_quote_note, same_pattern,
  material_difference, page_only_detectability, page_only_note, official_url, decided_by: "agent"}`.
- `agent_trace`: one entry per tool call, `{turn, tool, args, result, blocked, blocked_reason}`,
  where `result` is exactly what the model saw (capped at 12,000 characters). The same script
  gives the same trace.
- `stop_reason`: `finished` | `max_turns` | `budget_exhausted` | `link_cap` | `model_error`.

### Loop and budget

The model (`ctx.model`, meter label `case_link`) gets an English system prompt and one user
message with the product type and the cards (`id, kind, subject, claim, qualifiers, exceptions,
numbers, quote`). It has `ctx.case_link_max_turns` turns (8 when the field is absent) and may
call several tools per turn. A `BudgetError` from the run meter ends the loop as
`budget_exhausted`; any other model failure ends it as `model_error`. Neither raises, and links
accepted before the stop are kept. The loop also ends once `MAX_LINKS = 5` links are accepted
(`link_cap`).

The system prompt says that a link is a reference ("this page shows the same pattern a regulator
named"), that most cards have no fitting case and linking nothing is a correct outcome, that
`product_basis: 유추` cases come from another sector, that `partial`/`review_required`/
`out_of_scope` detectability means the page alone cannot settle the pattern, and that both
quotes must be exact.

### Tools

Both lookup tools take batches, because gpt-5-mini made one tool call per turn: search, read and
propose then cost three of the eight turns per link, and three of four gold pages ran out of
turns (2026-09-29). `search_cases` accepts up to 4 searches in `queries`, `read_case` up to 3
`case_ids`; a single search or read answers in its old shape, a batch as `{searches: [...]}` or
`{cases: [...]}`.

- `search_cases(query, card_ids=[], risk_kind="", top_k=5, queries=[])`: the deterministic search tool. The
  query is the model's own words plus the cited cards' slot text (claim, qualifiers, exceptions,
  numbers). Scoring is BM25 over the product-type-filtered cases (`issue + mvp_signal + text`,
  Korean character bigrams plus whole number tokens like `"30만원"`/`"16.9%"`), built in memory
  per run with no persisted index. `risk_kind` adds `RISK_KIND_BOOST = 1.0` to cases curated with
  that kind; it ranks and never filters. When `ctx.case_rerank` is on and `case_vectors` exists,
  hits are reordered by embedding cosine (one paid query embedding per search); otherwise BM25
  order stands and `method.rerank` records the fallback. Returns `case_id, record_type,
  product_basis, issue, mvp_signal, page_only_detectability, score` for at most `top_k` (capped
  at 10) cases, never the case text.
- `read_case(case_id="", case_ids=[])`: each case's fields and its `text` split into numbered sentences. For a
  `text_verified: false` case the result says the text may not be quoted.
- `propose_link(case_id, card_ids, page_quote, case_quote, same_pattern, material_difference)`: a
  proposal, validated by code (below).
- `finish(reason)`: ends the loop.

The product type (`classification["product_type"]`, via `load_cases`) is the only hard filter:
cases outside it can be neither searched nor read.

### Validation

A proposal becomes a link only when every check passes. Otherwise the tool result is
`{blocked: true, blocked_reason}` and the model can correct the proposal.

1. Fewer than `MAX_LINKS` links so far.
2. The case was returned by `search_cases` and read with `read_case` in this run.
3. The case is not already linked (one link per case).
4. At least one card id is cited, and every cited card id exists.
5. `page_quote` is found (`core.text.locate_quote`, whitespace-insensitive) in the `quote` of one
   cited card.
6. `case_quote` is found in the case text. For a `text_verified: false` case it must be `""`, and
   the link carries `case_quote_note: "원문 재확인 필요"`.
7. `same_pattern` is non-empty and contains no verdict word (`적합|부적합|위반|합법|불법|문제없`).

On acceptance, code fills in the rest. `material_difference` is the model's items followed by
the deterministic differences from the case's own fields (`product_basis: 유추`, a `record_type`
other than `위반사례`, the case's `product_subtype`), de-duplicated. `page_only_note` is
`"페이지 단독 판단 불가"` for `partial`/`review_required`/`out_of_scope` and empty for `full`.
`official_url` is the case's primary URL.

## Deterministic retrieval

```python
def retrieve_reference_cases(
    cards, classification, db_path, *,
    risk_kinds_path=None, corpus_path=None, embed=None, rerank=False, threshold=None,
) -> dict[str, Any]:
    ...
```

Returns `{status, reason, method, candidates, links}`. Each card is scored against each
product-type-filtered case with four BM25 slot scores (`claim 0.4, qualifier 0.25, exception
0.15, number 0.2`) plus the risk-kind boost for the card's kind (`rate_claim`/`fee_claim` →
`rate_fee`; `benefit_claim`/`eligibility`/`condition`/`exception` → `benefit_condition`;
`warning`/`footnote` → `warning_penalty`). A case scores as its best single card, and becomes a
link when that score reaches `threshold` (`DEFAULT_THRESHOLD = 10.0`). The optional embedding
rerank only reorders links that already cleared the threshold, and never adds or removes one.

## `assets/case_risk_kinds.yaml`

New file, `{ai_drafted: true, human_review: false, cases: {<case_id>: {risk_kinds: [...],
text_verified: bool}}}`, covering all 19 real corpus case IDs. `text_verified: false` is set
only for `case.fss_20260609_revolving_complaint` (per the corpus header comment: its quoted text
was never checked against the source verbatim). The risk-kind assignments themselves are an AI
reading of each case's `issue`/`mvp_signal` text — a curatorial judgment call, not derived from
any ground truth, and flagged `human_review: false` accordingly.

## Deterministic link fields

- `case_quote`: the sentence of the case's `text` with the most bigram overlap with the best
  contributing card's slot text, verified locatable via `core.text.locate_quote` before being
  used. When the case's `text_verified` is `false`, `case_quote` is always `""` and
  `case_quote_note` is `"원문 재확인 필요"` instead — the case is still linked (for the pattern it
  demonstrates and its official URL), but its wording is never quoted as evidence.
- `page_only_note`: `"페이지 단독 판단 불가"` when the case's `page_only_detectability` is
  `partial`, `review_required`, or `out_of_scope`; empty for `full`.
- `material_difference`: a deterministic list built from the case's own fields — flags
  `product_basis: 유추` (사례 대상이 다른 업권), a `record_type` that isn't `위반사례`, the case's
  `product_subtype` (page product identity isn't confirmed to match), and any of the
  qualifier/exception/number slots that scored zero for the linked case (no card evidence for
  that part of the pattern).

## Why linking moved to an agent: threshold measurements

`DEFAULT_THRESHOLD = 10.0`, set by the coordinator on 2026-09-29 against 25 gold cards quoted from
the two real lottecard pages (`eval/fixtures/gold/evidence_cards.json`, local only because
`eval/fixtures/` is gitignored). Three of those cards were judged to share a pattern with a case
(최대 1% 할인 → `crefia_ad_type_unconditional_discount`; 무이자할부 등 할인 제외 대상 →
`fss_20241007_interest_free_benefit_exclusion`; 혜택 제공조건·한도 → `fss_20241007_addon_limit_restore`).

| threshold | expected links found | false links | cards with any link |
|---|---|---|---|
| 4 | 3/3 | 18 | 15 |
| 6 | 1/3 | 3 | 3 |
| 8 | 0/3 | 1 | 1 |
| 10 | 0/3 | 0 | 0 |

Normalizing by query length, word tokens instead of bigrams, and scoring only `issue`+`mvp_signal`
were also tried; none separated the three positives from the negatives. Lexical overlap with 19
short case summaries mostly measures shared financial vocabulary. The default therefore favours no
link over a wrong one, which is the conservative reading of the design (cases are report-only and
a weak link is not shown). Choosing a better signal — a curated card-pattern → case table, or a
narrow model judgment over the few top candidates — was left for a person to decide. The
person chose the model judgment: the linking agent above keeps BM25 as its search tool and
replaces the threshold with a validated proposal.

`tests/fixtures/reference_links.synthetic.json` (built by the implementing agent from the test
corpus, each card paraphrasing its own case) is kept only as a ranking self-consistency check at
threshold 1.5.

## Case source

Both `link_reference_cases` and `retrieve_reference_cases` (given `corpus_path`) read the cases
from the DB when its case tables exist, otherwise straight from `assets/case_corpus.yaml` (validated with `case_schema_problems`, no
embedding). BM25 needs only the case text, and building the DB tables embeds every case, a paid
step. `method.cases_from` records which source was used.

## Covering the page (added after B4 round 1, 2026-09-29)

The first gold run scored 3/14 recall and 3/6 false links: the agent often searched once, read
nothing and finished. Two changes followed. The first `finish` is sent back once when a concrete
card (`rate_claim`, `fee_claim`, `benefit_claim`, `eligibility`, `condition`, `exception`,
`warning`) was never cited in a search, or when nothing was read; the reply lists the
unsearched card ids. A second `finish` always stops. The prompt now also says a card that states
a condition, rate or risk clearly is not a link to a case about hiding or omitting it.

