---
ai-generated: true
human-review: false
created: 2026-09-28
updated: 2026-09-30
---

# ADR-001 — Organize the code as one package module per State key

- **Status:** Accepted, 2026-09-27

## Context

A review passes through eight judging and reporting steps that share helpers but must not share decisions. Free checks have to run on their own, separate from checks that spend money on model calls.

## Decision

- `src/financial_disclosure_review/` has one folder under `domain/` per State key, shared helpers in `core/`, model calls in `llm/`, the rubric DB in `knowledge/`, and the graph in `graph/`.
- Imports run one way (`core → llm → knowledge → domain → graph → entry points`). Domains never import each other; they meet only through State.
- Tests mirror the layout under `tests/`. Paid or networked tests carry `use_llm` / `use_network` markers, so `uv run pytest` is free.

## Alternatives considered

| Alternative | Why not |
|---|---|
| A single notebook | One namespace for everything; tests need the notebook kernel. |
| One flat module per stage | No home for helpers two stages share; boundaries cannot be enforced. |

## Consequences

- A node can change without touching another domain, and its tests run in isolation.
- Inspecting an intermediate result means rerunning from a checkpoint (`rerun --thread … --from-node …`) instead of re-running a cell.
