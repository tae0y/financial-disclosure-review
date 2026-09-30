---
ai-generated: true
human-review: false
created: 2026-09-27
updated: 2026-09-30
---

# Evaluation

What was measured, on which data, with which labels, and what the numbers do not cover. Every
figure here comes from a file in `eval/results/`, and every cassette-backed one can be re-derived
for free:

```bash
uv run python -m financial_disclosure_review evaluate --ablation   # replays the cassette, $0
```

> **2026-09-30 — re-measured under the current criteria.** The explanation-duty check became
> the ad-disclosure check (A·B·C mandatory ad disclosures instead of 설명의무 by analogy), and the
> reader explanation became one paragraph of advice on what to check before signing
> ([ADR-006](architecture-decisions/adr-006-ad-disclosure-instead-of-explanation-duty.md),
> [ADR-007](architecture-decisions/adr-007-advice-only.md)). The `duty-flip` suite is now
> `disclosure-flip` (`eval/cases/disclosure_flip.json` v2) and the stability suite repeats the 17
> disclosure items. Both were recorded again on 2026-09-30 at commit `f6e79e2`, and the three
> advice scripts (`eval/cards_persona_eval.py`, `agentic_stability.py`, `persona_pair_eval.py`)
> recorded their advice answers again; the paid total was $0.2331 (26 calls). Results:
> disclosure deletions caught 2/3 in both arms (§2), disclosure verdicts stable on 15/17 items in
> both arms (§5), reader advice shown on both pages with 10/10 injected advice defects rejected
> (§6). Explanation-duty, unit and fact-ledger figures are kept below under "이전 기준" headings as
> history, not as results of the current code.

`eval/results/`, `eval/fixtures/`, `eval/cassettes/` and `tests/fixtures/classify/` hold captured
third-party pages and are gitignored; they ship in the submission zip
(`fdr-reproduction-assets-260929.zip`, unpacked at the repository root). Without them the
classification and stability suites stop with `no evaluation cases` instead of reporting an
empty score.

The current figures are from the 2026-09-30 recordings (`eval/results/260930-135417-disclosure-flip-record.md`,
`eval/results/260930-135741-stability-record.md`); classification, display-flip and
plain-contract did not change and replay their earlier answers. On 2026-09-30 the command above
replayed all five suites from 104 recorded answers — 74 hits, 0 misses, $0, about 5 seconds
(`eval/results/260930-140141-all-replay.md`). A suite whose prompt or model changes needs its
answers recorded again; `--record` calls the model only for the questions the cassette does not
hold. What the recordings cost:

| Recording | Calls | Cost | Time | File |
|---|---|---|---|---|
| classification (2026-09-27) | 8 | $0.0354 | 104 s | `eval/results/260927-174210-classification-record.md` |
| duty-flip, both arms, first target rule (2026-09-27) | 11 | $0.2166 | 802 s | `eval/results/260927-175540-duty-flip-record.md` |
| duty-flip, shared deletions (2026-09-28) | 4 | $0.0727 | 352 s | `eval/results/260928-201247-duty-flip-record.md` |
| plain-contract condition judgment (2026-09-28) | 1 | $0.0021 | 13 s | `eval/results/260928-183438-plain-contract-record.md` |
| stability, rounds 2–3 (2026-09-28) | 23 | $0.1657 | 646 s | `eval/results/260928-184936-stability-record.md` |
| display-flip pipeline arm (2026-09-28) | 19 | $0.2019 | 712 s | `eval/results/260928-190811-display-flip-record.md` |
| stability, ablation rounds 2–3 (2026-09-28) | 2 | $0.0288 | 143 s | `eval/results/260928-201825-stability-record.md` |
| display-flip, E02/E04/E05 decided by code (2026-09-29) | 10 | $0.0834 | 205 s | `eval/results/260929-091909-display-flip-record.md` |
| all suites after partial re-asking (2026-09-29) | 10 | $0.1482 | 555 s | `eval/results/260929-190829-all-record.md` |
| disclosure-flip, both arms, ad-disclosure criteria (2026-09-30) | 12 | $0.1236 | 484 s | `eval/results/260930-135417-disclosure-flip-record.md` |
| stability, disclosure rounds 2–3 (2026-09-30) | 4 | $0.0458 | 161 s | `eval/results/260930-135741-stability-record.md` |
| **Total for gpt-5-mini** | **104** | **$1.1241** | | |

Answers recorded under an earlier prompt or target rule that the current code no longer asks for
stay in the cassette unused; a replay never reads them.

The model comparison (other models on the same suites) is recorded in its own cassettes; see
§Model comparison.

## Five suites, five kinds of label

| Suite | Question | Label source | Cases | Comparison arm |
|---|---|---|---|---|
| `classification` | Is a real page put in the right product type? | the product type each issuer names on its page, written into the fixture by 영태 | 6 | `keyword`: count product words, no model |
| `disclosure-flip` (was `duty-flip`) | Is a disclosure that left the page noticed? | the deletion itself — the sentence is provably gone | 3 + 1 control | `ablation`: one call, no quote check, no condition step, no retry — on the same deletions |
| `display-flip` | Is a disclosure made too small or too faint noticed, and only that one? | the mutation itself — the measured size or contrast is provably under the threshold | 4 + 2 controls | `rules`: thresholds with no notion of which text is mandatory |
| `plain-contract` | Is a rewrite that drifts from the original caught? (the 2026-09-28 plain-language checks; see §4) | the defect written into each pair | 13 (9 defective, 4 clean) | `mechanical`: numbers, absolute phrases and quotes only, no model judgment of conditions |
| `stability` | Does the same input get the same answer? | agreement with itself, no label | 6 pages + 17 disclosure items (39 explanation-duty items before 2026-09-30), 3 rounds | `ablation`: the one-call judgment asked three times (the keyword classifier is code and never varies) |

Why the disclosure check is measured by deletion and the display method by mutation is recorded
in `docs/architecture-decisions/adr-002-defect-injection-evaluation.md` and `docs/architecture-decisions/adr-005-display-flip-evaluation.md`.

## Results

### 1. Classification — 6/6, and the keyword baseline also 6/6

| Arm | Correct | Notes |
|---|---|---|
| `pipeline` (gpt-5-mini, three quoted stages) | 6/6 | a reason on every page; 8 calls, $0.0354 |
| `keyword` (product-word counts) | 6/6 | no model call |

Two of the six are out-of-scope pages (삼성화재 자동차보험, 카카오뱅크 정기예금); the pipeline
rejected both at stage 2 with the second verification call agreeing.

The baseline matching the pipeline is a finding about the set, not a success: every page names its
own type in its title ("LOCA MONEY-장기카드대출", "일부결제금액이월약정(리볼빙)"), so counting words is
enough. The reason keywords were rejected on 2026-09-10 — pages that paraphrase or mention several
products — is not represented in these six pages and remains untested
(`docs/architecture-decisions/adr-003-staged-classification.md`).

The out-of-scope path is demonstrable without a network:
`uv run python eval/out_of_scope_report.py` replays the recorded calls and renders the report
through the same `build_report` the graph's `end_report` node uses.

### 2. Ad disclosures, defect injection — pipeline 2/3, ablation 2/3 on the same deletions

Base page: 롯데카드 디지로카 Las Vegas 상품안내 화면 (공개 페이지, 본문 5,667자), judged on the 17 A·B·C
mandatory ad disclosures that apply to a 신용카드 상품광고. Both arms judge the same deletions and the
same control: a target is an item both arms judged 적합 on the unedited page, and its deletion
removes every quote either arm gave for it that is on the page. The deletions:
A04 (연체이자율), A10 (건당 결제 금액별 할인율 표), A13 (원리금 변제 의무 경고).

| Metric | `pipeline` | `ablation` |
|---|---|---|
| 삭제한 의무표시를 부적합으로 잡아냄 | **2/3** (A04, A13) | 2/3 (A04, A13) |
| 미탐 중 삭제 뒤에도 본문에 있는 다른 근거를 댄 경우 | A10 | 확인 불가 |
| 인용 유효율 (인용문이 실제로 본문에 있음) | **56/56 (100%)** | 50/68 (73.5%) |
| 기준 실행의 인용 유효율 | **15/15 (100%)** | 13/17 (76.5%) |
| 대조군(무관 문장 삭제) 오탐 | 1건 (A08) | 0건 |
| 판정 불가로 보류한 항목 (기준 실행) | 1 (A09) | 1 (A09) |
| 기준 판정 분포 (적합/부적합/판정 불가) | 15 / 1 (B01) / 1 | 15 / 1 (A05) / 1 |

Detection is a tie; the difference is again the evidence. Every quote the pipeline gives is on
the page, against 74% of the ablation's, and the two arms disagree on which item fails on the
unedited page (pipeline B01, ablation A05). A10 was missed by both arms for the same reason F12
was under the old criteria: after the table was deleted, the pipeline passed A10 on another part
of the page that still states the per-payment discount rates, so "deleted, therefore 부적합" does
not hold for that case. The pipeline's one control flip (A08, 광고·심의필 유효기간) is on an item that
also changes verdict across the stability rounds (§5). Source:
`eval/results/260930-135417-disclosure-flip-record.json`, replayed in
`eval/results/260930-140141-all-replay.json`.

#### 이전 기준 — explanation duty by analogy (2026-09-27 – 09-29)

Measured before ADR-006 on the same page with 39 explanation-duty items; kept as history.

Both arms judge the same three deletions and the same control. A target is an item both arms
judged 적합 on the unedited page; its deletion removes every quote either arm gave for it that is on
the page, and an item whose sentence an earlier deletion already removed is skipped. The
deletions: F07 (연체이자율), F11 (연회비), F12 (L.POINT 설명).

| Metric | `pipeline` | `ablation` |
|---|---|---|
| 삭제한 설명을 부적합으로 잡아냄 | **2/3** (F07, F11) | 1/3 (F11) |
| 미탐 중 삭제 뒤에도 본문에 있는 다른 문장을 근거로 댄 경우 | F12 | 확인 불가 (인용이 본문에 없음) |
| 인용 유효율 (인용문이 실제로 본문에 있음) | **64/64 (100%)** | 27/156 (17.3%) |
| 기준 실행의 인용 유효율 | **16/16 (100%)** | 14/39 (35.9%) |
| 대조군(무관 문장 삭제) 오탐 | 2건 (F09, 설명09) | 0건 |
| 판정 불가로 보류한 항목 (기준 실행) | 6 | 2 |
| 기준 판정 분포 (적합/부적합/판정 불가) | 16 / 17 / 6 | 18 / 19 / 2 |

The pipeline catches two of the three deletions and the ablation one. With three cases this is
not a stable difference: the 2026-09-28 recording, before partial re-asking, had both arms at 1/3,
and a re-recording alone can move the pipeline between 1/3 and 2/3. The steadier difference is
the evidence: every quote the pipeline gives is on the page, against 17% of the ablation's. A
reviewer can check a pipeline finding in the page and cannot check most ablation findings. The
cost is two control false flips (F09, 설명09) the ablation did not make; both items also moved
to 부적합 once in the stability rounds (§5). Source: `eval/results/260929-190829-all-record.json`,
replayed in `eval/results/260929-212416-all-replay.json`.

> **Correction (2026-09-29).** Until this date this section reported both arms at 1/3 with
> quotes 67/67 against 45/156 and control flips F13·설명13 (`260928-201247-duty-flip-record`), and
> read the result as "detection is a tie; the difference is the evidence". After `1964aae`
> re-asks only the rejected codes, the re-recording changed the targets (F07·F11·F12 instead of
> F07·F15·설명12) and the numbers above. The tie reading no longer holds; the small sample does.

> **Correction (2026-09-28).** This section used to report pipeline 2/3 against ablation 1/3
> (`260927-175540-duty-flip-record`). That was not a comparison on the same cases: each arm chose
> its deletions from its own answers — the pipeline deleted F07·F15·설명07, the ablation
> 설명07·F06·설명06 — and in each arm two of the three rows deleted one sentence (F07 and 설명07;
> F06 and 설명06). The target rule was fixed in `9101c9a` and both arms were recorded again.

### 3. Display method, mutated measurements — 4/4 caught, 0/2 controls blamed

Two real reviews of 2026-09-28 (롯데카드 LOCA MONEY 장기카드대출, LOCA CLASSIC 신용카드) are the base.
One block at a time is shrunk to 9px (6.75pt, under the rubric's 8pt) or faded to rgb(204,204,204)
(about 1.6:1 on white, under 4.5:1). Targets are mandatory disclosures chosen from the rubric's
required wording, not from the model's labels: A01 (설명서·약관 확인 권유), A11 (신용평점 하락 경고),
A13 (원리금 변제 의무 경고). Controls change marketing copy the same way.

| Metric | `pipeline` | `rules` |
|---|---|---|
| 주입한 위반을 해당 블록을 지목해 부적합으로 판정 | **4/4** | 4/4 |
| 대조군 블록을 위반으로 지목 | **0/2** | 2/2 |
| 기준 판정 (card-loan E02 / loca-classic E04) | 적합 / 적합 | 적합 / 적합 |

Code alone catches every injected defect because it fails anything under the threshold — and for
the same reason it fails the marketing copy. What the pipeline adds is the step that tells a
mandatory disclosure from other text. Source: `eval/results/260928-190811-display-flip-record.json`.

The same run shows the effect of a fix made the same day. The original LOCA CLASSIC review failed
E02 on the product-name heading, measured at 0pt: its words sit in the DOM at font-size 0 while
the reader sees them as an image. With undrawn text kept out of the size rule
(`docs/agent-node-specs/display_check.md`), the base run now reads E02 판정 불가 on that page — unmeasurable, neither
a pass nor a failure.

### 4. Plain-language contract — 9/9 caught, 0/4 false alarms (2026-09-28 structure)

This suite measures `domain/plain_language` (`verify_block`, `judge_condition_preservation`), the
line-by-line rewrite of the 2026-09-28 graph. Since the 2026-09-29 merge the graph writes a
persona explanation instead and calls neither function, so this suite is kept as a record, not as
evidence about the current graph. The current counterpart is the advice check in §6 (10/10
injected advice defects rejected, 2026-09-30); the fact-ledger results in §6–§7 describe the
line-by-line output that ADR-007 removed.

| Metric | 2026-09-27, before the fix | 2026-09-27, after | 2026-09-28, condition judged by the model | 2026-09-29, `mechanical` arm |
|---|---|---|---|---|
| 주입 결함 적발 (재현율) | 9/9 | 9/9 | **9/9** | 7/9 |
| 무결함 대조군 오탐 | 2/4 (50%) | 0/4 | **0/4** | 0/4 |

The `mechanical` arm runs the same pairs with the model judgment of conditions removed; it misses
the two pairs that drop a condition (`condition-dropped-threshold`, `condition-dropped-penalty`).
Until 2026-09-29 this comparison was written as "no contract check = 0/9", which was inferred, not
run.

The first run found two defects in the contract layer itself, both fixed with regression tests in
`tests/domain/plain_language/test_contract.py`:

- `clean-annual-fee`: "연회비 20,000원" → "1년에 20,000원" counted the `1` as an invented number.
  Only a `1` before a period or count unit is exempt now.
- `clean-late-payment`: the `제일` inside "결제일에" counted as a superlative. A short, ambiguous
  phrase glued to a preceding Hangul syllable is read as part of another word.

On 2026-09-28 the condition-and-exception check moved from a keyword scan to a model judgment
(`judge_condition_preservation`, `docs/agent-node-specs/plain_language.md`) because correct synonym swaps looked like
omissions. The suite was re-recorded the same day (one call, $0.0021) with the same result.
Before/after files: `260927-173641-plain-contract-replay.before-fix.json`,
`260927-173802-plain-contract-replay.json`, `260928-183438-plain-contract-record.json`.

### 5. Stability — classification steady, ad disclosures 15/17 in both arms

Round 1 is the recording the other suites use; rounds 2–3 are salted repeats from the same
cassette. Figures are from the 2026-09-30 recording (`eval/results/260930-135741-stability-record.json`).

| Question | `pipeline` | `ablation` |
|---|---|---|
| Classification of the six pages | **6/6** | the keyword baseline is code: the same answer every time |
| Ad-disclosure verdicts on the base page (17 items) | 15/17 (88.2%) | 15/17 (88.2%) |
| — unstable items moving only between 적합 and 부적합 | 2 (A08 적합·적합·부적합, B01 부적합·부적합·적합) | 2 (A05, B02) |
| — moving through 판정 불가 | 0 | 0 |

Both arms agree with themselves on 15 of 17 items, and every disagreement is an outright 적합 ↔
부적합 contradiction, not a hand-off to 판정 불가. The two unstable pipeline items are the ones the
live run of the same page reported as 부적합 on 2026-09-30 (A08, B01; A09 was the third,
`data/live6/review-report-2026-09-30-lasvegas-advice.md`), so those findings from a single run are
not reproducible and a reviewer should check them first. Under the old criteria about a quarter of
the items moved (9/39, next subsection); under the ad-disclosure items it is 2/17 (12%).

#### 이전 기준 — explanation duty by analogy (2026-09-29 19:08 recording)

| Question | `pipeline` | `ablation` |
|---|---|---|
| Classification of the six pages | **6/6** | the keyword baseline is code: the same answer every time |
| Explanation-duty verdicts on the base page (39 items) | 30/39 (76.9%) | **31/39 (79.5%)** |
| — unstable items moving only between 적합 and 부적합 | **2** (F09, 설명09) | 6 (F13, F17, F18, 설명13, 설명17, 설명18) |
| — moving through all three verdicts | 2 (F13, 설명13) | 0 |
| — moving between 판정 불가 and 적합 | 4 (F05, F14, 설명14, 설명22) | 0 |
| — moving between 판정 불가 and 부적합 | 1 (설명21) | 2 (F01, 설명01) |

The one-call arm agrees with itself slightly more often. When the pipeline does not agree, seven
of nine times the item passes through 판정 불가 — handing it to a person; six of the ablation's
eight contradict themselves outright between 적합 and 부적합. The split by kind was chosen after the
agreement rates were seen, so the agreement rate stays the headline, and on it the ablation is
ahead. A reviewer's to-do list from a single run is not reproducible for about a quarter of the
explanation-duty items. Source: `eval/results/260929-190829-all-record.json`.

> **Correction (2026-09-29).** Until this date this section reported 28/39 against 31/39, with
> eleven unstable items, eight of them between 판정 불가 and 적합
> (`260928-184936-stability-record`, `260928-201825-stability-record`).

> **Case linking removed (2026-09-30).** Case search and case linking were removed from the
> workflow by the user's decision: the reference-case node never fed a judgment, and after the
> 2026-09-30 short report the report did not show cases either. Its measurements are dropped from
> §6–§8 with the feature. The judging suites (§1–§5) never read cases and are unaffected.

### 6. Evidence cards and reader advice — advice shown on 2/2 pages, 10/10 injected defects rejected (2026-09-30)

`uv run python eval/cards_persona_eval.py [--record]` runs on the two real lottecard pages in
`eval/fixtures/` against a 25-entry gold set in `eval/fixtures/gold/evidence_cards.json` (both
local only: `eval/fixtures/` is gitignored). Since ADR-007 the reader output is one paragraph of
advice (`advice`, `advice_codes`: which 설명의무 items to check in the product document before
signing), written for a 70s reader with low finance familiarity (`nemotron-ko-70s-lowfin`). The
card extraction prompt did not change, so the card rows replay the 2026-09-29 answers; only the
advice was recorded again (2 calls, $0.0131, `eval/results/260930-135827-cards-persona-record.json`,
commit `f6e79e2`, clean tree).

| Measure | 카드론 (131 sources) | LOCA CLASSIC (89 sources) |
|---|---|---|
| Cards kept / rejected by code | 45 / 0 | 28 / 0 |
| Card quote resolves in its source | 45/45 | 28/28 |
| Gold quotes covered (risk-only) | 11/12 (10/11) | 10/13 (9/12) |
| Advice passes its code checks and is shown | yes (336 chars) | yes (297 chars) |
| Items the advice points to | 설명02·04·21·23 | 설명02·10·16·23 |
| Injected advice defects rejected (invented number, verdict word, code in text, over length, unknown code) | 5/5 | 5/5 |

**Repeat stability of the advice** (`eval/agentic_stability.py`, three rounds on the round-1
cards; 4 calls, $0.0254, `eval/results/260930-135938-agentic-stability-record.json`). The advice
passed its checks in every round on both pages (6/6). The items it points to vary: pairwise
Jaccard of `advice_codes` between rounds is 0.33 / 0.33 / 1.00 on 카드론 and 0.75 / 0.60 / 0.75 on
LOCA CLASSIC. 설명02 (상환방법) is in every round on both pages; the rest of the list changes
from run to run. Card extraction itself is unchanged from §7 (Jaccard 0.37–0.53).

**Two readers, same page** (`eval/persona_pair_eval.py`, 4 calls, $0.0252,
`eval/results/260930-140114-persona-pair-record.json`). The same two dataset readers as §7 (70+,
초등학교, 익숙도 낮음; 40s bank/insurance worker, 익숙도 높음). Both advices pass on both pages. The item
overlap between the two readers is 0.60 on 카드론 (only the older reader gets 설명23, only the
familiar reader 설명17) and 0.29 on LOCA CLASSIC (older: 설명10·21; familiar: 설명09·17·23).
Whether a different list is a better list for that reader is not measured; no person has scored
the advice.

The live run of the current code on 디지로카 Las Vegas (2026-09-30, thread `review-260930-133058-9a1151`, 18 calls,
$0.1085, 305 s; `data/live6/review-result-2026-09-30-lasvegas-advice.json`, gitignored) collected
the page to `full_coverage` with 0 open gaps and judged 표시방법 적합 4/8 and 의무표시 적합 14/17
(A08, A09, B01 부적합); the advice for a 70s low-familiarity reader pointed to four items in one
call.

#### 이전 기준 — explanation units and fact ledger (2026-09-29)

Added with the bounded evidence agent, evidence cards and the persona explanation (branch
`agentic-evidence-persona`). Recording cost $0.0981 (13 calls). The unit and ledger rows describe
the line-by-line output ADR-007 removed.

| Measure | 카드론 (131 sources) | LOCA CLASSIC (89 sources) |
|---|---|---|
| Cards kept / rejected by code | 45 / 0 | 28 / 0 |
| Card quote resolves in its source | 45/45 | 28/28 |
| Gold quotes covered (risk-only) | 11/12 (10/11) | 10/13 (9/12) |
| Explanation units accepted / reverted | 35 / 0 | 17 / 0 |
| Analogies kept on rate/fee/warning cards | 0 (2 dropped by code) | 0 |
| Fact-ledger values preserved, decided by code | 40/40 | 25/25 |
| Generation-layer mutations caught (drop fact, invent number, verdict word, risk analogy) | 19/19 | 15/15 |
| Ledger-layer mutations caught (value changed or dropped in the assembled text) | 4/4 | 1/4 |

The generation layer (`review_unit`) is the gate that matters in a run: a unit that drops a
ledger value or invents a number never reaches the page. The ledger layer is a second net over
the assembled page text; it misses a change when the same value or wording still appears
elsewhere on the page (for example `최대` dropped from one line while other lines keep it).

**Live run of the page agent** (디지로카 Las Vegas, the page the 2026-09-28 audit found with 85
collapsed blocks). The first run ended `완료/full_coverage` because `observe()` read visibility
from html attributes only and counted the DaisyUI accordions as open; fixed in `ac6a11f`. The
rerun (thread `live-260929-lasvegas-2`, $0.1562, 19 calls, 391 s) ended `조사 불충분 /
no_viable_control`: 66 hidden text blocks, 29 unresolved `hidden_text` gaps, 7 agent steps, one
blocked expand (the accordion container's text contains `결제`, which the refusal list reads as a
payment action; the accordions open through a checkbox input the tools never click). The report
lists the 29 gaps as the reviewer's first action instead of passing the page.

### 7. Follow-up on the agentic design (2026-09-29, branch `agentic-followup`)

> 이전 기준: the persona-unit and fact-ledger figures in this section describe the line-by-line
> output removed by ADR-007; the current advice measurements are in §6. The display-flip and
> page-agent figures still apply.

Paid total for this follow-up: about $1.52; the measurements kept below cost $1.38 (re-recordings
$0.123, stability $0.160, reader pair $0.059, live reviews $1.04).

**Re-recorded suites.** display-flip, with E02/E04/E05 now decided by code: 4/4 injected defects
caught, 0/2 controls blamed, base verdicts 적합/적합 — the same as §3, at $0.0834 instead of
$0.2019 (`eval/results/260929-091909-display-flip-record.md`). The agentic cassette after the
unit-scoped ledger: ledger-layer mutations caught **8/8** on the two pages (was 4/4 and 1/4 in §6),
because a value dropped from one unit is no longer "preserved" by another line.

**Repeat stability** (`eval/agentic_stability.py`, three rounds, $0.1596). Evidence-card
extraction is not stable: Jaccard of (kind, quote) sets between rounds 0.37–0.53, 26–45 cards,
gold recall 0.75–0.92 (카드론) and 0.54–0.77 (LOCA). Accepted persona units vary (14–43 per round).
The code-decided fact ledger gives the same verdict for every fact in every round (40/40, 25/25)
and no risk-card analogy survives.

**Two readers, same facts** (`eval/persona_pair_eval.py`, $0.0589). Readers from the full
Nemotron-Personas-Korea dataset by attributes (70+, 초등학교; 40s bank/insurance worker): the
code-decided ledger is identical across readers (40/40, 25/25). The finance-familiar reader's
units were first reverted because numbered lists (`1)`) read as invented numbers; fixed, and on
replay LOCA goes from 5/9 to 9/9 accepted (카드론 1/3; the rest merge several lines into one
exact_fact).

**Page agent on more issuers** (`eval/agent_loop_eval.py`; data/live3, gitignored).

| Page | Collection | Notes | $ |
|---|---|---|---|
| 롯데 디지로카 Las Vegas (mobile) | 완료 / full_coverage, 68/68 gaps closed | DaisyUI accordions open through their checkbox; E07 now 부적합 on revealed blocks instead of 판정 불가 | 0.179 |
| 신한 Hi-Point (card) | first run: 20 turns without a rule | submit → "probe first" → probe loop; fixed (`8fd8b84`) | 0.109 |
| — rerun | 완료 / reachable_coverage | accepted; the run then hit its $0.15 cap during judgment and ended without a report | 0.156 |
| 신한 리볼빙 | 조사 불충분 / turn_budget, 21/70 | free-text reader chosen by the selection agent in 4 turns | 0.222 |
| KB 카드론 | first run: crash (page reloaded itself) | fixed; rerun: 20 turns without an accepted rule | 0.036 |
| 삼성 카드론 | 완료 / full_coverage | 장기카드대출 상품광고 | 0.088 |
| 현대 카드론 | 조사 불충분 / submitted_with_gaps | classification 판정 불가 (quote not in visible text) | 0.043 |
| 롯데 카드론 (PC) | 조사 불충분 / submitted_with_gaps, 0/26 | classified 신용카드 | 0.107 |
| KB·현대 신용카드 | out of scope | both were prepaid-card pages (a URL choice mistake) | 0.099 |

Two defects found this way are fixed: skip links counted as expandable controls, and the
closure metric counted header/menu/footer gaps (gaps now carry `in_region`). Still open: a run
that reaches its cost cap after collection raises instead of ending in a report; pages where the
agent submits with an untried in-region control.

**Human comprehension and harmful analogies** are not measured by code. `eval/review_sheet.py`
writes a blank sheet from live runs for a person to score; no score was filled by a model.

### 8. Audit remediation (2026-09-29, branch `agentic-followup`)

The [agentic behavior audit](../data/agentic-behavior-audit.md) confirmed three bounded agents
(two since 2026-09-30) inside a fixed workflow and found the evaluation too generous in three
places. Changes, all without a paid call:

- **Failures are results.** A run whose budget runs out after collection now ends in a `판정
  불가` report naming the interrupted node, instead of no report. `eval/agent_loop_eval.py` gives
  each requested thread one outcome (`complete`, `insufficient`, `collection_failed`,
  `interrupted`, `no_report`, `no_checkpoint`) and a success rate over all of them.
- **One generation per result.** `eval/agentic_eval.py` is now `eval/cards_persona_eval.py`.
  Every result file carries a `meta` block: implementation, commit, dirty flag, prompt hashes and
  the gold file's hash and version (`evaluation/run_meta.py`). Results written before this date
  have no `meta`.
- **Avoidable agent failures.** Root causes read from the stored traces: the KB 카드론 page became
  `chrome-error://` and the agent guessed selectors for 20 turns (now `수집 실패/page_unavailable`
  before the next model turn); 롯데 카드론 was accepted with untried controls inside its regions
  (now sent back once).

Re-aggregating the same seven live threads with the new outcome rule
(`eval/results/260929-115950-agent-loop.md`, $0): success 2/7 (0.286), report produced 6/7. The
earlier "완료 3/7" counted 신한 Hi-Point, which ended without a report.

**Re-measurement after the fixes** (live pages, paid $1.034; fresh data dirs `data/live4` and
`data/live5` so the page agent ran on every page; $0.15 per page).

| Measure | Before (live3) | After |
|---|---|---|
| Reports produced | 6/7 | 7/7 |
| Collection 완료 | 3/7 | 3/7 |
| In-region gap closure | 36.9% | 51.0% (123/241) |
| KB 카드론 (error page) | 20 turns, $0.036 | 0 turns, $0, `page_unavailable` |
| 롯데 카드론 gaps closed | 0/26 | 22/26 |
| Collection and judgment both finished | 2/7 | 1/7 |

The first live round exposed a defect in the new in-region nudge: it named controls the agent
had already expanded under another selector (신한 Hi-Point) or whose gap a popup kept open (현대
카드론), the agent repeated the expand, and exploration closed as `repeated_action`. Controls an
earlier expand reached are now skipped; the rerun of those two pages ended `완료/reachable_coverage`
and `조사 불충분/submitted_with_gaps` (the live3 outcomes).

Four pages ran out of the $0.15 cap during judgment and now end in a `판정 불가` report instead of
none; pages that finished judgment spent $0.18–0.22, so the cap, not the agents, set the last
row (live3's first round ran at $0.8). Per-page reports: `data/audit-remeasure-260929/`.
Results: `eval/results/260929-140148-agent-loop.md`, `260929-141601-agent-loop.md`.

## Model comparison

The same cassette-backed suites run with `--model`; each model has its own cassette.

The duty-flip rows were measured under the explanation-duty criteria (이전 기준); the other
models were not re-run on `disclosure-flip` after 2026-09-30.

| Suite | gpt-5-mini (default) | gpt-5-nano | gpt-5 |
|---|---|---|---|
| classification (6 pages) | **6/6** · 8 calls · $0.0354 · 104 s | 4/6 · 11 calls · $0.0244 · 350 s | 5/6 · 9 calls · $0.1903 · 184 s |
| duty-flip, pipeline arm (2026-09-28 code, 이전 기준) | **1/3**, quotes 67/67 (2026-09-29 code: 2/3, 64/64) | 0/3, quotes 47/47 | not run |
| duty-flip, ablation arm (2026-09-28 code, 이전 기준) | 1/3, quotes 45/156 (2026-09-29 code: 1/3, 27/156) | 0/3, quotes 59/127 | not run |
| duty-flip recordings, both rules | 15 calls · $0.2893 · 1,154 s | 16 calls · $0.1411 · 2,473 s, plus $0.0199 lost | — |
| plain-contract | 9/9, 0/4 false alarms | 9/9, 0/4 | 9/9, 0/4 |

Misclassifications: gpt-5 rejected the auto-installment page (할부금융·리스) as out of scope; gpt-5-nano
rejected the card-loan page (장기카드대출) as out of scope and returned 판정 불가 for the insurance
page. An in-scope page rejected as out of scope is the costliest error — it is never reviewed —
and both other models made it. gpt-5-nano also wrote about three times gpt-5-mini's output tokens on
the explanation-duty judgments, took 38 minutes and detected none of the deleted disclosures. Its
first attempt at the new control variant answered 11 of 39 items twice; the pipeline stopped as it
does in a real review, and the harness then lost the two paid answers ($0.0199) because it saved
the cassette only at the end. That is fixed (`85f1623`): the cassette is saved on the way out,
and an arm that cannot answer a variant is recorded as 판정 실패. Duty-flip targets are chosen per
model from that model's two arms (gpt-5-nano: F07, F11, F12), so the two arms of one model share
their deletions but different models do not.
gpt-5 was not run on duty-flip; at about five times the classification cost it would have cost
roughly $1. Files: `eval/results/*-gpt-5-nano.*`, `eval/results/*-gpt-5.*`; cassettes
`eval/cassettes/gpt-5-nano.json`, `eval/cassettes/gpt-5.json`.

## Failure analysis

Each finding is traced to a cause rather than left as a rate.

### 광고 의무표시 기준 (2026-09-30 재측정)

**A10 미탐은 F12와 같은 정답 쪽 문제입니다.** 건당 결제 금액별 할인율 표를 지웠지만, 본 구성은 삭제 뒤
페이지에 남은 다른 부분(건당 결제 금액·할인율·월 통합 할인한도를 담은 표)을 근거로 적합을 유지했고 그 근거는
변형 페이지에 실제로 있습니다(`missed_with_evidence_on_page: A10`). 같은 사실이 두 곳에 있으면 '삭제했으므로
부적합'이라는 정답이 성립하지 않습니다. → 삭제 대상을 페이지에 한 번만 나오는 사실로 제한하는 개선이 여전히
남아 있습니다.

**단발 실행의 부적합 3건 중 2건이 반복 측정에서 흔들리는 항목입니다.** 같은 페이지의 실제 실행(2026-09-30)은
A08(유효기간)·A09(통계 출처)·B01(신용평점 기준)을 부적합으로 냈습니다. 반복 측정에서 A08은 적합·적합·부적합,
B01은 부적합·부적합·적합으로 갈렸고, 무관 문장 하나를 지운 대조군에서도 A08이 적합 → 부적합으로 바뀌었습니다
(§2, §5). 두 항목은 원래부터 경계선상의 판정입니다. → 같은 질문을 세 번 묻고 일치할 때만 확정하는 방식의
적용 대상이 17항목 중 이 둘로 좁혀졌습니다.

**A09는 두 구성 모두 기준 실행에서 판정 불가였습니다.** 실제 실행에서는 할인율 표를 '인용한 통계'로 읽어
출처 누락으로 부적합을 냈습니다. 혜택 조건표는 통계 인용이 아니므로 오탐일 가능성이 높습니다. → 조건 판단
단계에서 '통계·도표 인용'의 범위를 좁히는 것이 다음 확인 사항입니다.

**두 구성이 기준 페이지에서 서로 다른 항목을 부적합으로 봤습니다.** 본 구성은 B01, 축소 구성은 A05를
부적합으로 판정했고, 축소 구성의 기준 실행 인용 17건 중 4건은 본문에 없는 문장이었습니다. 탐지율이 같아도
검토자가 확인할 수 있는 근거의 비율은 100% 대 77%입니다.

### 이전 기준 — 설명의무 준용 기준 (2026-09-27 – 09-29)

**설명의무 두 구성의 첫 비교는 같은 사례가 아니었습니다.** 각 구성이 자기 판정에서 삭제 대상을 골라
본 구성은 F07·F15·설명07, 축소 구성은 설명07·F06·설명06을 지웠고, 한 구성 안에서도 같은 문장을 지운 두 행을
두 건으로 셌습니다. 채점 루프가 이를 찾았고, 두 구성이 모두 적합으로 본 항목에서 겹치지 않는 문장만 고르게
고친 뒤 다시 녹음했습니다. 결과는 2/3 대 1/3에서 1/3 대 1/3으로 바뀌었습니다(§2).

**F12 미탐은 정답 쪽 문제입니다.** 본 구성은 삭제 뒤에도 적합을 유지했고, 변형 페이지에 실제로 있는
다른 문장("디지로카 Las Vegas 카드로 결제 시, 롯데카드가 제공하는 L.POINT 적립 서비스가 제공되지
않습니다.")을 근거로 댔습니다. 같은 사실이 여러 문장에 있으면 '삭제했으므로 부적합'이라는 정답이
성립하지 않습니다. 결과 파일의 `missed_with_evidence_on_page`가 이런 사례를 따로 표시합니다. 9/28 녹음에서는
F15·설명12가 같은 이유로 미탐이었습니다. → 삭제 대상을 페이지에 한 번만 나오는 주제로 제한하거나, 한 항목을
뒷받침하는 문장을 모두 지워야 합니다.

**F09·설명09 대조군 오탐은 경계선상의 적합이 뒤집힌 것입니다.** 무관한 긴 문장 하나를 지웠을 때 두 항목이
적합 → 부적합으로 바뀌었습니다. 두 항목은 3회 반복 측정에서도 한 번 부적합으로 흔들렸으므로, 원래부터 약한
적합이었습니다(9/28 녹음의 대조군 오탐은 F13·설명13이었고, 이번 반복 측정에서는 두 항목 모두 흔들렸습니다).
인용 검증은 **문장이 본문에 있는지**만 보고 **그 문장이 기준을 충족하는지**는 보지 않으므로 약한 적합이
통과했습니다. → 기준의 어느 요소를 충족했는지 요소 단위로 쓰게 하고, 빈 요소가 있으면 판정 불가로 내립니다.

**설명의무 판정의 23%가 같은 입력에서 흔들립니다.** 흔들린 9항목 중 7항목은 판정 불가를 거쳤습니다.
F13·설명13·F14·설명14는 1회차에 판정 불가였다가 다른 회차에 적합을 받았고, 이 가운데 설명13·설명14/F14는
인용 검증 실패로 판정 불가가 자주 나는 항목입니다. 한 번
호출하는 축소 구성은 21%(8/39)로 조금 덜 흔들렸지만, 그중 6항목은 적합과 부적합이 뒤바뀌었습니다(§5). →
`설명14`/`F14`처럼 인용 검증에서 반복해 실패하는 항목은 카세트의 실패한 답과 원문을 비교해, 모델의 바꿔쓰기인지
`core.text.locate_quote` 정규화 문제인지부터 가립니다($0). 그다음 같은 질문을 세 번 묻고 세 답이 일치할 때만
확정하며 불일치는 판정 불가로 넘기는 방식(호출 비용 약 3배, 설명의무 단계 기준)을 검토합니다.

**E01의 판정과 사유가 어긋났습니다.** 같은 디지로카 Las Vegas 페이지에서 9/27 실행은 E01을 부적합,
9/28 실행은 적합으로 판정했는데, 9/28의 사유는 "혜택 30~36pt, 불이익 9~13.5pt로 혜택이 더 강조"라고
불균형을 서술합니다. E01의 질문은 "균형을 잃었는가?"(예 = 위반)이고 프롬프트는 이 방향을 명시하지만,
모델이 서술과 반대 결론을 냈습니다. → 기준 질문에 대한 예/아니오를 따로 받고 판정은 코드가 방향에 맞춰
정하는 방식, 사유와 판정의 일치 검사가 다음 개선입니다.

**키워드 기준선이 3단계 판정과 같은 6/6이었습니다.** 평가셋의 여섯 페이지가 모두 제목에 상품유형을 적고
있어 난도가 낮습니다. → 여러 상품을 함께 언급하거나 상품명이 유형을 드러내지 않는 페이지를 추가해야
두 방식의 차이를 잴 수 있습니다.

**계획서의 비용 추정이 낮았습니다.** 계획서는 상품 1건 전체 처리를 약 $0.0061로 잡았습니다. 2026-09-28에
끝까지 돌린 검토 3건의 실측은 **$0.148~$0.193(중앙값 $0.184, 약 258원), 20~24회 호출, 513~723초**입니다
(`eval/results/260928-191135-cost-ledger.md`). 출력 토큰이 원인입니다 — 설명의무 항목마다 조건·판정·인용·
근거를 쓰고 원문·쉬운말을 각각 판정하므로 한 번 검토의 출력이 54,000~72,000 tokens입니다. 처음 보는
사이트에서는 페이지 구조 파악 호출(6~10회, $0.013~$0.039)이 더해집니다. 광고 의무표시 기준과 조언 한
문단으로 바꾼 뒤의 실제 실행(2026-09-30, 페이지 구조 파악 포함)은 **18회 호출, $0.1085, 305초, 출력 31,217
tokens**였습니다(`data/live6/review-result-2026-09-30-lasvegas-advice.json`).

## What this evaluation does not say

- 표본이 작습니다. 분류 6건, 결함 주입 3건과 대조군 1건, 표시방법 2개 페이지에 주입 4건과 대조군 2건,
  쉬운말 13건입니다. 여기의 비율은 경향이고 신뢰구간이 붙은 성능치가 아닙니다.
- 결함 주입은 3건입니다. 광고 의무표시 기준에서 두 구성 모두 2/3이고, 두 구성이 놓친 A10은 같은 사실이
  다른 곳에 남아 정답이 성립하지 않았습니다. 이전 기준에서는 재녹음만으로 1/3과 2/3을 오갔습니다.
- 실제 페이지에서 수집과 판정을 모두 끝낸 것은 7건 중 1건입니다(§8). 녹음 재생 스위트의 수치는 저장된
  페이지에 대한 값이며, 실제 페이지의 완주율을 뜻하지 않습니다.
- `plain-contract`는 9/28 구조의 쉬운말 검사를 잽니다. 현재 그래프는 이 검사를 부르지 않습니다(§4).
- 결함 주입은 삭제 방향만 측정했습니다(2026-09-30 이전 수치는 설명의무 준용 기준입니다). 없던 설명을 넣으면 적합으로 바뀌는지(반대 방향)는 보지 않았습니다.
- 표시방법 평가는 측정값을 바꾼 것이지 화면을 다시 그린 것이 아닙니다. 캡처 이미지는 내보내지 않아
  이미지 위 글자는 두 구성 모두에서 판정 불가로 남습니다.
- 분류 라벨은 페이지에 적힌 상품 구분을 영태가 옮겨 적은 것이고 프롬프트도 영태가 썼습니다. 두 번째
  사람의 교차 확인은 아직 없습니다.
- 쉬운말 케이스는 손으로 만든 문장쌍입니다. 실제 모델이 만드는 오류 분포와 다를 수 있습니다.
- 인용 유효율 100%는 "인용문이 본문에 있다"는 뜻이고 "그 인용이 기준을 충족한다"는 뜻이 아닙니다.
- 광고 의무표시 판정은 같은 입력에서 17항목 중 2항목(12%)이 흔들렸습니다(축소 구성도 2항목). 이전 기준인
  설명의무 준용에서는 23%였습니다. 한 번의 실행 결과를 확정 판정으로 읽으면 안 됩니다.
- 조언이 가리키는 설명의무 항목은 실행마다 달라집니다(회차 간 Jaccard 0.33~1.00). 조언은 매번 코드 검사를
  통과하지만, 어떤 목록이 그 독자에게 더 나은지는 재지 않았습니다.
- 증거 카드 정답셋은 AI 초안이고, 쉬운말 확인 권고의 사람 평가는 0건입니다.

## Adding a case

1. 분류: `tests/fixtures/classify/<case>.json`에 `{url, product, html, expected}`를 넣습니다.
2. 결함 주입: `eval/cases/disclosure_flip.json`의 `prefer_codes`(A·B·C 코드)를 조정하거나 `base_html`을 다른 수집 결과로
   바꿉니다.
3. 표시방법: `eval/cases/display_flip.json`의 `pages[].cases`에 `{id, kind, rubric, text}`를 더합니다.
   `rubric: null`이면 대조군입니다. 새 페이지는 실제 검토의 `product_page`를
   `eval/fixtures/display_*.json`로 내보내 씁니다.
4. 쉬운말: `eval/cases/plain_contract.json`에 `{id, defect, expect_marker, source_quote, rewrite}`를
   추가합니다. `defect: null`이면 무결함 대조군입니다.
5. 프롬프트나 모델을 바꿨다면 카세트가 무효가 됩니다. `--record`로 다시 녹음합니다.
