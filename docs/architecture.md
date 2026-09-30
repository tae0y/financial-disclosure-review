---
ai-generated: true
human-review: false
created: 2026-09-30
---

# Architecture

This page describes how the `financial_disclosure_review` package is organized and the rules that hold across the review workflow. The workflow itself is drawn in the [project README](../README.md#how-a-review-runs).

## Layers

| Layer | Responsibility |
|---|---|
| `core/` | Shared types, context, text helpers, usage metering, threads |
| `llm/` | Structured model calls, retries, tool-call turns, image input |
| `knowledge/` | Rubrics with their statute sources; SQLite rubric DB build and lookup |
| `domain/<name>/` | One folder per State key: prompts, schemas, rules, decisions |
| `graph/` | Nodes, routing, retry policy, graph assembly |
| `evaluation/` | Cassettes, suites, fixtures, metrics; never called by a review |
| `serving/` | HTTP gateway, worker, job store; no domain judgment |

Imports flow one way, from `core` toward `graph` and then to the CLI or serving entry point. Domains never import each other; they exchange data only through State.

## State and checkpoints

Each top-level State key belongs to one module: `product_page`, `classification`, `evidence_cards`, `display_check`, `persona_explanation`, `ad_disclosure_check`, `verification`, `report`. A node writes only its own key. Settings such as the model, paths, and limits travel in `Context` at invoke time, not in State.

`SqliteSaver` stores a checkpoint per review thread. `rerun --from-node` branches from a saved checkpoint and leaves the original history intact. Checkpoints contain rendered page content and model output, so treat them as internal data.

## Rubrics and scope

Rubrics are YAML files in `assets/`, built into `data/reference.sqlite` by `build-db`. Code, not a model, selects the items that apply from the classified product type and page type ([ADR-004](architecture-decisions/adr-004-fixed-statute-lookup.md)).

| Rule set | Source | How it is used |
|---|---|---|
| Mandatory ad disclosures (A·B·C of `card_guardrail_rubric`) | 금소법 제22조, 여신협회 광고규정·세부지침 | Judged on the page by `judge_ad_disclosure` |
| Display-method rules (E of `card_guardrail_rubric`) | 여신협회 광고규정 세부지침 | Judged on the rendered page by `judge_display_method` |
| Explanation-duty items (`plain_service_rubric`) | 금소법 제19조 | Not judged. They bind the contract-stage product document, so the report lists them and the reader advice picks the ones to ask about ([ADR-006](architecture-decisions/adr-006-ad-disclosure-instead-of-explanation-duty.md), [ADR-007](architecture-decisions/adr-007-advice-only.md)) |

## Agents and their bounds

The system is a fixed workflow with two bounded agentic steps, not an autonomous agent.

| Agent | Chooses | Bounded by | Bypassed when |
|---|---|---|---|
| Page agent (`preprocess_product_page`) | Which controls to expand, which selectors cover the product | Turn, visit, click and interaction budgets; read-only tools | A saved site rule replays cleanly |
| Reader selection (`generate_persona_explanation`) | Dataset filters for a reader given in free text | 6 turns; every filter validated against the dataset | The reader is given by uuid or attributes, or not at all |

Each agent records a machine-readable stop reason. The report's `summary.agent_runs` states which agents ran in a review.

## Rules every node follows

- A node writes only its own State key (`core/state.py`).
- Every quote a model gives must be found in the text it claims to come from. A quote that is not there is rejected or turns the item into `판정 불가`.
- `판정 불가` is never a pass. It becomes a reviewer task in the report.
- Every model call is metered against the run's call and cost caps (`core/usage.py`). A cap reached after collection still ends in a `판정 불가` report that names the interrupted node.
- Legal criteria come only from the rubric DB. A node never invents a criterion.
