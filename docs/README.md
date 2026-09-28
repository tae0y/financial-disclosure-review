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
| `knowledge/` | Rubrics, statutes, cases, SQLite/`sqlite-vec` access, and retrieval. |
| `domain/<name>/` | Domain prompts, schemas, rules, and decisions. |
| `graph/` | Nodes, routing, retry policy, and graph assembly. |
| `evaluation/` | Cassettes, suites, fixtures, and metrics; never called by a review. |
| `serving/` | Gateway, worker, jobs, and HTTP schemas; no domain judgment. |

Dependencies flow from `core` toward `graph` and then to the CLI or serving entry point. Domains do
not import each other; they exchange data only through State.

### Workflow

```text
START → preprocess → classify ─┬→ search cases → display → plain language → explanation duty → verify → report
                               └→ report (out of scope / uncertain)
```

- Classification ends normally for `범위 밖` and `판정 불가`; the report explains why.
- Case retrieval informs later judgment but is not itself a judgment or retry target.
- Plain language precedes explanation duty because the latter compares the source with the rewrite.
- Verification routes to the earliest actionable failure. At most two rounds run; display checks
  are not repeated because unchanged measurements would only repeat the same evidence.

### State and persistence

Each top-level State key belongs to one module: `product_page`, `classification`, `case_search`,
`display_check`, `plain_language`, `explanation_duty_check`, `verification`, and `report`. A node
writes only its own key. Settings such as model, paths, and limits belong to `Context`, passed at
invoke time rather than stored in State.

`SqliteSaver` stores checkpoints per review thread. A re-run branches from a saved checkpoint; the
original history remains intact. Checkpoints include rendered page content and judgments, so they
are internal data even though the source page is public.

### Rubrics and scope

Rubrics live in SQLite built from the checked-in source data. Classification alone assigns product
and page types. The application reviews public card-company product pages; explanation-duty items
on advertising pages are applied as quality criteria by analogy, not asserted as direct statutory
duties. Any unavailable evidence or unresolved condition becomes a reviewer task, never a pass.

### Cost and quality

Every model call is metered. Per-run call and cost limits are checked before a call, and the report
records the resulting usage. The evaluation package is separate from production: it replays
recorded answers by default. See [evaluation](evaluation.md) for suites and results, and
[operations](operations.md) for escalation and cost controls.

## Run and operate

- [API](api.md) — job lifecycle, authentication, response detail, and limits.
- [Docker setup](setup-docker.md) and [Cloudflare tunnel](setup-cloudflare.md) — local and deployed service setup.
- [Operations](operations.md) — escalation, cost controls, data handling, and abuse controls.

## Review workflow

- [Agent node specs](agent-node-specs/) — per-node behavior: [product-page discovery](agent-node-specs/product_page.md),
  [classification](agent-node-specs/classification.md), [display checks](agent-node-specs/display_check.md),
  [plain language](agent-node-specs/plain_language.md), [explanation duty](agent-node-specs/explanation_duty_check.md),
  and [reporting](agent-node-specs/report.md).

## Evidence and history

- [Evaluation](evaluation.md) — suites, results, and what the numbers do not establish.
- [Architecture decisions](architecture-decisions/README.md) — decisions that constrain the implementation.
- Lessons from previous projects — insights carried into this design from
  [`financial-product-disclosure-and-plain-language`](lessons-from-previous-projects/financial-product-disclosure-and-plain-language.md)
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
