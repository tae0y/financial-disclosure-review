# Design

`financial_disclosure_review` reviews one public financial-product page and produces a report for a
human reviewer. It does not determine legal compliance or publish rewritten content.

## Boundaries

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

## Input and page discovery

The input is a live public URL. Playwright renders the page, records snapshots, and extracts the
LLM-facing HTML. The discovery agent may identify the product, expand in-page content, and open
eligible same-host links. Tool guards prohibit typing, form submission, script evaluation,
downloads, and uncontrolled navigation.

Saved site rules make repeat templates inexpensive. A visit reuses a rule only when structural
checks and output validation still pass; otherwise it rediscovers the content. Measurements are
taken from rendered snapshots, not inferred from source HTML. See [product-page discovery](product_page.md).

## Workflow

```text
START → preprocess → classify ─┬→ search cases → display → plain language → explanation duty → verify → report
                               └→ report (out of scope / uncertain)
```

- Classification ends normally for `범위 밖` and `판정 불가`; the report explains why.
- Case retrieval informs later judgment but is not itself a judgment or retry target.
- Plain language precedes explanation duty because the latter compares the source with the rewrite.
- Verification routes to the earliest actionable failure. At most two rounds run; display checks
  are not repeated because unchanged measurements would only repeat the same evidence.

## State and persistence

Each top-level State key belongs to one module: `product_page`, `classification`, `case_search`,
`display_check`, `plain_language`, `explanation_duty_check`, `verification`, and `report`. A node
writes only its own key. Settings such as model, paths, and limits belong to `Context`, passed at
invoke time rather than stored in State.

`SqliteSaver` stores checkpoints per review thread. A re-run branches from a saved checkpoint;
the original history remains intact. Checkpoints include rendered page content and judgments, so
they are internal data even though the source page is public.

## Rubrics and scope

Rubrics live in SQLite built from the checked-in source data. Classification alone assigns product
and page types. The application reviews public card-company product pages; explanation-duty items
on advertising pages are applied as quality criteria by analogy, not asserted as direct statutory
duties. Any unavailable evidence or unresolved condition becomes a reviewer task, never a pass.

## Cost and quality

Every model call is metered. Per-run call and cost limits are checked before a call, and the report
records the resulting usage. The evaluation package is separate from production: it replays
recorded answers by default and documents both results and limitations in [evaluation](evaluation.md).

For operating safeguards, see [operations](operations.md); for decisions behind this structure,
see [ADRs](adr/README.md).
