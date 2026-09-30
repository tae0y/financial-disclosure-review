---
ai-generated: true
human-review: false
created: 2026-09-30
updated: 2026-09-30
---

# Agent Node Specs

This page lists the graph nodes, what each reads and writes, and where its spec lives. The workflow diagram is in the [project README](../../README.md#how-a-review-runs), and the rules shared by every node are in [Architecture](../architecture.md#rules-every-node-follows).

| Node | Spec | Reads | Writes | Model use |
|---|---|---|---|---|
| `preprocess_product_page` | [product_page](product_page.md) | `product_page.url` | `product_page` | Tool-calling page agent; none when a saved rule replays |
| `classify_type` | [classification](classification.md) | `product_page` | `classification` | 1–2 structured calls plus one verification call |
| `extract_evidence_cards` | [evidence_cards](evidence_cards.md) | `product_page`, `classification` | `evidence_cards` | One structured call, one retry |
| `judge_display_method` | [display_check](display_check.md) | `product_page`, `classification`, `evidence_cards` | `display_check` | Structured calls for labels and verdicts, optional image crops |
| `generate_persona_explanation` | [persona_explanation](persona_explanation.md) | `evidence_cards`, `classification`, `verification.feedback` | `persona_explanation` | Reader-selection agent for free-text readers; one drafting call |
| `judge_ad_disclosure` | [ad_disclosure_check](ad_disclosure_check.md) | `product_page`, `classification`, `verification.feedback`, its own previous rows on a retry | `ad_disclosure_check` | One structured call |
| `verify_answer` | [verification](verification.md) | every module key | `verification` | None |
| `retry_dispatch` | [verification](verification.md) | `verification` | `verification` (retry fields) | None |
| `end_report` | [report](report.md) | every module key | `report` | None |

[plain_language](plain_language.md) is a legacy module. The graph no longer calls it; it is kept for the `plain-contract` evaluation suite.
