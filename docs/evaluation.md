---
ai-generated: true
human-review: false
created: 2026-09-27
updated: 2026-09-30
---

# Evaluation

This page describes what was measured, how each label was obtained, the current results, and what the numbers do not establish.

Every figure comes from a file in `eval/results/`. Cassette-backed figures replay for free:

```bash
uv run python -m financial_disclosure_review evaluate --ablation   # replays the cassette, $0
```

On 2026-09-30 this command replayed all five suites from 104 recorded answers: 74 hits, 0 misses,
$0, about 5 seconds (`eval/results/260930-140141-all-replay.md`). `eval/results/`, `eval/fixtures/`,
`eval/cassettes/` and `tests/fixtures/classify/` hold captured third-party pages and are gitignored.
They ship as `fdr-reproduction-assets-260930.zip`, unpacked at the repository root; without them
the suites stop with `no evaluation cases`.

All current figures use the ad-disclosure criteria and the advice-only output
([ADR-006](architecture-decisions/adr-006-ad-disclosure-instead-of-explanation-duty.md),
[ADR-007](architecture-decisions/adr-007-advice-only.md)).

## Suites

Each suite gets its label from something other than the judgment under test.

| Suite | Question | Label source | Cases | Comparison arm |
|---|---|---|---|---|
| `classification` | Is a real page put in the right product type? | The type each issuer names on its page, copied into the fixture by 영태 | 6 | `keyword`: product-word counts, no model |
| `disclosure-flip` | Is a disclosure removed from the page noticed? | The deletion itself: the sentence is provably gone | 3 + 1 control | `ablation`: one call, no quote check, no condition step, no retry, same deletions |
| `display-flip` | Is a disclosure made too small or too faint noticed, and only that one? | The mutation itself: the measured size or contrast is provably under the threshold | 4 + 2 controls | `rules`: thresholds with no notion of which text is mandatory |
| `plain-contract` | Is a rewrite that drifts from the original caught? (legacy module) | The defect written into each pair | 13 (9 defective, 4 clean) | `mechanical`: numbers, absolutes and quotes only, no model judgment of conditions |
| `stability` | Does the same input get the same answer? | Agreement with itself | 6 pages + 17 disclosure items, 3 rounds | `ablation`: the one-call judgment asked three times |

Why disclosures are measured by deletion and display by mutation:
[ADR-002](architecture-decisions/adr-002-defect-injection-evaluation.md) and
[ADR-005](architecture-decisions/adr-005-display-flip-evaluation.md).

## Results

### Classification — 6/6, keyword baseline also 6/6

| Arm | Correct | Notes |
|---|---|---|
| `pipeline` (gpt-5-mini, three quoted stages) | 6/6 | A reason on every page; 8 calls, $0.0354 |
| `keyword` (product-word counts) | 6/6 | No model call |

- Two of the six pages are out of scope (삼성화재 자동차보험, 카카오뱅크 정기예금). The pipeline rejected
  both at stage 2, and the verification call agreed.
- The baseline tie describes the set, not a success: every page names its type in its title, so
  counting words is enough. Pages that paraphrase or mention several products are not in the set
  ([ADR-003](architecture-decisions/adr-003-staged-classification.md)).
- `uv run python eval/out_of_scope_report.py` replays the out-of-scope path offline and renders
  the report through the same `build_report` the graph uses.

### Ad disclosures by defect injection — 20/33 in both arms, quotes 574/574 against 529/743

A target is an item both arms judged 적합 on the unedited page. Its deletion removes every quote
either arm gave for it; the item should then turn 부적합. A control deletes one unrelated sentence.

**Single page.** 롯데카드 디지로카 Las Vegas (public page, 5,667 characters of text), 17 A·B·C items
that apply to a 신용카드 상품광고. Deletions: A04 (연체이자율), A10 (per-payment discount-rate table),
A13 (원리금 변제 의무 경고).

| Metric | `pipeline` | `ablation` |
|---|---|---|
| Deleted disclosures caught as 부적합 | **2/3** (A04, A13) | 2/3 (A04, A13) |
| Quotes found on the page | **56/56 (100%)** | 50/68 (73.5%) |
| Quotes found on the page, base run | **15/15 (100%)** | 13/17 (76.5%) |
| Control false flips | 1 (A08) | 0 |
| Base verdicts (적합 / 부적합 / 판정 불가) | 15 / 1 (B01) / 1 (A09) | 15 / 1 (A05) / 1 (A09) |

Source: `eval/results/260930-135417-disclosure-flip-record.json`, replayed in
`eval/results/260930-140141-all-replay.json`.

**Five pages.** Three deletions give a 95% interval of 21–94% for 2/3, too wide to conclude
anything, so the same suite (same prompts, arms and code) ran on five pages from three card
companies and four product types, up to 8 deletions and 2 controls per page
(`eval/disclosure_flip_multi.py`, cases in `eval/cases/disclosure_flip_multi.json`). Recording
took 106 calls, $1.008 and about 14 minutes; the pooled replay is free, 8 seconds, 0 misses.

| Page (product type) | Deleted | Caught pipeline / ablation | Controls flipped | Quotes on page |
|---|---|---|---|---|
| Lotte Las Vegas (신용카드) | 8 | 5 / 5 | 2/2 / 0/2 | 139/139 / 121/169 |
| Shinhan Hi-Point Plan (신용카드) | 8 | 5 / 4 | 1/2 / 0/2 | 148/148 / 143/170 |
| Samsung rate-cut request (장기카드대출) | 1 | 1 / 1 | 0/2 / 1/2 | 7/7 / 7/54 |
| Shinhan revolving (리볼빙) | 8 | 4 / 5 | 0/2 / 0/2 | 134/134 / 117/170 |
| Lotte auto installment (할부금융·리스) | 8 | 5 / 5 | 0/2 / 0/2 | 146/146 / 141/180 |
| **Total** | **33** | **20 / 20** (61%, 95% CI 44–75%) | **3/10 / 1/10** | **574/574 / 529/743** |

- Detection is a tie at eleven times the sample. The validation steps do not raise it.
- The pipeline's effect is on evidence: all 574 of its quotes are on the page, against 71% of the
  ablation's. Without the quote check, 214 of 743 quotes (29%) are not on the page.
- The pipeline flips more controls (3/10 against 1/10): A08 twice and B01 once, the same two items
  that are unstable across rounds (see Stability).
- All 13 misses passed on another sentence still on the edited page. Six are company or product
  name items (A02, A03) whose names appear all over the page, so those deletions carry no valid
  label. The other seven need a person to decide whether the remaining sentence meets the
  criterion.

Source: `eval/results/260930-150207-disclosure-multi-all-replay.{json,md}`.

### Display method by mutated measurements — 4/4 caught, 0/2 controls blamed

Two real reviews (롯데카드 LOCA MONEY 장기카드대출, LOCA CLASSIC 신용카드) are the base. One block at a
time is shrunk to 9px (6.75pt, under the rubric's 8pt) or faded to rgb(204,204,204) (about 1.6:1
on white, under 4.5:1). Targets are mandatory disclosures chosen from the rubric's required
wording: A01 (설명서·약관 확인 권유), A11 (신용평점 하락 경고), A13 (원리금 변제 의무 경고). Controls
change marketing copy the same way.

| Metric | `pipeline` | `rules` |
|---|---|---|
| Injected defect judged 부적합, citing that block | **4/4** | 4/4 |
| Control block blamed | **0/2** | 2/2 |
| Base verdicts (card-loan E02 / loca-classic E04) | 적합 / 적합 | 적합 / 적합 |

- Thresholds alone catch every defect, and for the same reason also fail the marketing copy. The
  pipeline adds the step that tells a mandatory disclosure from other text.
- With E02/E04/E05 decided by code, the re-recording gives the same result at $0.0834 instead of
  $0.2019 (`eval/results/260929-091909-display-flip-record.md`).

Source: `eval/results/260928-190811-display-flip-record.json`.

### Plain-language contract (legacy module) — 9/9 caught, 0/4 false alarms

This suite measures the line-by-line rewrite checks of [plain_language](agent-node-specs/plain_language.md),
which the current graph does not call. The current counterpart is the advice check below.

| Metric | Pipeline (condition judged by the model) | `mechanical` arm |
|---|---|---|
| Injected defects caught | **9/9** | 7/9 |
| False alarms on clean pairs | **0/4** | 0/4 |

The `mechanical` arm misses the two pairs that drop a condition (`condition-dropped-threshold`,
`condition-dropped-penalty`).

Source: `eval/results/260928-183438-plain-contract-record.json`.

### Stability — classification steady, ad disclosures 15/17 in both arms

Round 1 is the recording the other suites use; rounds 2–3 are salted repeats.

| Question | `pipeline` | `ablation` |
|---|---|---|
| Classification of the six pages | **6/6** | Keyword baseline is code and never varies |
| Ad-disclosure verdicts on the base page (17 items) | 15/17 (88.2%) | 15/17 (88.2%) |
| Unstable items, 적합 ↔ 부적합 | 2 (A08 적합·적합·부적합, B01 부적합·부적합·적합) | 2 (A05, B02) |
| Unstable items through 판정 불가 | 0 | 0 |

- Every disagreement is an outright 적합 ↔ 부적합 contradiction, not a hand-off to 판정 불가.
- A08 and B01 are two of the three items the live run of the same page reported as 부적합 on
  2026-09-30. A single run's findings on them are not reproducible; a reviewer should check them
  first.

Source: `eval/results/260930-135741-stability-record.json`.

### Evidence cards and reader advice — advice shown on 2/2 pages, 10/10 injected defects rejected

`uv run python eval/cards_persona_eval.py [--record]` runs on two real Lotte Card pages against a
25-entry gold set (`eval/fixtures/gold/evidence_cards.json`, AI-drafted). The advice is written
for a 70s reader with low finance familiarity (`nemotron-ko-70s-lowfin`).

| Measure | 카드론 (131 sources) | LOCA CLASSIC (89 sources) |
|---|---|---|
| Cards kept / rejected by code | 45 / 0 | 28 / 0 |
| Card quote resolves in its source | 45/45 | 28/28 |
| Gold quotes covered (risk-only) | 11/12 (10/11) | 10/13 (9/12) |
| Advice passes its code checks and is shown | Yes (336 chars) | Yes (297 chars) |
| Items the advice points to | 설명02·04·21·23 | 설명02·10·16·23 |
| Injected advice defects rejected (invented number, verdict word, code in text, over length, unknown code) | 5/5 | 5/5 |

- **Repeat stability** (`eval/agentic_stability.py`, three rounds): the advice passed its checks
  in every round on both pages (6/6). The items vary: pairwise Jaccard of `advice_codes` is
  0.33 / 0.33 / 1.00 on 카드론 and 0.75 / 0.60 / 0.75 on LOCA CLASSIC. Only 설명02 (상환방법)
  appears in every round. Card extraction itself varies (Jaccard 0.37–0.53).
- **Two readers, same page** (`eval/persona_pair_eval.py`): a 70+ low-familiarity reader and a
  40s bank/insurance worker. Both advices pass on both pages; item overlap is 0.60 on 카드론 and
  0.29 on LOCA CLASSIC.
- No person has scored the advice, so whether a different list is a better list for that reader
  is not measured.

Sources: `eval/results/260930-135827-cards-persona-record.json`,
`260930-135938-agentic-stability-record.json`, `260930-140114-persona-pair-record.json`.

### Live pages and the page agent

The page agent and the full graph ran on seven live pages from five issuers
(`eval/agent_loop_eval.py`, $0.15 cap per page). Every thread gets one outcome, and a run whose
budget runs out after collection still ends in a 판정 불가 report naming the interrupted node
([agentic behavior audit](../data/agentic-behavior-audit.md)).

| Page | Collection |
|---|---|
| 롯데 디지로카 Las Vegas (mobile) | 완료 / full_coverage |
| 신한 Hi-Point | 완료 / reachable_coverage |
| 삼성 카드론 | 완료 / full_coverage |
| 신한 리볼빙 | 조사 불충분 / no_viable_control |
| 현대 카드론 | 조사 불충분 / submitted_with_gaps |
| 롯데 카드론 (PC) | 조사 불충분 / submitted_with_gaps, 22/26 gaps closed |
| KB 카드론 | 수집 실패 / page_unavailable, 0 model turns |

| Measure | Result |
|---|---|
| Reports produced | 7/7 |
| Collection 완료 | 3/7 |
| In-region gap closure | 51.0% (123/241) |
| Collection and judgment both finished | 1/7 |

- Four pages ran out of the $0.15 cap during judgment and ended in a 판정 불가 report. Pages that
  finished judgment spent $0.18–0.22, so the cap, not the agents, set the last row.
- The live run on 디지로카 Las Vegas under the current criteria (18 calls, $0.1085, 305 s) collected
  the page to `full_coverage` with 0 open gaps and judged 표시방법 적합 4/8 and 의무표시 적합 14/17
  (A08, A09, B01 부적합).
- On 2026-09-30 at 18:00 KST the same five pages used for defect injection were submitted through
  the deployed web front end: URL and reader text ("70대, 금융 경험 적음") typed into the form, the
  result awaited, and the report saved with the "Markdown 저장" button (Playwright). Three ran end
  to end; 신한 리볼빙 and 롯데 오토할부 failed on the first model call because the OpenAI credit ran
  out (`429 credit_balance_exhausted`), which the front end showed as "검토에 실패했습니다" and which
  ended the job without a 판정 불가 report.

| Page | Time | Calls, cost | Collection | 표시방법 적합 | 의무표시 적합 | Download |
|---|---|---|---|---|---|---|
| 롯데 디지로카 Las Vegas | 215.9 s | 9, $0.0701 | 완료, saved rule reused | 5/8 | 16/16 | 4,410 bytes |
| 삼성 금리인하요구 (장기카드대출) | 108.4 s | 9, $0.0398 | 완료, saved rule reused | 1/8 (5 판정 불가) | 2/16 (11 부적합) | 9,954 bytes |
| 신한 Hi-Point | 374.5 s | 24, $0.1439 | 완료 / reachable_coverage, re-explored | 3/8 (4 판정 불가) | 16/16 | 4,957 bytes |

  Across the five live runs under the current criteria (two on Las Vegas, these three) a review
  took 108–375 s (median 305 s) and cost $0.040–$0.144 (median $0.091). A08 and B01 on Las Vegas,
  부적합 in the earlier run, came out 적합 here; they are the two items that move under repetition.
  Files: `data/live7/` (screenshots, downloaded reports, API responses; shipped in the asset zip).

Sources: `eval/results/260929-140148-agent-loop.md` (seven pages) and
`260929-141601-agent-loop.md` (reruns of 신한 Hi-Point and 현대 카드론); per-page reports and the
pooled gap closure in `data/audit-remeasure-260929/`.

## Model comparison

The same cassette-backed suites run with `--model`; each model has its own cassette. The
duty-flip rows use the earlier explanation-duty criteria; other models were not re-run on
`disclosure-flip`.

| Suite | gpt-5-mini (default) | gpt-5-nano | gpt-5 |
|---|---|---|---|
| classification (6 pages) | **6/6** · 8 calls · $0.0354 · 104 s | 4/6 · 11 calls · $0.0244 · 350 s | 5/6 · 9 calls · $0.1903 · 184 s |
| duty-flip, pipeline arm (earlier criteria) | **1/3**, quotes 67/67 | 0/3, quotes 47/47 | Not run |
| duty-flip, ablation arm (earlier criteria) | 1/3, quotes 45/156 | 0/3, quotes 59/127 | Not run |
| plain-contract | 9/9, 0/4 false alarms | 9/9, 0/4 | 9/9, 0/4 |

- gpt-5 rejected the auto-installment page (할부금융·리스) as out of scope. gpt-5-nano rejected the
  card-loan page (장기카드대출) as out of scope and returned 판정 불가 for the insurance page. An
  in-scope page rejected as out of scope is the costliest error, because it is never reviewed.
- gpt-5-nano wrote about three times gpt-5-mini's output tokens on the judgments, took 38 minutes
  and detected none of the deleted disclosures.

Files: `eval/results/*-gpt-5-nano.*`, `eval/results/*-gpt-5.*`.

## Recording cost

`--record` calls the model only for questions the cassette does not hold. A suite whose prompt or
model changes needs its answers recorded again.

All gpt-5-mini recordings from 2026-09-27 to 2026-09-30 total 104 calls and $1.1241; the largest
were the display-flip pipeline arm (19 calls, $0.2019) and the first duty-flip recording (11
calls, $0.2166). The 2026-09-30 re-measurement under the current criteria, including the three advice scripts,
cost $0.2331 (26 calls). Each recording has a matching file in `eval/results/`.

## Failure analysis

Each finding is traced to a cause rather than left as a rate.

- **The A10 miss is a label problem.** After the per-payment discount-rate table was deleted, the
  pipeline kept 적합 on another table still on the page that states the same rates
  (`missed_with_evidence_on_page: A10`). When a fact appears twice, "deleted, therefore 부적합" does
  not hold. Next step: limit targets to facts the page states once.
- **Two of the three single-run 부적합 findings are unstable.** The live run of 2026-09-30 reported
  A08 (validity period), A09 (statistics source) and B01 (credit-score basis) as 부적합. Across
  rounds A08 went 적합·적합·부적합 and B01 부적합·부적합·적합, and A08 also flipped on the control.
  Next step: ask these two items three times and confirm only on agreement.
- **A09 is likely a false positive.** Both arms returned 판정 불가 on the base run. The live run read
  the discount table as a cited statistic and failed it for a missing source; a benefit-condition
  table is not a statistic. Next step: narrow what counts as a cited statistic in the condition step.
- **The two arms fail different items on the base page.** The pipeline failed B01 and the ablation
  A05, and 4 of the ablation's 17 base-run quotes were not on the page. With equal detection, the
  share of evidence a reviewer can check is 100% against 77%.
- **E01's verdict contradicted its reason.** On the same page, one run judged E01 적합 while its
  reason described benefits at 30–36pt against drawbacks at 9–13.5pt, which is the imbalance the
  item asks about. Next step: take a yes/no answer to the criterion question and let code set the
  verdict direction, then check that reason and verdict agree.
- **The keyword baseline also scored 6/6.** Every page names its type in the title, so the set is
  easy. Pages that mention several products or hide the type are needed to separate the two
  methods.
- **The plan's cost estimate was low.** The plan assumed about $0.0061 per product. Three full
  reviews on 2026-09-28 cost $0.148–$0.193 (median $0.184, about 258 KRW), 20–24 calls and
  513–723 s (`eval/results/260928-191135-cost-ledger.md`); output tokens were the cause. The live
  run under the current criteria cost 18 calls, $0.1085, 305 s, 31,217 output tokens.

## Limits

- The samples are small: 6 classification pages, 3 + 33 disclosure deletions, 2 display pages with
  4 injections and 2 controls, 13 plain-language pairs. The rates are directions, not performance
  figures.
- Only 1 of 7 live pages finished both collection and judgment. Replay figures describe stored
  pages, not the completion rate on live pages.
- A 100% quote rate means the quote is on the page, not that it meets the criterion. Lotte
  auto-installment A12 passed a deleted credit-score warning on a different sentence.
- Only the deletion direction is measured. Adding a missing disclosure is not.
- The display suite mutates measurements; it does not re-render the page. Crops were not exported,
  so text inside images stays 판정 불가 in both arms.
- 2 of 17 ad-disclosure items (12%) change verdict on the same input. Do not read a single run as a
  final verdict.
- The items the advice points to change between runs (Jaccard 0.33–1.00). No person has scored the
  advice, and the evidence-card gold set is an AI draft.
- Classification labels and prompts were both written by 영태; no second person has cross-checked
  them.
- `plain-contract` measures a module the current graph does not call, on hand-written pairs.
- No evaluation with injected instructions has been run (see [operations](operations.md)).

## Add a case

1. Classification: add `tests/fixtures/classify/<case>.json` with `{url, product, html, expected}`.
1. Defect injection: adjust `prefer_codes` (A·B·C codes) in `eval/cases/disclosure_flip.json`, or
   point `base_html` at another collected page.
1. Display method: add `{id, kind, rubric, text}` to `pages[].cases` in
   `eval/cases/display_flip.json`. `rubric: null` makes a control. For a new page, export a real
   review's `product_page` to `eval/fixtures/display_*.json`.
1. Plain language: add `{id, defect, expect_marker, source_quote, rewrite}` to
   `eval/cases/plain_contract.json`. `defect: null` makes a clean control.
1. After changing a prompt or model, re-record the affected suites with `--record`.
