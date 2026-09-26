---
ai-generated: true
human-review: false
created: 2026-09-26
---

# Design

Decisions for `notebooks/review.ipynb`. This file records the target design, not progress.

## Principles

- Simplicity first. Add only what the current step needs.
- Build one step at a time. The notebook runs top to bottom after every step.
- Data model, node inputs/outputs, and graph shape are decided by 영태.

## Notebook sections

1. Dependencies: `!uv sync`, imports
2. Data model: class definitions
3. Helpers: domain-agnostic functions (file/DB reads, string handling)
4. Business logic: functions holding judgment or generation rules
5. Graph nodes: take State, call section 4, return only changed keys
6. Graph build: nodes, edges, compile
7. Run (DB build code sits right before this section)

Sections with no code yet keep only their markdown heading.

## Data rules

- Runtime data moves only through State. No global variables for it.
- Settings (paths, model name, DB file) are passed at invoke time, not stored in State.
- Reusable data (rubrics, statutes, glossary, cases) is read from SQLite. Helpers open and
  close the connection. Vector search uses `sqlite-vec` (needs a Python build with
  `enable_load_extension`; the Homebrew 3.12 venv has it).

## Graph

Serial, three modules: display method → plain language → explanation duty.

```
START → init_user → preprocess_product_page → classify_type
      → judge_display_method → generate_plain_lang → judge_explanation_duty
      → verify_answer ─┬→ end_report → END
                       └→ retry_dispatch → judge_display_method
```

- Order: explanation duty judges the plain-language output, so plain language runs right
  before it. A plain-language retry then re-runs only what depends on it.
- No `pre_*` nodes. Each module node prepares its own input at the top of the function.
  `preprocess_product_page` builds only the page HTML that all modules share.
- All retries go through `retry_dispatch`. It links only to `judge_display_method` for now;
  per-module branching (re-run only the failed module) is added there later.
- `route_after_verify` returns `"end_report"` until the retry logic is built.

## State

One top-level key per module. A node writes only its own module's key and reads the rest.

| Key | Type | Fields |
|---|---|---|
| `product_page` | `ProductPage` | `product_id`, `url`, `html`, `snapshots`, `product_type`, `page_type` |
| `display_check` | `DisplayCheck` | `items`, `judgments` |
| `plain_language` | `PlainLanguage` | `items`, `draft`, `html`, `term_refs`, `accepted_blocks`, `contract_errors` |
| `explanation_duty_check` | `ExplanationDutyCheck` | `items`, `original`, `plain`, `fidelity` |
| `verification` | `Verification` | `passed`, `reasons`, `failed_modules`, `feedback`, `loop_count` |
| `report` | `Report` | defined when `end_report` is built |

- Sub-TypedDicts use `total=False`. The initial State sets every key to `{}`.
- LangGraph replaces a returned key's whole value. A node copies its module's current dict
  and overwrites only the fields it changed.
- `verification.feedback` is read by `generate_plain_lang` in the next round.
- `explanation_duty_check.original` is fixed after the first round.
- `report` is printed to check the result.

## Rubrics

Each module has its own rubric. Items carry `applies_to` (product types), `page_types`, and
`applies_condition`. `classify_type` sets `product_type` and `page_type`; each module node
looks up its own items with them. Original and plain-language text are judged against the
same explanation-duty items.

Rubric drafts: `../05 법령·지침 원문 검증/카드사 가드레일 루브릭/`.

## Checkpoints

- Compile with `SqliteSaver` (`langgraph-checkpoint-sqlite`) so checkpoints survive a kernel
  restart and paid LLM calls can be skipped.
- Re-run from a node: pick the checkpoint in `graph.get_state_history(config)` whose `next` is
  that node, then `graph.invoke(None, {"configurable": {"thread_id": ..., "checkpoint_id": ...}})`.
  Use `graph.update_state()` first to change State before re-running.
