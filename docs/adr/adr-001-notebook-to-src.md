---
ai-generated: true
human-review: false
created: 2026-09-28
---

# ADR-001 — Move the review pipeline from one notebook into a src package

- **Status:** Accepted, 2026-09-27
- **Recorded here:** 2026-09-28. The first copy lived in `localdocs/adr/` (gitignored, local only)
  and did not travel with the repository; this is the repository copy, rewritten from
  `docs/src-layout-migration.md` and `docs/design.md`, which were written with the decision.

## Context

Until 2026-09-27 the whole review pipeline was `notebooks/review.ipynb`: about 2,900 lines of
definitions in seven sections. That suited exploration — a cell could be re-run against a live
checkpoint — but three costs had become concrete:

- every definition shared one namespace, so nothing kept the display-check helpers away from the
  product-page session, and nothing said which module owned which helper;
- verification was one assert cell that ran only with the whole notebook, so the free checks
  could not be run on their own or separated from the paid ones;
- task prompts (`ralph/PROMPT_*.md`) pointed at cell ids, which broke whenever a cell was split.

## Decision

Move the code into `src/financial_disclosure_review/` with one folder per State key under
`domain/` (`product_page`, `classification`, `display_check`, `plain_language`,
`explanation_duty_check`, `verification`, `report`), shared helpers in `core/`, model calls in
`llm/`, the rubric DB in `knowledge/`, and the graph in `graph/`. Imports run one way
(`core → llm → knowledge → domain → graph → __main__`); domains never import each other and meet
only through State. Tests mirror the layout under `tests/`, and paid or networked tests carry the
`use_llm` / `use_network` markers so `uv run pytest` stays free.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Keep the notebook, add `%run` includes | Keeps one namespace; tests still need the notebook kernel. |
| Split into several notebooks | Cell-id references still break; no import boundary. |
| One flat module per stage | No home for helpers two stages share; boundary rules unenforceable. |

## Consequences

- The logic moved as is. Equivalence was checked on 2026-09-27 by running two sample URLs through
  the new graph to END with the same classification as before the move.
- Two stubs that existed at the time of the move (`report`, `graph/retry.py`) were filled the same
  day; `grep -rn "Stub:" src/` returns nothing.
- Lost: inspecting a checkpoint interactively. `rerun --thread … --from-node …` replaces it.
- The file-by-file mapping is in `docs/src-layout-migration.md`.
