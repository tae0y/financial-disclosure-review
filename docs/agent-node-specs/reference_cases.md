---
ai-generated: true
human-review: false
created: 2026-09-29
---

# reference_cases

`knowledge.reference.retrieve_reference_cases(cards, classification, db_path, ...)` is the
deterministic reference-case retrieval this doc specifies (Stage 2, part B of the agentic
design; see `Stage 0 설계 기록.md` §2.3 and §8-13 for the design record this implements). It is
not wired into the graph yet — see "What still needs wiring" below.

## Signature and return shape

```python
def retrieve_reference_cases(
    cards: Sequence[Mapping[str, Any]],
    classification: Mapping[str, Any],
    db_path: str | Path,
    *,
    risk_kinds_path: str | Path | None = None,
    embed=None,
    rerank: bool = False,
    threshold: float | None = None,
) -> dict[str, Any]:
    ...
```

Returns `{status, reason, method, candidates, links}`:

- `status`: `건너뜀` (no cards, DB never touched) | `판정 불가` (case DB or risk-kind file
  missing/unbuilt) | `해당 사례 없음` (product type has no cases, or nothing cleared the
  threshold) | `완료`.
- `method`: `{candidate, score, rerank, threshold, threshold_source}` — a record of exactly how
  the result was produced, for the report's version/method section.
- `candidates`: every case whose `product_types` include `classification["product_type"]` (the
  hard filter, via `knowledge.cases.load_cases`) that any card scored above zero on. Each entry:
  `{case_id, risk_kinds, bm25, slots: {claim, qualifier, exception, number}, boost, embedding,
  final, card_ids}`.
- `links`: one entry per candidate whose `final` score is `>= threshold`, sorted by score (by
  `embedding` when `rerank=True`, else by `final`). Each entry: `{case_id, card_ids, page_quote,
  case_quote, case_quote_note, same_pattern, material_difference, page_only_detectability,
  page_only_note, official_url}`. Links never carry a compliance verdict.

## Ranking

1. **Hard filter**: `classification["product_type"]`, via `load_cases(db_path,
   product_types=(product_type,))`. Nothing outside this set is ever scored, regardless of text
   overlap.
2. **BM25 slot overlap**: for each candidate case and each contributing card, four separate BM25
   scores are computed — the card's `claim`, `qualifiers`, `exceptions`, and `numbers` against
   the case document (`issue + mvp_signal + text`, tokenized as Korean character bigrams plus
   whole number tokens like `"30만원"`/`"16.9%"`). They combine with fixed weights (`claim
   0.4, qualifier 0.25, exception 0.15, number 0.2`). This BM25 index is built in memory from
   whatever `load_cases` returned for this call — no DB rebuild, no persisted index.
3. **Risk-kind boost**: a card's `kind` maps to one of three fixed risk kinds
   (`rate_claim`/`fee_claim` → `rate_fee`; `benefit_claim`/`eligibility`/`condition`/`exception`
   → `benefit_condition`; `warning`/`footnote` → `warning_penalty`). If that risk kind is in the
   case's curated `risk_kinds` (`assets/case_risk_kinds.yaml`), the case gets a flat
   `RISK_KIND_BOOST = 1.0` added to its score for that card. This is purely a ranking signal —
   `assets/case_corpus.yaml` is never edited (that would need a paid embedding rebuild), and the
   product-type filter above is the only hard filter.
4. **Threshold**: `final = bm25 (sum of weighted slot scores across contributing cards) + boost
   (max over contributing cards)`, rounded to 6 decimals. A case becomes a link only if
   `final >= threshold`.
5. **Optional embedding rerank** (`rerank=True`, off by default): for each already-kept
   candidate, its best-scoring card's slot text is embedded and searched against the existing
   `case_vectors` KNN index (`knowledge.search.search`). The cosine similarity becomes
   `candidates[i]["embedding"]`, and `links` is re-sorted by it. This step **never adds or
   removes a candidate** — it only reorders what the BM25+boost stage already kept. If
   `case_vectors` is unavailable, the order silently falls back to `final` and `method["rerank"]`
   records that fallback.

## `assets/case_risk_kinds.yaml`

New file, `{ai_drafted: true, human_review: false, cases: {<case_id>: {risk_kinds: [...],
text_verified: bool}}}`, covering all 19 real corpus case IDs. `text_verified: false` is set
only for `case.fss_20260609_revolving_complaint` (per the corpus header comment: its quoted text
was never checked against the source verbatim). The risk-kind assignments themselves are an AI
reading of each case's `issue`/`mvp_signal` text — a curatorial judgment call, not derived from
any ground truth, and flagged `human_review: false` accordingly.

## Link fields worth calling out

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

## Threshold derivation

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
narrow model judgment over the few top candidates — is left for a person to decide.

`tests/fixtures/reference_links.synthetic.json` (built by the implementing agent from the test
corpus, each card paraphrasing its own case) is kept only as a ranking self-consistency check at
threshold 1.5.

## Case source

`retrieve_reference_cases(..., corpus_path=...)` reads the cases from the DB when its case tables
exist, otherwise straight from `assets/case_corpus.yaml` (validated with `case_schema_problems`, no
embedding). BM25 needs only the case text, and building the DB tables embeds every case, a paid
step. `method.cases_from` records which source was used.
