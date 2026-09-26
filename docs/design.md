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

## Input

The graph takes a live product page URL, not a saved snapshot. The URL arrives in the initial
State (`product_page.url`). The page is loaded with
Playwright, since the display-method check needs rendered, computed styles. The fetched HTML
lives in State, so the thread's checkpoints are the record of what was judged.

Page preparation follows the old repo's `collect.py`, `preprocess.py`, `ai.py`:

1. Open the URL, wait for `networkidle`, scroll to the bottom.
2. LLM identifies the target product (name, type, summary) from the page outline.
3. First removal: `header`, `nav`, `footer`, `aside`, `[role=banner]`, `[role=navigation]`,
   `[role=contentinfo]`.
4. Site rule: LLM picks the main region, extra removal selectors, and expandable controls.
   Cached per host in SQLite and reused once verified.
5. Second check: LLM judges each removed region for target-product content. Such regions are
   kept, and the rule is regenerated with that feedback (max 2 retries). A rule that never
   passes is stored as unverified.
6. Expand collapsed controls (`details`, `aria-expanded=false`, rule's expand selectors).
7. Open in-content links; include only pages the LLM judges to describe the target product.
8. On the live page, for both default and expanded states, assign `data-block-id` and extract
   computed styles.

- Steps 1-8 all run inside `preprocess_product_page`. Steps 6 and 7 use the results of steps 2
  and 4, so the browser session stays open within one node. Playwright objects never enter
  State. In a notebook, sync Playwright runs in a separate thread to avoid the asyncio loop.
- Image captioning is out of scope.
- The old `collect` command skipped step 5 (it ran only in `llm-process`). This design runs it.

## Graph

Serial, three modules: display method → plain language → explanation duty.

```
START → preprocess_product_page → classify_type
      → judge_display_method → generate_plain_lang → judge_explanation_duty
      → verify_answer ─┬→ end_report → END
                       └→ retry_dispatch → judge_display_method
```

- Order: explanation duty judges the plain-language output, so plain language runs right
  before it. A plain-language retry then re-runs only what depends on it.
- No `pre_*` nodes. Each module node prepares its own input at the top of the function.
  `preprocess_product_page` builds the page data that all modules share (Input steps 1-8).
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

- Sub-TypedDicts use `total=False`. The initial State sets every key to `{}`, except
  `product_page.url`.
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

| Id | Set by | Scope |
|---|---|---|
| `checkpointer` | `compile()`, once | one SQLite file |
| `thread_id` | the caller, per invoke | one review of one page, e.g. `f"{product_id}-{run_time}"` |
| `checkpoint_id` | LangGraph, per node step | one saved point inside a thread |

- Each review request gets a new `thread_id`. Do not split by user: this graph is a one-shot
  review, not a conversation. Record the requester in State or config if needed.
- Re-running from a checkpoint adds a new branch to the same thread; the original history stays.
- `SqliteSaver` serializes writes to one file. Fine for the demo; a concurrent web service
  would need a Postgres saver.
- Checkpoints store the full State (page HTML, judgments). Only public product pages are
  processed, so no personal data is stored.
