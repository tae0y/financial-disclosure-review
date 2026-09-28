---
ai-generated: true
human-review: false
created: 2026-09-29
---

# evidence_cards

`extract_evidence_cards` turns the page's own text into a flat list of fact-shaped `cards`
(a claim, its conditions, its exceptions, its numbers, and where it came from). It runs after
classification. The model drafts candidate cards from the page's text lines in one call; code
decides which candidates survive. The node never rules on compliance — `kind` names the shape of
the fact (`benefit_claim`, `rate_claim`, …), not a verdict.

## Sources: `page_sources`

`page_sources` (`blocks.py`) splits the page html into visual lines with `html_lines`, drops
duplicates and any line `locate_quote` cannot re-find in `visible_text(html)` — the same
"only keep what can be pointed back to" rule `plain_blocks` uses. Ids are positional (`dom-0`,
`dom-1`, …) in page order.

`visibility` is decided by code, never the model, by matching each `display_check.blocks.
display_blocks` measured block against the source line (the measured block's normalized text is a
substring of the line's normalized text — the same relationship `display_blocks` itself uses to
map a measured row back to an html line):

1. no measured block matches (including: the page has no render snapshots at all) → `unresolved`
2. any matching block was visible in the default snapshot → `default_visible`
3. else, any matching block became visible in a later snapshot → `revealed`
4. else, every matching block is visual-risk (image-backed or undrawn text) → `image_only`
5. else (matched, never visible, not image-risk) → `hidden`

## Candidate extraction and the code contract

One model call (`EvidenceCardDrafts`, `prompts.EVIDENCE_CARD_TASK`) sees the page's sources (id +
text) and the classified `product_type`, and drafts cards. To bound prompt size, only the first
`SOURCE_CAP` (300) sources in page order are sent; every source still appears in the returned
`sources` list regardless of the cap, so a page longer than the cap is not silently dropped from
`sources`/coverage matching, only from what the drafting model can cite.

`contract.validate_candidate` is the only place a card is accepted or rejected, and it only
compares strings already on the page:

- `kind` is one of the eight allowed values
- `source_id` names a source that was sent to the model
- `quote` is locatable inside that source's text (`locate_quote`)
- every string in `numbers`, `qualifiers`, `exceptions` is locatable inside `quote` itself

This is wired as `call_ask`'s `check`: a candidate that fails is retried once with
`previous_problems`; whatever still fails after the retry is handed to `salvage`, which keeps the
candidates that passed and moves the rest to `rejected` as `{candidate, reason}` — it never raises
(unlike `plain_language`'s salvage, which reverts to the source quote, a card with no accepted
claim is simply dropped, not replaced by anything). `model_calls` counts the actual `ask`
invocations (1 normally, 2 when a retry happened).

Accepted candidates are deduplicated by `(normalized quote, kind)` and given deterministic ids
(`c1`, `c2`, …) in source order — the order of `sources`, not the order the model answered in, so
the same page always produces the same ids regardless of how the model orders its answer.
`numbers` (and `qualifiers`/`exceptions`) are kept as the literal substrings the model wrote, e.g.
`"30만원"`, never converted to a number — matching the design record's §8 correction that a card
comparing `300000` to the page's `"30만원"` cannot be checked at all.

## `coverage_gaps`

Two sources, both descriptive (never a verdict):

- open/unresolved entries copied from `page.coverage.gaps` (Stage 1's output), each given
  `card_ids`: a `hidden_text` gap collects cards whose `visibility` is `hidden` or `unresolved`; a
  `benefit_without_condition` gap collects `benefit_claim`/`rate_claim` cards with no qualifiers
  and no exceptions. Any other gap kind is copied through with an empty `card_ids`.
- one card-level gap this node derives itself: `{kind: "claim_without_visible_condition",
  card_ids, status: "open"}` for every `benefit_claim`/`rate_claim` card with no qualifiers and no
  exceptions — even when `page.coverage` was never provided.

A missing or hidden qualifier is a gap to investigate, not proof that no condition exists — never
treated as an automatic violation downstream.

## Status

`판정 불가` only when there is nothing to work with at all: no `page.html`, or `classification`
has no `product_type` (no model call in either case). `카드 없음` when a model call happened but
zero candidates survived validation (including: the page had sources but the model's candidates
were all rejected). `완료` once at least one card survived.

## Metrics (`evaluation/evidence_metrics.card_metrics`)

`quote_resolution` (share of cards whose quote still locates in its own source — should be 1.0 by
construction on a freshly run extraction, but is useful once cards get carried into a replay or a
cassette) and `gold_recall` / `risk_gold_recall` (share of a curated gold set's quotes matched by
some card's quote, either direction, normalized) against `eval/fixtures/gold/evidence_cards.json` (local only).
Deliberately not vector similarity, per the design record's rejection of embedding rerank as a
quality metric (§8 item 13 discusses this for `reference_cases`; the same reasoning applies here).

## Known gaps (for a human to confirm)

- The gold set lives in `eval/fixtures/gold/evidence_cards.json`, next to the two real lottecard
  pages it quotes (`eval/fixtures/display_lottecard_card_loan.json`,
  `display_lottecard_loca_classic.json`). `eval/fixtures/` is gitignored in the public repo, so
  the gold set exists only on a working machine and `tests/domain/evidence_cards/test_gold.py`
  skips when it is absent. The 25 entries were drafted by the coordinator on 2026-09-29
  (`ai_drafted: true`) and still need a person's review.
- `SOURCE_CAP = 300` bounds the one extraction call. The two real pages have 93 and 136 source
  lines, so neither is cut; a page longer than the cap sends only its first 300 lines.
- Card `numbers`/`qualifiers`/`exceptions` are validated as substrings of the card's own `quote`,
  not of the source line. A model could in principle write a `quote` that itself misquotes the
  source in a way `locate_quote` still accepts (e.g. dropping a clause) while keeping internally
  consistent numbers; `locate_quote`'s ignore-whitespace matching does not protect against that.
  This is the same trust boundary `plain_language`'s `verify_source_quote` accepts for its own
  quotes.
