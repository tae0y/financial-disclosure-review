---
ai-generated: true
human-review: false
---

# classify_type 테스트 시나리오

`classify_type` 노드와 `route_after_classify` 엣지의 확인 항목을 정리한 문서입니다. 현재 검증 코드는 `notebooks/review.ipynb`의 "classify_type 확인" 셀에 있고, 이 문서는 그 셀이 다루는 범위와 아직 자동화하지 않은 항목을 함께 기록합니다.

## 대상과 기준

- 대상: `classify_page(page, model, ask)`, `classify_type(state, runtime)`, `route_after_classify(state)`
- 판정 기준: `docs/design.md`의 "Rubrics" 절
- 결과 형태: `classification = {product_type, page_type, reason}`
- 시스템 오류(API 호출 실패, 응답 스키마 파싱 실패)만 예외로 처리하고, 판정 결과는 항상 정상 반환합니다.

## 입력 데이터

`notebooks/fixtures/classify/<case>.json`은 `{url, product, html, expected}` 구조입니다. 출처는 `financial-product-disclosure-and-plain-language`의 스냅샷(case별 최신 타임스탬프)입니다.

| case | product_type | page_type |
|---|---|---|
| lottecard-loca-professional | 신용카드 | 상품광고 |
| lottecard-card-loan | 장기카드대출 | 상품광고 |
| lottecard-auto-installment | 할부금융·리스 | 상품광고 |
| lottecard-revolving | 리볼빙 | 업무광고 |
| samsungfire-direct-auto-insurance | 범위 밖(2단계) | None |
| kakaobank-fixed-deposit | 범위 밖(2단계) | None |

이 fixture의 html은 이전 프로젝트의 `content_llm.html`입니다. 현재 전처리 노드가 만드는 `product_page.html`과 형태가 다를 수 있으므로, 전처리 출력으로 다시 만든 fixture와 비교하는 시나리오(S-14)를 남겨 둡니다.

## 시나리오

### A. 가짜 ask (무료, 셀에서 자동 확인)

기대 답을 돌려주는 가짜 `ask`로 실행합니다.

| ID | 시나리오 | 기대 결과 |
|---|---|---|
| S-01 | fixture 6개에 기대 답을 돌려주는 가짜 ask | 표의 product_type과 page_type이 그대로 나옴. reason이 비어 있지 않음 |
| S-02 | S-01 중 범위 밖 fixture | reason이 "2단계"로 시작. 호출 순서는 분류, 검증 |
| S-03 | 페이지에 없는 quote | 분류를 한 번 더 호출한 뒤 `판정 불가`, reason이 "판정 근거 부족"으로 시작, page_type은 None |
| S-04 | 빠진 reason | S-03과 같음 (재시도 후 판정 불가) |
| S-05 | 첫 답은 quote 불일치, 재시도 답은 정상 | 재시도 답으로 정상 결과 (리볼빙, 업무광고) |
| S-06 | 2단계 아니오에 검증 호출이 "예" | `판정 불가`, reason이 "판정 불일치"로 시작하고 분류 이유와 검증 이유를 모두 포함 |
| S-07 | 공백만 다른 quote | 통과. 정상 결과 |
| S-08 | 1단계 실패를 흉내 낸 답 | `범위 밖`, reason이 "1단계"로 시작, page_type은 None |
| S-09 | `route_after_classify`에 "범위 밖", "판정 불가" | END |
| S-10 | `route_after_classify`에 다섯 가지 정상 product_type | "judge_display_method" |
| S-11 | `classify_type`에 정상 페이지 (가짜 ask 주입) | `{"classification": {...}}` 반환, 예외 없음 |
| S-12 | `classify_type`에 빈 `product_page` | 모델 호출 없이 `판정 불가` (reason "입력 없음"), 예외 없음 |

### B. 실제 모델 (유료, 사용자 승인 후 실행)

| ID | 시나리오 | 확인할 것 | 상태 |
|---|---|---|---|
| S-13 | 롯데카드 Las Vegas, 신한카드 Hi-Point Plan 샘플 URL을 전처리부터 그래프로 실행 | 신용카드 / 상품광고, 각 단계 quote가 페이지에 존재 | 2026-09-27 실행, 두 건 모두 기대와 일치 (gpt-5-mini) |
| S-14 | fixture 6개를 실제 모델로 실행 (`run_paid = True`) | 기대값 대 실제값, 각 단계 quote 존재 여부 | 미실행 |
| S-15 | 전처리 노드 출력으로 fixture를 다시 만들어 S-14와 비교 | 스냅샷 기반 결과와 판정이 같은지 | 미실행 |

### C. 자동화하지 않은 위험 항목

| ID | 항목 | 이유 |
|---|---|---|
| R-01 | 리볼빙 페이지 끝의 단기카드대출 권유 문구 | 공통 규칙 2번(다른 상품 이름은 주제로 보지 않음)이 실제로 지켜지는지는 S-14에서만 확인됨 |
| R-02 | 이벤트·묶음·목록 페이지 | 1단계 아니오 경로의 실제 모델 검증 fixture가 없음 |
| R-03 | 검증 호출이 예로 답하는 실제 사례 | 판정 불일치 빈도를 알려면 여러 페이지 실행이 필요함 |
| R-04 | 호출 횟수 상한 | 최악의 경우 fixture당 3회(분류 2 + 검증 1). 실행 전체의 횟수와 토큰 상한은 코드에 없음 |

## 실행 방법

- 가짜 ask 확인(S-01~S-12): 노트북을 처음부터 끝까지 실행하면 "가짜 ask 확인 통과" 메시지가 출력됩니다.
- 유료 실행: 해당 셀의 `run_paid` 또는 `run_live`를 임시로 `True`로 바꿔 실행하고, 커밋 전에 `False`로 되돌립니다. 실행 전에 영태에게 먼저 묻습니다.
- 모든 시나리오는 `classify_page`와 `classify_type`이 예외를 던지지 않는다는 조건을 공통으로 만족해야 합니다.

## 후속 작업 후보

- 가짜 ask 확인을 `tests/`의 pytest 파일로 옮기기 (노트북 셀 의존을 없애려면 `classify_page`를 모듈로 분리해야 함)
- S-14, S-15 실행
- 이벤트·목록 페이지 fixture 추가 (R-02)
