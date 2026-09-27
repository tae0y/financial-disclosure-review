---
ai-generated: true
human-review: false
created: 2026-09-27
---

# product_page

How `preprocess_product_page` turns a URL into the product-specific content the other modules
judge. The entry point is `fetch_product_page(url, ctx)`; everything below happens inside one
worker thread, because sync Playwright objects are bound to the thread that made them.

## The three paths a visit can take

`visit()` decides which path a URL takes by looking for a saved rule for its page family.

| Path | When | Model calls |
|---|---|---|
| reuse | a rule exists, `check_rule` finds no drift, and the replay passes `validate_output` | none |
| rediscover | a rule exists but the page moved past it | the full discovery loop |
| discover | no rule for this host, page family and viewport | the full discovery loop |

`page_family` masks the parts of a URL that identify one product — the last path segment
becomes `*`, numeric folders become `#`, and only query parameter *names* are kept. A rule is
stored per host, family and viewport, so one file covers every product on the same template.

## What a rule stores, and what rejects it

A rule holds `include`/`exclude` selectors, the `steps` needed to reveal hidden content,
2–6 structural `landmarks`, a `name_selector`, and three things measured when it was saved:
`counts` (matches per include), `outside` (structural paths of the text blocks it does not
cover), and `content_chars`.

`check_rule` is the structural gate before a rule is used. It rejects the rule when an include
matches fewer elements than it covered, an expand step matches nothing, a landmark is gone, the
name selector no longer contains the product name, or the page has text blocks on structural
paths the stored signature never saw. A rule with no stored `outside` signature is always
rejected: coverage cannot be established without it.

`validate_output` then checks the replay itself — the product name has to appear, every
`active_includes` selector has to contribute text, the content may not shrink below half of
`content_chars`, and an expand step that matched elements but clicked none is an error.

## What the agent may and may not do

The guards live in the tools, never in the prompt.

- No `fill`, `type`, `evaluate` or download tool exists at all.
- A click is refused by `reject_reason` unless the element is a visible tab, accordion or
  in-page anchor. Form controls, submit/reset/file/password inputs, anything whose text reads
  like apply, login, submit, pay or download, and any navigation link are all refused.
- `PageSession.guard_navigation` aborts any main-frame navigation the code did not ask for, and
  the aborted URLs are reported back to the agent.
- Popups are closed, dialogs dismissed, downloads cancelled.
- `open_link` opens only a plain `a[href]` outside a form, on the same host, over http(s), whose
  path is not a document extension.
- Caps: `max_turns` model turns, `max_visits` page loads, 30 clicks per expand call.

`submit_rule` never writes the rule file. It validates the proposal against the live page and,
on the first clean proposal, nudges the agent twice — once if `inspect_page` reported expandable
controls that were never tried, and once with a sample of the text blocks left outside the
selection. Only code saves the rule, after `finalize_rule` reloads the page and replays the
proposal exactly as a reuse visit would.

## Snapshots

A snapshot is one whole-page capture: every text-bearing element's own text, computed style and
bounds from a CDP `DOMSnapshot`, plus the page HTML written to `data/snapshots/`. The first
capture after arriving is `kind="default"`; later ones are `expanded` or `explore`.

`phase` separates the two jobs. During discovery the phase is `discover`; during
`finalize_rule` and every reuse visit it is `render`, and only `render` snapshots are measured
by `display_check`. Rendered crops of risky text blocks (`capture_visual_samples`) are also
taken only in the `render` phase, so a judgment can be replayed from a checkpoint without the
browser.

A block is flagged `visual_risk` when a CSS background image or gradient applies to it or an
ancestor, or when its bounds overlap a visible `img`. Flat-colour contrast cannot be trusted
for those blocks, which is why the crop is saved.
