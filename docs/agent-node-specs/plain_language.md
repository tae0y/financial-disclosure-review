---
ai-generated: true
human-review: false
created: 2026-09-27
updated: 2026-09-30
---

# Plain-Language Rewrite (`generate_plain_lang`, legacy)

This page describes the legacy line-by-line plain-language rewrite, which the graph no longer calls.

The module is kept only for the `plain-contract` evaluation suite ([evaluation](../evaluation.md)). The current plain-language output is the [reader advice](persona_explanation.md).

## What it did

It split the page into visual lines (`b0`, `b1`, ...) and rewrote each in plain Korean. A line whose rewrite failed a check was replaced by the original sentence, and the failure was kept for verification.

| Checked by code | Judged by a second model call |
|---|---|
| numbers added to or missing from the rewrite; new absolute or superlative phrases (`누구나`, `무조건`, `최고`); a hedge (`~할 수 있습니다`) turned into a certainty; glossed terms really in the quote | whether a condition, exception, limit or penalty survived in meaning |

The meaning check replaced a keyword scan, which flagged correct synonym rewrites of jargon (`해지` → `그만둠`) as omissions. An unclear answer counts as a pass, so uncertainty does not revert a correct rewrite.

## Limits

- Its mapping from plain-language rubric items to check failures is this module's own reading, not stated by the rubric. One failure can be reported on several items (쉬운말06, 07, 09).
- The `condition_dropped` cases in `eval/cases/plain_contract.json` need a recorded cassette because the meaning check is a model call.

Tests: `tests/domain/plain_language/`.
