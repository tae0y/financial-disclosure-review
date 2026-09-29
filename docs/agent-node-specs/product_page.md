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
- One input is allowed (user decision, 2026-09-29): a checkbox/radio that is a direct child of a
  `.collapse` container and outside every form -- the DaisyUI accordion toggle, which only flips
  CSS. `.collapse-title` and the `.collapse` container are clicked *through* that toggle
  (`CLICK_TARGET_JS`), because the toggle is layered over the title. An already-checked toggle is
  skipped (`already open`) so a second expand never closes a panel.
- Wording (`RISKY_TEXT`) is checked on the control's own label. For an accordion toggle that is
  its title, never the panel it opens. An action noun followed by an information noun
  (`결제일`, `결제 금액`, `신청 방법`, `발급 대상`, …; `INFO_SUFFIX`) is not action wording, so
  "국내외 가맹점 결제일 할인" opens while "결제하기" and "카드 신청" stay refused.
- `PageSession.guard_navigation` aborts any main-frame navigation the code did not ask for, and
  the aborted URLs are reported back to the agent.
- Popups are closed, dialogs dismissed, downloads cancelled.
- `open_link` opens only a plain `a[href]` outside a form, on the same host, over http(s), whose
  path is not a document extension.
- Caps: `max_turns` model turns, `max_visits` page loads, 30 clicks per expand call.

`submit_rule` never writes the rule file. An include selector the agent never probed is still
refused, but the submit probes it itself and returns the result under `probe`, so the next
submit needs no separate probe turn (2026-09-29 F1: a page used all 20 turns alternating submit,
"probe first" and probe). It validates the proposal against the live page and,
on the first clean proposal, nudges the agent twice — once if an open `unexpanded_control` gap
exists and no expand was ever tried, and once with a sample of the text blocks left outside the
selection. Only code saves the rule, after `finalize_rule` reloads the page and replays the
proposal exactly as a reuse visit would.

## Stage 1: coverage gaps and the bounded interaction loop

`domain/product_page/coverage.py` measures the live page (`observe`) and turns that measurement
into a persistent, per-visit list of gaps (`derive_gaps`, stored on `PageSession.gaps`). Gaps are
lexical signals that steer exploration -- they never become a verdict.

- `unexpanded_control`: a control the safety rules would actually let the agent click
  (`reject_reason` on a live `GUARD_JS` read), outside chrome, not yet targeted by a successful
  `interact expand`.
- `hidden_text`: a DOM text block hidden by default. Closes once it is no longer hidden in a
  later `observe()`; starts `unresolved` when no actionable control exists anywhere on the page.
  Hidden means *rendered* hidden (computed `display`/`visibility`/`opacity`, a zero-size box, or a
  zero-height `overflow: hidden` ancestor), not only the `hidden`/`aria-hidden`/inline-style
  attributes: a stylesheet-collapsed accordion is hidden text (fixed after the 2026-09-29 live run,
  where a DaisyUI page read as fully open).
- `benefit_without_condition`: a visible benefit/rate signal with no visible condition/limit
  signal anywhere on the page. Reported only -- never closes the exploration and never changes
  `product_page.status`.
- `image_only`: an `img` whose `alt` reads like disclosure wording. Always `unresolved` -- text
  in an image cannot be measured.

`interact` (`tools.tool_interact`) now requires `gap_id` and `expected_evidence` on
scroll/expand/open_link (`go_back` needs neither); a missing rationale, a repeated
`(action, selector)` on expand/open_link, or an element `reject_reason` would refuse are all
returned as `{"blocked": true, "blocked_reason": "..."}` and logged as such in `agent_trace`. A
repeat immediately closes exploration (`repeated_action`); scroll is exempt from the repeat
check. `expand` may only click an element with `aria-expanded`/`aria-controls`, `<summary>`,
`role=tab`, an `EXPANDER_CLASS` match, or an in-page anchor -- a plain `<button>` with none of
those is refused as "not an expander". `open_link` compares the full origin (scheme, host, port),
not just the hostname. While a click, `open_link` or `go_back` is running
(`PageSession.interacting_window`), every non-GET/HEAD sub-request is aborted and logged as
`blocked_request`; the initial page load is unaffected.

Exploration closes (further `interact` calls are refused with `"exploration closed: <reason>;
submit_rule now"`, while `inspect_page`/`probe_selector`/`submit_rule` keep working) on the first
of: a repeated action (`repeated_action`), `Context.max_interactions` interactions reached
(`interaction_budget`, default 8), `Context.max_no_progress` consecutive interactions with no new
visible text (`no_new_evidence`, default 2), the last 4 model turns starting (`turn_budget`), or
no actionable open gap remaining (`full_coverage`). `Context` does not yet declare
`max_interactions`/`max_no_progress`; `coverage.max_interactions`/`max_no_progress` read them via
`getattr` with the Stage 1 defaults, so adding the fields later needs no code change here.

On an accepted `submit_rule`, `coverage.finalize_coverage` evaluates every `unexpanded_control`/
`hidden_text` gap that falls inside the submitted include/exclude regions. An untried
`unexpanded_control` always counts. A `hidden_text` gap counts only while some control on the
page is still untried; once every reachable control was tried (or none existed), text that is
still hidden is excluded, its gap becomes `unresolved`, and the report lists it as a limitation
(user decision, 2026-09-29). None left -> `product_page.status = "완료"`, `stop_reason =
"full_coverage"`, or `"reachable_coverage"` when unreachable hidden text was excluded. Some left
-> `"조사 불충분"`, with `stop_reason` = the reason exploration closed, else
`"no_viable_control"` or `"submitted_with_gaps"`. `benefit_without_condition` and `image_only`
gaps are reported but never change `status`.

Hidden-text gaps are keyed by selector *and* the block's text: the structural selector of one
accordion panel often matches every panel, so keying by selector alone merged dozens of blocks
into one gap. One `expand` over many accordions closes each control gap whose element the click
actually reached (`MARK_CLICKED_JS` marks clicked elements in a page-side `WeakSet`).

Before every model turn the loop checks the page address. A page that has turned into
Chromium's error page (`chrome-error://`) ends at once as `수집 실패`/`page_unavailable`, with no
further model call (2026-09-29 KB 카드론: the agent spent 20 turns guessing selectors on an error
page). `submit_rule` also sends a proposal back once when unexpanded controls that were never
tried lie inside the submitted regions, even if some other control was tried; this runs only
while exploration is open, and an unchanged resubmit is accepted with the status the gaps give
(2026-09-29 롯데 카드론: accepted with three such controls untried). A control whose element an
earlier expand already reached, under any selector, is not named even if its gap stayed open
(a popup can hide it from the next observation); naming it made the agent repeat the expand and
close exploration as `repeated_action`.

`fetch_product_page` never raises for a page or agent failure; any other Playwright error ends
as `수집 실패`/`fetch_error` with the browser's message (2026-09-29 F1: a KB page reloaded itself
while the arrival scroll ran). The arrival scroll retries once after such a self-reload. It always returns `{url, product,
actions, snapshots, html, status, stop_reason, error, coverage, agent_trace}`. `status` is one of
`완료`, `조사 불충분`, `수집 실패`; `stop_reason` is one of `rule_reused`, `full_coverage`,
`submitted_with_gaps`, `no_viable_control`, `no_new_evidence`, `repeated_action`, `turn_budget`,
`interaction_budget`, `max_turns`, `budget_exhausted`, `fetch_error`, `page_unavailable`,
`visit_cap`, `invalid_url`,
`replay_failed`, `reachable_coverage`. `coverage` is `{before, after, gaps}` (count dicts plus the gap list); `html` is
`""` whenever `status != "완료"`. `discover(sess, ctx, chat=None)` and
`fetch_product_page(url, ctx, chat_factory=None)` accept an injected chat (matching
`llm.client.ToolChat`'s `system`/`user`/`tool_result`/`turn` interface) so tests can script the
model offline; see `tests/domain/product_page/fake_chat.py` and `test_coverage.py`.

Each `agent_trace` entry is `{turn, tool, args, rationale: {gap_id, expected_evidence}, result,
blocked, blocked_reason, new_evidence, coverage_before, coverage_after}`. `result` is exactly the
(now 12,000-character, up from 300) string the model was shown for that call, with `html_path`
and `visual_samples` removed and any base64-looking run over 200 characters replaced by
`<omitted>`, so two runs of the same script produce an identical trace.

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
