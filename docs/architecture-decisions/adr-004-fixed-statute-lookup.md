---
ai-generated: true
human-review: false
created: 2026-09-28
---

# ADR-004 — Look statutes up through a fixed mapping; search only sanction cases by similarity

- **Status:** Accepted 2026-09-17
- **Recorded here:** 2026-09-28, from the case-search implementation notes and
  [Rubrics and scope](../README.md#rubrics-and-scope) (since superseded by this ADR) and the study
  `관련자료/260917 법률 조회 로직 Graph(GraphRAG) 적용 가능성 조사.md` (종합 의견).

## Context

The riskiest thing a legal-review tool can do is cite a provision that does not exist or does not
apply. The corpus is small and already structured: 17 source documents, 141 rubric items with
their article locations and verbatim quotes. The yaml the app reads is `assets/`; the authoring
trail — source snapshots with URL and SHA-256 (`manifest.csv`), comparison tables and the quote-check
scripts — is kept in the project folder `05 법령·지침 원문 검증/카드사 가드레일 루브릭/`, one level up
from this repository.
The questions asked of it are point lookups — which items apply to this product and page type.

## Decision

- Statutes and rubric items are never retrieved by a model or by similarity. Code selects them
  from the SQLite reference DB by product type and page type (`knowledge/rubrics.py`).
- Only sanction and dispute cases (19, `case_corpus.yaml`) are embedded and searched with
  sqlite-vec, because "a case like this one" is a similarity question.

## Alternatives considered

| Alternative | Why not |
|---|---|
| RAG over statute chunks | Chunking flattens the delegation between 법·시행령·감독규정 and lets the model cite what it retrieved rather than what applies. |
| GraphRAG / graph DB | Built for discovering structure in million-token corpora; here the structure is known and the corpus is ~140 items of point lookups. Cost (schema, loading, rewrites) with no measured accuracy gain at this size. |
| Model chooses the provisions | The hallucinated-citation risk this decision exists to remove. |

## Consequences

- A provision reaches a judgment only through the DB, so every cited item has a verbatim source
  that the rubric check scripts matched against the snapshots (184/184 and 146/146 quotes).
- Changing the rubric means rebuilding the DB (`build-db`) and re-recording evaluations whose
  prompts change.
- Retrieved cases are shown to the reviewer as context; they do not decide a verdict.
