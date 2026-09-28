# Documentation

Use the shortest document that answers the question. The README is the entry point; these pages
hold the detail it links to.

## Run and operate

- [API](api.md) — job lifecycle, authentication, response detail, and limits.
- [Docker setup](setup-docker.md) and [Cloudflare tunnel](setup-cloudflare.md) — local and deployed service setup.
- [Operations](operations.md) — escalation, cost controls, data handling, and abuse controls.
- [Team usage](team-usage-guide.md) — submit and poll a deployed API.

## Review workflow

- [Design](design.md) — package boundaries, graph, state, inputs, rubrics, and checkpoints.
- [Product-page discovery](product_page.md), [classification](classification.md),
  [display checks](display_check.md), [plain language](plain_language.md),
  [explanation duty](explanation_duty_check.md), and [reporting](report.md).
- [Case search](cases.md) — corpus, indexing, and retrieval limits.

## Evidence and history

- [Evaluation](evaluation.md) — suites, results, and what the numbers do not establish.
- [Architecture decisions](adr/README.md) — decisions that constrain the implementation.
- [Source-layout migration](src-layout-migration.md) — notebook-to-package migration record.

## Writing conventions

- Open with the page's purpose, then state the decision or procedure.
- Keep a fact in one canonical document; link to it elsewhere.
- Use short, descriptive inline links for sources and related documents. Do not add a separate
  footnote merely to repeat a URL.
- Put operational commands in fenced blocks and state any cost, network, or destructive effect
  immediately before the command.
- Mark assumptions and unresolved limits explicitly; do not bury them in implementation history.
