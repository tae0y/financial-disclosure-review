---
ai-generated: true
human-review: false
created: 2026-09-28
updated: 2026-09-30
---

# ADR-004 — Look up statutes through a fixed mapping, not retrieval

- **Status:** Accepted, 2026-09-17

## Context

The riskiest thing a legal-review tool can do is cite a provision that does not exist or does not apply. The corpus is small and already structured: 141 rubric items from 17 source documents, each with its article location and a verbatim quote. The questions asked of it are point lookups: which items apply to this product type and page type.

## Decision

Statutes and rubric items are never retrieved by a model or by similarity. Code selects them from the SQLite reference DB by product type and page type (`knowledge/rubrics.py`).

## Alternatives considered

| Alternative | Why not |
|---|---|
| RAG over statute chunks | Chunking flattens the delegation between 법·시행령·감독규정 and lets the model cite what it retrieved rather than what applies. |
| GraphRAG or a graph DB | Built to discover structure in large corpora; here the structure is known and the lookups are exact. Cost with no accuracy gain at this size. |
| The model chooses the provisions | The hallucinated-citation risk this decision exists to remove. |

## Consequences

- A provision reaches a judgment only through the DB, so every cited item has a verbatim source.
- Changing a rubric means editing `assets/*.yaml`, rebuilding the DB (`build-db`), and re-recording the evaluations whose prompts change.
- Supporting another financial sector means authoring its rubric by hand; the lookup code does not change.
