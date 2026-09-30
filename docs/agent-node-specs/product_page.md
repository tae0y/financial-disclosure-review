---
ai-generated: true
human-review: false
created: 2026-09-27
updated: 2026-09-30
---

# Product Page Discovery (`preprocess_product_page`)

This page describes how `preprocess_product_page` turns a URL into the product-specific content the other nodes judge.

## Input and output

| | Content |
|---|---|
| Reads | `product_page.url` |
| Writes | `product_page`: `{url, product, actions, snapshots, html, status, stop_reason, error, coverage, agent_trace}` |
| Entry point | `fetch_product_page(url, ctx)` in `domain/product_page/` |

`html` is empty whenever `status` is not `완료`. The function never raises for a page or agent failure; it returns a status instead.

## Three paths per visit

A rule is saved per host, page family and viewport. The page family masks the product-specific parts of the URL, so one rule covers every product on the same template.

| Path | When | Model calls |
|---|---|---|
| reuse | a saved rule passes the structural check and its replay passes validation | none |
| rediscover | a rule exists but the page has drifted from it | full discovery loop |
| discover | no rule exists | full discovery loop |

A rule stores include/exclude selectors, the expand steps that reveal hidden content, structural landmarks, a product-name selector, and the coverage measured when it was saved. A rule is rejected when a selector matches fewer elements than before, an expand step or landmark is gone, the product name is missing, the page has text blocks the rule never saw, or the replay leaves more hidden text than discovery did.

## How discovery works

A tool-calling agent explores the page; code measures coverage and decides when to stop.

| Done by code | Done by the model |
|---|---|
| measuring the page and listing coverage gaps; refusing unsafe actions; closing exploration; replaying and saving the rule | choosing which gap to explore next and proposing include/exclude selectors |

Coverage gaps steer exploration and never become a verdict:

- `unexpanded_control`: a tab, accordion or in-page anchor the agent may click but has not yet expanded.
- `hidden_text`: text hidden by default, judged by rendered style (display, visibility, opacity, zero size, collapsed ancestor).
- `benefit_without_condition`: a visible benefit or rate with no visible condition anywhere. Reported only.
- `image_only`: an image whose alt text reads like disclosure wording. Always unresolved.

Each `interact` call must name the gap it targets and the evidence it expects. Exploration closes on the first of: the interaction budget (at least `max_interactions`, default 8), two interactions in a row with no new text (`max_no_progress`), the last four model turns, or no actionable gap left. The agent can still submit a rule after that.

Only code saves a rule, after reloading the page and replaying the proposal exactly as a reuse visit would.

## What the page agent may not do

The guards live in the tools, not in the prompt.

- No fill, type, script-evaluation or download tool exists.
- A click is allowed only on a visible tab, accordion or in-page anchor. Form controls, navigation links, and anything labelled like apply, login, submit, pay or download are refused. The one allowed input is an accordion checkbox outside every form, which only toggles CSS.
- Navigation the code did not request is aborted. Popups are closed, dialogs dismissed and downloads cancelled.
- `open_link` follows only a same-origin http(s) link outside a form that is not a document file.
- During a click, every non-GET/HEAD request is blocked.
- Caps: `max_turns` (20) model turns, `max_visits` (3) page loads, 30 clicks per expand call.

## Status and stop reasons

| `status` | Meaning |
|---|---|
| `완료` | no reachable gap left in the product regions |
| `조사 불충분` | gaps remain; the report lists them as reviewer tasks |
| `수집 실패` | the page could not be loaded or became an error page |

`stop_reason` is one of `rule_reused`, `full_coverage`, `reachable_coverage`, `submitted_with_gaps`, `no_viable_control`, `no_new_evidence`, `turn_budget`, `interaction_budget`, `max_turns`, `budget_exhausted`, `fetch_error`, `page_unavailable`, `visit_cap`, `invalid_url`, `replay_failed`.

Hidden text that no reachable control can reveal is excluded and listed as a limitation (`reachable_coverage`), not counted as a failure.

## Snapshots

A snapshot captures every text-bearing element's text, computed style and bounds, plus the page HTML under `data/snapshots/`. Only snapshots taken while replaying the saved rule (`phase="render"`) are measured by the display check. Blocks over a background image or overlapping an `img` are flagged `visual_risk`, and a rendered crop is saved so their contrast can be judged from the checkpoint without a browser.

Tests: `tests/domain/product_page/`.
