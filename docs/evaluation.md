---
ai-generated: true
human-review: false
created: 2026-09-27
updated: 2026-09-28
---

# Evaluation

What was measured, on which data, with which labels, and what the numbers do not cover. Every
figure here comes from a file in `eval/results/`, and every one can be re-derived for free:

```bash
uv run python -m financial_disclosure_review evaluate --ablation   # replays the cassette, $0
```

On 2026-09-28 that command replayed all five suites from 62 recorded answers — 75 hits, 0 misses,
$0, about 5 seconds (`eval/results/260928-191314-all-replay.md`). A suite whose prompt or model
changes needs its answers recorded again; `--record` calls the model only for the questions the
cassette does not hold. What the recordings cost:

| Recording | Calls | Cost | Time | File |
|---|---|---|---|---|
| classification (2026-09-27) | 8 | $0.0354 | 104 s | `eval/results/260927-174210-classification-record.md` |
| duty-flip, both arms (2026-09-27) | 11 | $0.2166 | 802 s | `eval/results/260927-175540-duty-flip-record.md` |
| plain-contract condition judgment (2026-09-28) | 1 | $0.0021 | 13 s | `eval/results/260928-183438-plain-contract-record.md` |
| stability, rounds 2–3 (2026-09-28) | 23 | $0.1657 | 646 s | `eval/results/260928-184936-stability-record.md` |
| display-flip pipeline arm (2026-09-28) | 19 | $0.2019 | 712 s | `eval/results/260928-190811-display-flip-record.md` |
| **Total for gpt-5-mini** | **62** | **$0.6217** | | |

The model comparison (other models on the same suites) is recorded in its own cassettes; see
§Model comparison.

## Five suites, five kinds of label

| Suite | Question | Label source | Cases | Comparison arm |
|---|---|---|---|---|
| `classification` | Is a real page put in the right product type? | the product type each issuer names on its page, written into the fixture by 영태 | 6 | `keyword`: count product words, no model |
| `duty-flip` | Is a disclosure that left the page noticed? | the deletion itself — the sentence is provably gone | 3 + 1 control | `ablation`: one call, no quote check, no condition step, no retry |
| `display-flip` | Is a disclosure made too small or too faint noticed, and only that one? | the mutation itself — the measured size or contrast is provably under the threshold | 4 + 2 controls | `rules`: thresholds with no notion of which text is mandatory |
| `plain-contract` | Is a rewrite that drifts from the original caught? | the defect written into each pair | 13 (9 defective, 4 clean) | none measured — a build without the check publishes all 9 |
| `stability` | Does the same input get the same answer? | agreement with itself, no label | 6 pages + 39 items, 3 rounds | — |

Why the explanation duty is measured by deletion and the display method by mutation is recorded
in `docs/adr/adr-002-defect-injection-evaluation.md` and `docs/adr/adr-005-display-flip-evaluation.md`.

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
(`docs/adr/adr-003-staged-classification.md`).

The out-of-scope path is demonstrable without a network:
`uv run python eval/out_of_scope_report.py` replays the recorded calls and renders the report
through the same `build_report` the graph's `end_report` node uses.

### 2. Explanation duty, defect injection — pipeline 2/3, ablation 1/3

Base page: 롯데카드 디지로카 Las Vegas 상품안내 화면 (공개 페이지, 본문 5,667자, 적용 항목 39개).

| Metric | `pipeline` | `ablation` |
|---|---|---|
| 삭제한 설명을 부적합으로 잡아냄 | **2/3 (66.7%)** | 1/3 (33.3%) |
| 인용 유효율 (인용문이 실제로 본문에 있음) | **66/66 (100%)** | 66/156 (42.3%) |
| 기준 실행의 인용 유효율 | **10/10 (100%)** | 14/39 (35.9%) |
| 대조군(무관 문장 삭제) 오탐 | 2건 (F13, 설명13) | 0건 |
| 판정 불가로 보류한 항목 | 11 | 2 |
| 기준 판정 분포 (적합/부적합/판정 불가) | 10 / 18 / 11 | 18 / 19 / 2 |

The ablation arm calls 18 items 적합 against the pipeline's 10 and admits uncertainty twice against
11 — and **more than half of its citations are not in the page**. A reviewer cannot act on a finding
whose quote does not exist, so its higher 적합 count is the over-acceptance the project set out to
prevent, with the evidence that would have exposed it removed. Source:
`eval/results/260927-175540-duty-flip-record.json`.

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
(`docs/display_check.md`), the base run now reads E02 판정 불가 on that page — unmeasurable, neither
a pass nor a failure.

### 4. Plain-language contract — 9/9 caught, 0/4 false alarms

| Metric | 2026-09-27, before the fix | 2026-09-27, after | 2026-09-28, condition judged by the model |
|---|---|---|---|
| 주입 결함 적발 (재현율) | 9/9 | 9/9 | **9/9** |
| 무결함 대조군 오탐 | 2/4 (50%) | 0/4 | **0/4** |

The first run found two defects in the contract layer itself, both fixed with regression tests in
`tests/domain/plain_language/test_contract.py`:

- `clean-annual-fee`: "연회비 20,000원" → "1년에 20,000원" counted the `1` as an invented number.
  Only a `1` before a period or count unit is exempt now.
- `clean-late-payment`: the `제일` inside "결제일에" counted as a superlative. A short, ambiguous
  phrase glued to a preceding Hangul syllable is read as part of another word.

On 2026-09-28 the condition-and-exception check moved from a keyword scan to a model judgment
(`judge_condition_preservation`, `docs/plain_language.md`) because correct synonym swaps looked like
omissions. The suite was re-recorded the same day (one call, $0.0021) with the same result.
Before/after files: `260927-173641-plain-contract-replay.before-fix.json`,
`260927-173802-plain-contract-replay.json`, `260928-183438-plain-contract-record.json`.

### 5. Stability — classification steady, explanation duty 28/39

Round 1 is the recording the other suites use; rounds 2–3 were recorded on 2026-09-28.

| Question | Same answer in all three rounds |
|---|---|
| Classification of the six pages | **6/6** |
| Explanation-duty verdicts on the base page (39 items) | **28/39 (71.8%)** |

The eleven items that moved: F05, F09, F11, F12, F14, 설명05, 설명09, 설명11, 설명14, 설명21, 설명22
(an F code and the 설명 code with the same number share their criterion text). Ten of them were 적합
in one round and not in another: eight moved between 판정 불가 and 적합, two (F09, 설명09) between
부적합 and 적합; 설명21 moved between 판정 불가 and 부적합. A reviewer's to-do list from a single run is therefore not
reproducible for about a quarter of the explanation-duty items. Source:
`eval/results/260928-184936-stability-record.md`.

## Model comparison

The same cassette-backed suites run with `--model`; each model has its own cassette.

MODEL_COMPARISON_TABLE

## Failure analysis

Each finding is traced to a cause rather than left as a rate.

**F15 (부가서비스 조건) 미탐은 방법의 한계입니다.** 삭제한 문장은 "실적조건 없이 혜택을 제공합니다."였고,
같은 사실이 다른 문장("국내 가맹점 2~3개월 무이자 할부 혜택은 지난달 실적 조건 없이 제공됩니다.")에
남아 있었습니다. 근거가 사라지지 않았으므로 적합 유지가 맞는 판정입니다. → 삭제 대상을 페이지에 한 번만
나오는 주제로 제한해야 합니다.

**F13·설명13 대조군 오탐은 페이지 변화에 대한 반응입니다.** 무관한 긴 문장 하나를 지웠을 때 두 항목이
적합 → 부적합으로 바뀌었고, 인용했던 문장은 그대로 남아 있었습니다. 3회 반복 측정에서 두 항목은 흔들리지
않았으므로 실행마다 생기는 잡음이 아니라, 문단이 빠져 프롬프트가 짧아지자 경계선상의 적합이 뒤집힌
것입니다. 인용 검증은 **문장이 본문에 있는지**만 보고 **그 문장이 기준을 충족하는지**는 보지 않으므로 약한
적합이 통과했습니다. → 기준의 어느 요소를 충족했는지 요소 단위로 쓰게 하고, 빈 요소가 있으면 판정 불가로
내립니다.

**설명의무 판정의 28%가 같은 입력에서 흔들립니다.** 흔들린 11항목 중 8항목은 1회차(9/27)에 판정 불가였다가
2·3회차(9/28)에 적합으로 답한 경우입니다. → 같은 질문을 세 번 묻고 세 답이 일치할 때만 확정하며 불일치는 판정 불가로
넘기는 방식(호출 비용 약 3배, 설명의무 단계 기준)이 다음 개선입니다.

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
사이트에서는 페이지 구조 파악 호출(6~10회, $0.013~$0.039)이 더해집니다.

## What this evaluation does not say

- 표본이 작습니다. 분류 6건, 결함 주입 3건과 대조군 1건, 표시방법 2개 페이지에 주입 4건과 대조군 2건,
  쉬운말 13건입니다. 여기의 비율은 경향이고 신뢰구간이 붙은 성능치가 아닙니다.
- 설명의무는 삭제 방향만 측정했습니다. 없던 설명을 넣으면 적합으로 바뀌는지(반대 방향)는 보지 않았습니다.
- 표시방법 평가는 측정값을 바꾼 것이지 화면을 다시 그린 것이 아닙니다. 캡처 이미지는 내보내지 않아
  이미지 위 글자는 두 구성 모두에서 판정 불가로 남습니다.
- 분류 라벨은 페이지에 적힌 상품 구분을 영태가 옮겨 적은 것이고 프롬프트도 영태가 썼습니다. 두 번째
  사람의 교차 확인은 아직 없습니다.
- 쉬운말 케이스는 손으로 만든 문장쌍입니다. 실제 모델이 만드는 오류 분포와 다를 수 있습니다.
- 인용 유효율 100%는 "인용문이 본문에 있다"는 뜻이고 "그 인용이 기준을 충족한다"는 뜻이 아닙니다.
- 설명의무 판정은 같은 입력에서도 28%가 흔들립니다. 한 번의 실행 결과를 확정 판정으로 읽으면 안 됩니다.

## Adding a case

1. 분류: `tests/fixtures/classify/<case>.json`에 `{url, product, html, expected}`를 넣습니다.
2. 결함 주입: `eval/cases/duty_flip.json`의 `prefer_codes`를 조정하거나 `base_html`을 다른 수집 결과로
   바꿉니다.
3. 표시방법: `eval/cases/display_flip.json`의 `pages[].cases`에 `{id, kind, rubric, text}`를 더합니다.
   `rubric: null`이면 대조군입니다. 새 페이지는 실제 검토의 `product_page`를
   `eval/fixtures/display_*.json`로 내보내 씁니다.
4. 쉬운말: `eval/cases/plain_contract.json`에 `{id, defect, expect_marker, source_quote, rewrite}`를
   추가합니다. `defect: null`이면 무결함 대조군입니다.
5. 프롬프트나 모델을 바꿨다면 카세트가 무효가 됩니다. `--record`로 다시 녹음합니다.
