---
ai-generated: true
human-review: false
created: 2026-09-26
---

# Design

Decisions for the `financial_disclosure_review` package. This file records the target
design, not progress.

## Principles

- Simplicity first. Add only what the current step needs.
- Build one step at a time. `uv run pytest`, `ruff check` and `pyright` pass after every step.
- Data model, node inputs/outputs, and graph shape are decided by 영태.

## Package layout

`src/financial_disclosure_review/`, with one folder per State key. The placement rules are in
`localdocs/plan.src-layout.md`; the short form is:

| Folder | Holds | Never holds |
|---|---|---|
| `core/` | code two or more domains share: State, Context, text, colour, threads | domain judgment |
| `llm/` | the call devices: structured output, image input, one tool-calling turn | prompt text |
| `knowledge/` | reading and building reusable reference data (rubrics, later statutes and cases) | which items an item-owner picks |
| `<domain>/` | judgment rules, prompts, response schemas, loop decisions | `langgraph`, `State`, another domain |
| `graph/` | nodes, routing, retry branching, graph assembly | business logic |
| `__main__.py` | the CLI | anything else |

Import direction: `core → llm → knowledge → 도메인 → graph → __main__`. Domains never import
each other; their data meets only in State. A domain exports one entry function from its
`__init__.py`, and that function takes the State values it needs, not the whole State.

Domains with no code yet (`plain_language`, `explanation_duty_check`, `verification`, `report`)
hold a stub that returns `{}`, so the graph still runs to END.

## Data rules

- Runtime data moves only through State. No global variables for it.
- Settings (paths, model name, DB file) are passed at invoke time, not stored in State:
  `Context(model, db_path)` via `context=`. Pass it again when re-running from a checkpoint.
  The CLI takes them as `--model`, `--data-dir`, `--db-path` and `--checkpoints`.
- Reusable data (rubrics, statutes, glossary, cases) is read from SQLite. Helpers open and
  close the connection. Vector search uses `sqlite-vec` (needs a Python build with
  `enable_load_extension`; the Homebrew 3.12 venv has it).

## Input

The graph takes a live product page URL, not a saved snapshot. The URL arrives in the initial
State (`product_page.url`). The page is loaded with
Playwright, since the display-method check needs rendered, computed styles. The fetched HTML
lives in State, so the thread's checkpoints are the record of what was judged.

Code loads the page; an agent manipulates it. Selector rules per site are not used: every
site differs, and rules would need hand-tuning per site.

1. Code opens the URL in a new tab, waits for `networkidle` (on timeout, continues), scrolls
   to the bottom, and takes the tab's `default` snapshot.
2. An agent works on the live page with tools that wrap Playwright's own API (not the
   Playwright MCP server). It identifies the target product, marks page chrome for removal,
   expands collapsed content, and opens in-content links. The prompt lists the signals to
   watch: `aria-expanded`, `aria-controls`, `aria-hidden`, `hidden`, `role=tab`/`tabpanel`/
   `dialog`, `details`/`summary`, landmarks (`header`, `nav`, `footer`, `aside`, `role=banner`
   etc.), and the exception that a `header` inside the product article is content.
3. Snapshots are tied to navigation. Arriving on a page (initial load, `goto`, `open_tab`)
   takes a `default` snapshot; leaving it (`goto`, `close_tab`, `finish`) takes an `expanded`
   snapshot. The agent can also save extra `expanded` snapshots (e.g. one per tab panel).
   A snapshot assigns `data-block-id` and reads computed styles over CDP.
4. Code builds the LLM-facing `html` from the main page's last `expanded` snapshot plus linked
   pages the agent included: marked regions and styling attributes removed, blocks hidden by
   computed style get `data-hidden`.

- Guards live in the tools, not the prompt: no `fill`/`type`/`evaluate`/download tools; a click
  that would navigate the main frame is answered with 204 and reported to the agent, which
  must use `goto` so the page is snapshotted before it leaves; turn and page caps.
- Block ids are unique per State (prefix `v{visit}-`). Default and expanded snapshots of one
  visit share ids, since the page is never reloaded within a visit.
- Everything runs inside `preprocess_product_page`. Sync Playwright objects are bound to their
  thread, so the whole agent loop runs in one worker thread. Playwright objects never enter
  State. Tool calls are not checkpointed one by one; the agent's action log is kept in State.
- Image captioning is out of scope.

## Graph

Serial, three modules: display method → plain language → explanation duty.

```
START → preprocess_product_page → classify_type ─┬→ judge_display_method
                                                 └→ END   (범위 밖 / 판정 불가)

judge_display_method → generate_plain_lang → judge_explanation_duty
      → verify_answer ─┬→ end_report → END
                       └→ retry_dispatch → judge_display_method
```

- `route_after_classify` returns `END` when `classification.product_type` is `범위 밖` or
  `판정 불가`, and `"judge_display_method"` otherwise. Ending here is a normal result, not an
  error: the caller reads `classification` (with its `reason`) from the final State. Only
  system errors (API failure, response schema parse failure) raise exceptions.
- Order: explanation duty judges the plain-language output, so plain language runs right
  before it. A plain-language retry then re-runs only what depends on it.
- No `pre_*` nodes. Each module node prepares its own input at the top of the function.
  `preprocess_product_page` builds the page data that all modules share (Input).
- All retries go through `retry_dispatch`. It links only to `judge_display_method` for now;
  per-module branching (re-run only the failed module) is added there later.
- `route_after_verify` returns `"end_report"` until the retry logic is built.

## State

One top-level key per module. A node writes only its own module's key and reads the rest.

| Key | Type | Fields |
|---|---|---|
| `product_page` | `ProductPage` | `url`, `product`, `actions`, `snapshots`, `html` |
| `classification` | `Classification` | `product_type`, `page_type`, `reason` |
| `display_check` | `DisplayCheck` | `items`, `judgments` |
| `plain_language` | `PlainLanguage` | `items`, `draft`, `html`, `term_refs`, `accepted_blocks`, `contract_errors` |
| `explanation_duty_check` | `ExplanationDutyCheck` | `items`, `original`, `plain`, `fidelity` |
| `verification` | `Verification` | `passed`, `reasons`, `failed_modules`, `feedback`, `loop_count` |
| `report` | `Report` | defined when `end_report` is built |

- `product_page.product` holds `product_name`, `summary`, `evidence` only. It identifies the
  product; types are set by `classify_type` in `classification`.
- Sub-TypedDicts use `total=False`. The initial State sets every key to `{}`, except
  `product_page.url`.
- LangGraph replaces a returned key's whole value. A node copies its module's current dict
  and overwrites only the fields it changed.
- `verification.feedback` is read by `generate_plain_lang` in the next round.
- `explanation_duty_check.original` is fixed after the first round.
- `report` is printed to check the result.

## Rubrics

Each module has its own rubric. Items carry `applies_to` (product types), `page_types`, and
`applies_condition`. `classify_type` writes `classification`; each module node looks up its
own items with it. Only `classify_type` decides types: `product_page` carries no type or
category field. Original and plain-language text are judged against the
same explanation-duty items.

Scope: a public card-company product page is an ad (금소법 제22조). Explanation-duty items are
applied by analogy (준용) as quality criteria, not as direct duties. Explanation screens inside
the application flow are out of scope.

`classify_type` judges in three steps: (1) is it a single product page, (2) is it a card
company's credit product or service, (3) which product type. A "no" at step 1 or 2 ends the
review with `product_type = "범위 밖"`. The page type is not judged; it follows from the
product type.

| `product_type` | `page_type` |
|---|---|
| 신용카드, 장기카드대출, 할부금융·리스 | 상품광고 |
| 단기카드대출, 리볼빙 | 업무광고 |

- Non-review results: `product_type` is `범위 밖` (step 1 or 2 failed) or `판정 불가` (the
  model's answer failed validation twice, or the verification call disagreed; needs a human
  check). In both cases `page_type` is `None` and `reason` names the step and the grounds.
- Fixed by scope, not classified: ad status, the card company's own site, association review,
  online automated sale, explanation screen.
- `applies_condition` is judged per item by the LLM inside each module node, not by
  `classify_type`.

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
| `thread_id` | the caller, per invoke | one review of one page, e.g. `f"review-{run_time}"` |
| `checkpoint_id` | LangGraph, per node step | one saved point inside a thread |

- Each review request gets a new `thread_id`. Do not split by user: this graph is a one-shot
  review, not a conversation. Record the requester in State or config if needed.
- Re-running from a checkpoint adds a new branch to the same thread; the original history stays.
- `SqliteSaver` serializes writes to one file. Fine for the demo; a concurrent web service
  would need a Postgres saver.
- Checkpoints store the full State (page HTML, judgments). Only public product pages are
  processed, so no personal data is stored.
