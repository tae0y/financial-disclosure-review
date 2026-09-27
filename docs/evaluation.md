---
ai-generated: true
human-review: false
created: 2026-09-27
---

# Evaluation

What was measured, on which data, with which labels, and what the numbers do not cover. Every
figure here comes from a file in `eval/results/`, and every one can be re-derived for free:

```bash
uv run python -m financial_disclosure_review evaluate --ablation   # replays the cassette, $0
```

The paid run that produced the recordings cost **$0.252 (about 353원)** in total — 19 model calls,
906 seconds. The free replay reproduces the identical table in 0.3 seconds. Why it is built that
way is in `localdocs/adr/adr-002-defect-injection-evaluation.md`.

## Three suites, three kinds of label

| Suite | Question | Label source | Cases | Cost |
|---|---|---|---|---|
| `classification` | is a real page put in the right product type? | 영태's labels on six captured pages | 6 | $0.035 |
| `duty-flip` | is a disclosure that left the page noticed? | the deletion itself — the sentence is provably gone | 3 + 1 control, × 2 arms | $0.217 |
| `plain-contract` | is a rewrite that drifts from the original caught? | the defect written into each pair | 13 | $0 (no model call) |

`duty-flip` runs two arms on the same inputs. `pipeline` is this project's check — condition
first, one quote per verdict, the quote validated against the page, one retry, unusable answers
downgraded to `판정 불가`. `ablation` is the same rubric items in one call with none of that. The
difference between the arms is this project's engineering, not the model's general ability.

## Results

### 1. Classification — 6/6

| Metric | Value |
|---|---|
| Accuracy | 6/6 (100%) |
| Reason given for every case | 6/6 |
| Calls / tokens | 8 calls, 48,702 in / 11,593 out |
| Cost / time | $0.0354 (약 50원), 104초 |

Two of the six are out-of-scope pages (삼성화재 자동차보험, 카카오뱅크 예금) and both were
rejected at step 2 with the second verification call agreeing. Source:
`eval/results/260927-174210-classification-record.json`.

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

The two numbers that matter together: the ablation arm calls 18 items 적합 against the pipeline's
10, admits uncertainty twice against 11 — and **more than half of its citations are not in the
page at all**. A reviewer cannot act on a finding whose quote does not exist, so its higher 적합
count is not a better result; it is the same over-acceptance the project set out to prevent, with
the evidence that would have exposed it removed. Source:
`eval/results/260927-175540-duty-flip-record.json`.

### 3. Plain-language contract — 9/9 caught, false alarms 50% → 0%

The first run of this suite found two defects in the contract layer itself. Both are fixed, with
regression tests in `tests/domain/plain_language/test_contract.py`.

| Metric | Before the fix | After |
|---|---|---|
| 주입 결함 적발 (재현율) | 9/9 (100%) | 9/9 (100%) |
| 무결함 대조군 오탐 | 2/4 (50%) | **0/4 (0%)** |
| 결함 유형별 적발 | 5개 유형 전부 | 5개 유형 전부 |

- `clean-annual-fee`: "연회비 20,000원" → "1년에 20,000원" 에서 `1`을 지어낸 수치로 셌습니다.
  기간·횟수 단위 앞의 `1`만 예외로 뒀습니다. 원문 수치를 바꾸면 '수치 누락' 쪽에서 잡히므로
  이 예외가 여는 구멍은 좁습니다.
- `clean-late-payment`: "결제일에"의 `제일`을 최상급 표현으로 셌습니다. 짧고 모호한 표현은 한글
  음절 뒤에 붙어 있으면 다른 낱말의 일부로 봅니다.

Baseline for this suite is definitional rather than measured: a build with no contract layer
publishes the model's wording as written, so it catches 0 of the 9.

Before/after files: `eval/results/260927-173641-plain-contract-replay.before-fix.json` and
`260927-173802-plain-contract-replay.json`.

## Failure analysis

Three findings, each traced to a cause rather than a rate.

**F15 (부가서비스 조건) 미탐은 방법의 한계입니다.** 삭제한 문장은 "실적조건 없이 혜택을
제공합니다."였고, 삭제 후에도 같은 사실이 다른 문장("국내 가맹점 2~3개월 무이자 할부 혜택은
지난달 실적 조건 없이 제공됩니다.")에 남아 있었습니다. 근거가 사라지지 않았으므로 적합 유지가
맞는 판정입니다. 플립 테스트가 "삭제한 문장이 유일한 근거"라고 가정한 것이 틀렸습니다.
→ 삭제 대상을 그 주제가 페이지에 한 번만 나오는 항목으로 제한해야 합니다.

**F13·설명13(이행책임) 대조군 오탐은 판정의 불안정성입니다.** 무관한 긴 문장 하나를 지웠을 때
이 두 항목이 적합 → 부적합으로 바뀌었습니다. 확인해 보면 기준 실행이 인용했던 문장("L.POINT
롯데멤버스㈜ 고객정보 제공에 동의하신 회원만…")은 삭제 후에도 본문에 그대로 있었습니다. 근거는
그대로인데 답이 달라진 것입니다. 원인으로 두 가지가 남습니다.
1. 기준 실행의 적합 판정 자체가 약했습니다. 저 문장은 "부가서비스를 누가 책임지고 제공하는지"를
   사실상 말하지 않습니다. 인용 검증은 **문장이 본문에 있는지**만 보고 **그 문장이 기준을
   충족하는지**는 보지 않으므로, 경계선상의 적합이 그대로 통과했습니다.
2. 39개 항목을 한 번의 호출로 판정하므로, 긴 문단이 빠져 프롬프트가 짧아지면 경계선상 항목의
   답이 흔들립니다.
→ 적합 판정에 기준의 어느 요소를 충족했는지 요소 단위로 쓰게 하고 빈 요소가 있으면 판정 불가로
내리는 것, 같은 입력을 3회 판정해 불일치율을 재는 것이 다음 개선 항목입니다.

**계획서의 비용 추정이 낮았습니다.** 계획서는 상품 1건 전체 처리를 약 $0.0061로 잡았습니다.
실제 페이지 1건을 처음부터 끝까지 돌린 측정값은 **$0.1456(약 204원), 12회 호출, 538초**입니다
(재시도 1회 포함, 실행 로그 `eval/results/260927-175600-review-demo-run.log`, 보고서
`data/reports/demo-260927.md`). 추정의 24배인데, 원인은 출력 토큰입니다:
설명의무 39항목마다 조건·판정·인용·근거를 쓰게 하고 원문·쉬운말 양쪽을 판정하므로 한 번
검토에 출력이 63k tokens 나왔습니다. 월 20건 기준 약 4,100원이라 과징금 위험과 비교하면
결론은 바뀌지 않지만, 계획서의 숫자는 측정값으로 대체해야 합니다. 보고서만 다시 만드는 것은
체크포인트에서 0회 호출·$0로 가능합니다(`rerun --from-node end_report`).

## What this evaluation does not say

- 표본이 작습니다. 분류 6건, 결함 주입 3건과 대조군 1건, 쉬운말 13건입니다. 여기의 비율은
  경향이고, 신뢰구간이 붙은 성능치가 아닙니다.
- 삭제 방향만 측정했습니다. 없던 설명을 넣으면 적합으로 바뀌는지(반대 방향)는 보지 않았습니다.
- 표시방법(`display_check`)은 평가에 없습니다. 근거가 렌더링된 크기·대비·좌표라서 문장 하나를
  지우면 그 뒤 전체 배치가 바뀌고, 정답이 깨끗하게 만들어지지 않습니다.
- 분류 라벨은 영태가 붙였고, 프롬프트도 영태가 썼습니다. 완전히 독립된 평가셋이 아닙니다.
- 쉬운말 케이스는 손으로 쓴 문장쌍입니다. 실제 모델이 만드는 오류 분포와 다를 수 있습니다.
- 인용 유효율 100%는 "인용문이 본문에 있다"는 뜻이고, "그 인용이 기준을 충족한다"는 뜻이
  아닙니다. F13 사례가 그 차이를 보여줍니다.

## Adding a case

1. 분류: `tests/fixtures/classify/<case>.json`에 `{url, product, html, expected}`를 넣습니다.
2. 결함 주입: `eval/cases/duty_flip.json`의 `prefer_codes`를 조정하거나 `base_html`을 다른
   수집 결과로 바꿉니다.
3. 쉬운말: `eval/cases/plain_contract.json`에 `{id, defect, expect_marker, source_quote,
   rewrite}`를 추가합니다. `defect: null`이면 무결함 대조군입니다.
4. 프롬프트나 모델을 바꿨다면 카세트가 무효가 됩니다. `--live --record`로 다시 녹음합니다.
