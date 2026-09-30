---
ai-generated: true
human-review: false
created: 2026-09-29
updated: 2026-09-30
---

# Evidence Cards (`extract_evidence_cards`)

This page describes how `extract_evidence_cards` turns the page's own text into a flat list of fact-shaped cards that later nodes cite.

A card holds a claim, its conditions, exceptions and numbers, a verbatim quote, and the source line it came from. `kind` names the shape of the fact (`benefit_claim`, `rate_claim`, ...), never a verdict.

## Input and output

| | Content |
|---|---|
| Reads | `product_page`, `classification` |
| Writes | `evidence_cards`: `{status, reason, sources, cards, rejected, coverage_gaps, model_calls}` |
| Model use | one structured call, one retry |

## Sources

The page HTML is split into visual lines. A line is kept only if it can be found again in the page's visible text; duplicates are dropped. Ids are positional (`dom-0`, `dom-1`, ...).

Code, not the model, sets each line's `visibility` by matching it to the display check's measured blocks:

| `visibility` | Meaning |
|---|---|
| `default_visible` | visible when the page first loaded |
| `revealed` | visible only after a user action |
| `hidden` | measured, never visible |
| `image_only` | every matching block is image-backed or undrawn text |
| `unresolved` | no measured block matches |

Only the first 300 lines are sent to the model; every line still appears in `sources`.

## How it works

| Done by code | Done by the model |
|---|---|
| splitting lines, setting visibility, accepting or rejecting each candidate, deduplicating, assigning ids | drafting candidate cards from the lines |

A candidate is accepted only if its `kind` is allowed, its `source_id` was sent, its quote is found in that source line, and every number, qualifier and exception is found in the quote. Failing candidates are retried once with the problems fed back; whatever still fails goes to `rejected` with a reason. Accepted cards are deduplicated and numbered `c1`, `c2`, ... in page order, so the same page always gives the same ids. Numbers stay as the literal page text (`30만원`), never converted.

## Coverage gaps

Gaps are descriptive, never a verdict:

- open gaps copied from page discovery, each linked to the cards they affect;
- `claim_without_visible_condition` for every benefit or rate card with no qualifier and no exception.

A missing condition is something to investigate, not proof of a violation.

## Status

| `status` | When |
|---|---|
| `완료` | at least one card survived |
| `카드 없음` | the model was called but no candidate survived |
| `판정 불가` | no page HTML or no product type; no model call |

## Limits

- The gold set (`eval/fixtures/gold/evidence_cards.json`, 25 entries) is AI-drafted and not yet reviewed by a person. It ships in the reproduction asset zip, not the repository.
- Numbers and qualifiers are checked against the card's own quote. A quote that drops a clause but still matches the source is not caught.

Tests: `tests/domain/evidence_cards/`.
