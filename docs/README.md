# Documentation

Use the shortest document that answers the question. The root README is the entry point; this
page indexes the detail it links to.

## Architecture

`financial_disclosure_review` reviews one public financial-product page and produces a report for
a human reviewer. It does not determine legal compliance or publish rewritten content.

### Boundaries

| Layer | Responsibility |
|---|---|
| `core/` | Shared types, context, text, usage metering, threads, and display helpers. |
| `llm/` | Structured model calls, retry helpers, tool-call turn, and image input. |
| `knowledge/` | Rubrics with their statute sources, and the SQLite rubric DB build and lookup. |
| `domain/<name>/` | Domain prompts, schemas, rules, and decisions. |
| `graph/` | Nodes, routing, retry policy, and graph assembly. |
| `evaluation/` | Cassettes, suites, fixtures, and metrics; never called by a review. |
| `serving/` | Gateway, worker, jobs, and HTTP schemas; no domain judgment. |

Dependencies flow from `core` toward `graph` and then to the CLI or serving entry point. Domains do
not import each other; they exchange data only through State.

### Workflow

```text
START → preprocess* ─┬→ classify ─┬→ evidence cards → display ─┬→ reader overview* ────────────────┬→ ad disclosure → verify → report
                     │            │                            └→ ad disclosure (original side) ┘
                     │            └→ report (out of scope / uncertain)
                     └→ report (collection failed / insufficient)

* bounded tool-calling agents: the page-discovery agent (preprocess) and a small reader-selection
  agent that the reader overview runs when the reader is given in free text.
```

The system is a deterministic review workflow with bounded agentic subflows, not an autonomous
agent. The graph, its routing and its retry policy are fixed in code; classification, card
extraction, display judgment, the overview and the ad-disclosure checks are single structured model
calls. Only the two subflows above choose their own tool calls, and each can be bypassed: a
saved site rule replays without the page agent, and a reader given by uuid, attributes or the
product-type default skips selection. The report's `에이전트 실행` line and `summary.agent_runs`
state which loops ran in each review (see the [2026-09-29 audit](../data/agentic-behavior-audit.md)).

- Classification ends normally for `범위 밖` and `판정 불가`; the report explains why.
- The reader overview precedes the ad-disclosure check because the latter judges the page and the
  overview by the same criteria and compares them. The original side reads only the page, so
  `judge_disclosure_original` runs in the same step as the overview. LangGraph waits for every node of a step, which is
  why each independent node is paired with the step it fits. With the partial re-ask of rejected
  codes, one live page went from 662 s to 468 s (2026-09-29, 디지로카 Las Vegas, saved site rule).
- Agents choose tools; code validates every quote, selector and filter they propose, and each
  agent has a turn budget and a machine-readable stop reason.
- Verification routes to the earliest actionable failure. At most two rounds run; display checks
  are not repeated because unchanged measurements would only repeat the same evidence.

### State and persistence

Each top-level State key belongs to one module: `product_page`, `classification`,
`evidence_cards`, `display_check`, `persona_explanation`,
`ad_disclosure_check`, `verification`, and `report`. A node
writes only its own key. Settings such as model, paths, and limits belong to `Context`, passed at
invoke time rather than stored in State.

`SqliteSaver` stores checkpoints per review thread. A re-run branches from a saved checkpoint; the
original history remains intact. Checkpoints include rendered page content and judgments, so they
are internal data even though the source page is public.

### Rubrics and scope

Rubrics live in SQLite built from the checked-in source data. Classification alone assigns product
and page types. The application reviews public card-company advertising pages, so it judges them by
the rules that bind an advertisement: the mandatory ad disclosures (A·B·C groups of
`card_guardrail_rubric`, from 금소법 제22조 and the 여신협회 광고규정) and the display-method rules.
Explanation-duty items (금소법 제19조) bind the contract-stage product document, not an ad, so they
are listed for the reviewer to confirm in that document and are not judged
([ADR-006](architecture-decisions/adr-006-ad-disclosure-instead-of-explanation-duty.md)). Any
unavailable evidence or unresolved condition becomes a reviewer task, never a pass.

### Cost and quality

Every model call is metered. Per-run call and cost limits are checked before a call, and the report
records the resulting usage. The evaluation package is separate from production: it replays
recorded answers by default. See [evaluation](evaluation.md) for suites and results, and
[operations](operations.md) for escalation and cost controls.

## Run and operate

- [API](api.md) — job lifecycle, authentication, easy-language reader input, response detail, and limits.
- [Docker setup](setup-docker.md) and [Cloudflare tunnel](setup-cloudflare.md) — local and deployed service setup.
- [Operations](operations.md) — escalation, cost controls, data handling, and abuse controls.

## Review workflow

- [Agent node specs](agent-node-specs/README.md) — the workflow map and a per-node summary, then per-node behavior: [product-page discovery](agent-node-specs/product_page.md),
  [classification](agent-node-specs/classification.md), [display checks](agent-node-specs/display_check.md),
  [evidence cards](agent-node-specs/evidence_cards.md),
  [reader overview](agent-node-specs/persona_explanation.md), [ad disclosure](agent-node-specs/ad_disclosure_check.md),
  [verification and retry](agent-node-specs/verification.md) and [reporting](agent-node-specs/report.md). The legacy [plain language](agent-node-specs/plain_language.md)
  module is kept only for the plain-contract evaluation suite.

## Evidence and history

- [Evaluation](evaluation.md) — suites, results, and what the numbers do not establish.
- [Architecture decisions](architecture-decisions/README.md) — decisions that constrain the implementation.
- Lessons from previous projects — insights carried into this design from
  [`financial-product-disclosure-and-plain-language`](lessons-from-previous-projects/disclosure-plain-language.md)
  (an earlier implementation of this task) and the
  [guardrail research study](lessons-from-previous-projects/guardrail-research-study.md) (QGuard reproduction and extension).

## Writing conventions

- Open with the page's purpose, then state the decision or procedure.
- Keep a fact in one canonical document; link to it elsewhere.
- Use short, descriptive inline links for sources and related documents. Do not add a separate
  footnote merely to repeat a URL.
- Put operational commands in fenced blocks and state any cost, network, or destructive effect
  immediately before the command.
- Mark assumptions and unresolved limits explicitly; do not bury them in implementation history.
