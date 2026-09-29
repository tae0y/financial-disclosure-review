---
ai-generated: true
human-review: false
---

# 금융상품 판매화면 검토 결과

- 판정: **판정 불가**
- 조치 방침: judge_explanation_duty 단계에서 실행이 중단되어(비용 한도 도달) 자동 판정을 내리지 않았습니다.
- 대상 화면: https://m.lottecard.co.kr/front/card/basic/credit/info/las-vegas?brand=city&pcYn=Y
- 상품명: 디지로카 Las Vegas
- 상품유형/화면유형: 신용카드 / 상품광고
- 분류 근거: 페이지에 '신용카드 발급'과 연회비·혜택·연체이자율 등 신용카드 발급 및 이용과 직접 관련된 안내가 포함되어 있어 본문 주제가 신용카드임을 명확히 보여줍니다.
- 페이지 수집: 완료 (full_coverage)
- 에이전트 실행: 페이지 탐색 agent 11턴(full_coverage) · 사례 연결 agent 8턴(max_turns) · 독자 선택 상품유형 기본 조건

## 1. 담당자 조치 목록

1. 검토 중단(비용 한도 도달): run budget $0.15 reached ($0.150892) before PlainJudgments
2. 한도를 조정해 재실행하거나 사람이 페이지 전체를 직접 검토

## 2. 검토 요약

| 검토 영역 | 검토 항목 | 위반·반려 | 판정 불가·차이 |
|---|---|---|---|
| 표시방법 | 8 | 3 | 1 |
| 설명의무(원문) | 0/0 | 0 | 0 |
| 설명의무(독자 맞춤 설명) | 0/0 | 0 | 0 |
| 독자 맞춤 설명 | 9 | 0 | 0 |

부적합 3건 중 위반 3건, 권고 미충족 0건입니다. 광고 규정과 협회 표시 규정은 공개 상품 페이지(광고)에 직접 적용되어 위반으로 읽고, 설명의무 항목은 계약 권유 단계의 의무를 광고 화면에 준용한 것이어서 권고 미충족으로 읽습니다.

## 3. 확인이 필요한 항목

| 항목 | 대상 | 판정 | 구분 | 사유 | 인용 |
|---|---|---|---|---|---|
| E01 | 판매 화면 표시방법 | 부적합 | 위반(법령) | 혜택 문구들(b12, b16, b18, b21, b23)은 30~36pt 등 큰 글씨로 눈에 띄게 표시된 반면 조건·제한 문구(b41, b45, b49)는 12pt 수준의 회색 문자로 작고 흐리게 표시되어 글자 색·크기의 균형을 잃었습니다. | 100,000원 / 최대 2% / 최대 10만원 / 2~3개월 / 무이자 / 실적조건 없이 혜택을 제공합니다. / 디지로카 Las Vegas … |
| E05 | 판매 화면 표시방법 | 판정 불가 | - | a pass would be unproven: image-backed text without a readable crop: ['b19']; contrast unmeasured: ['b19'] |  |
| E06 | 판매 화면 표시방법 | 부적합 | 위반(협회 자율규제) | 측정 결과 의무표시사항 중 b26과 b70이 다른 문장과 분리되지 않고 이어붙여져 있어 문장마다 기호나 줄바꿈으로 구분되지 않았습니다. | 디지로카 Las Vegas 국내외 가맹점 결제일 할인 디지로카 Las Vegas 할인 공통기준 / 즉시 할인이 되지 않을 수 있습니다. |
| E07 | 판매 화면 표시방법 | 부적합 | 위반(협회 자율규제) | 의무표시사항 관련 블록들이 접힌 영역으로 표기되어 있으며(b27 등) 검사 로그에 사용자 조작으로 나타난 항목(b45 등)이 있어 주요 정보를 숨겼습니다. | 디지로카 Las Vegas 국내외 가맹점 결제일 할인 / 디지로카 Las Vegas 카드가 아닌 롯데카드 이용금액, 모든 무이자할부 이용금액,… |

## 4. 표시방법 검토 상세

| 항목 | 판정 | 근거 블록 | 사유 |
|---|---|---|---|
| E01 | 부적합 | b12, b16, b18, b21, b23, b41, b45, b49 | 혜택 문구들(b12, b16, b18, b21, b23)은 30~36pt 등 큰 글씨로 눈에 띄게 표시된 반면 조건·제한 문구(b41, b45, b49)는 12pt 수준의 회색 문자로 작고 흐리게 표시되어 글자 색·크기의 균형을 잃었습니다. |
| E02 | 적합 | b133 | all 29 labelled block(s) measured within the threshold (min 9.0pt) |
| E03 | 적합 | b125, b127, b128, b129, b130, b131, b64 | 연체이자율·경고문구(b125, b127–b131)가 w500으로 주변 안내문(b64 등, w400)보다 굵게 표시되어 구별됩니다. |
| E04 | 적합 | b118 | all 7 labelled block(s) measured within the threshold (min contrast 5.05) |
| E05 | 판정 불가 |  | a pass would be unproven: image-backed text without a readable crop: ['b19']; contrast unmeasured: ['b19'] |
| E06 | 부적합 | b26, b70 | 측정 결과 의무표시사항 중 b26과 b70이 다른 문장과 분리되지 않고 이어붙여져 있어 문장마다 기호나 줄바꿈으로 구분되지 않았습니다. |
| E07 | 부적합 | b27, b45 | 의무표시사항 관련 블록들이 접힌 영역으로 표기되어 있으며(b27 등) 검사 로그에 사용자 조작으로 나타난 항목(b45 등)이 있어 주요 정보를 숨겼습니다. |
| E08 | 적합 | b19, b16 | 할인율이 b19에서 '0.5%~2%'로 범위를, b16에서 '최대 2%'로 최고치를 명시하고 있어 짝이 되는 주요 정보가 함께 제공됩니다. |

## 5. 설명의무 검토 상세 (원문 대비 독자 맞춤 설명)

(해당 항목 없음)

- F01–F19·F21·F22는 같은 의무를 담은 설명 코드(설명01–19·27·28)와 한 주제입니다. 표에는 둘 다 남기고, 조치 목록에서는 같은 판정이면 한 번만 셉니다.

## 6. 독자 맞춤 설명 결과

- 상태: 완료
- 독자 프로필: nemotron:0851bae336c84f3698ea0f6fcb0d03e4 vt1@ada0f5b (nvidia/Nemotron-Personas-Korea rev=ada0f5b uuid=0851bae336c84f3698ea0f6fcb0d03e4 (CC-BY-4.0), ai-drafted, 적용)
- 독자 선택: 상품유형 기본 조건, 조건 {'age_min': 20}, 일치 989509행
- 금융 익숙도: 낮음 (행 속성 추정)
- 독자 개요(합성 페르소나): 93세 남자 · 학력 초등학교 · 직업 무직 · 전북 거주 · 가구 배우자와 거주 이창식 씨는 전주에서 아내와 거주하며 신문 읽기와 소소한 집수리를 즐기는, 엄격한 자기관리와 성실함을 삶의 훈장으로 여기는 93세 어르신입니다.
- 원문 사실(exact_fact)은 설명 옆에 그대로 남습니다. 위험 개념에는 비유를 쓰지 않습니다.

| 단위 | 출처 | 원 사실 | 설명 | 비유 | 상태 |
|---|---|---|---|---|---|
| u1 | dom-16, dom-14 | * 건당 결제금액별로 0.5%~2% 할인율 적용 | 결제할 때 건마다 적용되는 할인률이 다릅니다. '0.5%~2%'가 적용된다고 적혀 있습니다. 한 건에서 받을 수 있는 할인은 '결제금액 최대 2%'까지입니다. | 한 장씩 붙이는 할인 스티커처럼, 결제 건마다 다른 비율로 붙습니다. | accepted |
| u2 | dom-10, dom-15 | 100,000원 | 페이지에 예시로 '100,000원'이 적혀 있습니다. 혜택의 안내에는 '최대 10만원 할인'이라고 표기되어 있습니다. | 예시 금액은 광고의 예시값과 같습니다. 실제로 받을 금액은 본문에 적힌… | accepted |
| u3 | dom-54 | 본인카드와 가족카드의 월 할인한도는 합산되며, 남은 월 할인한도는 이월되지 않습니다. | 본인카드와 가족카드의 한도가 더해집니다. 만약 그 달에 한도를 다 쓰지 못하면, 남은 한도는 다음 달로 넘어가지 않습니다. | - | accepted |
| u4 | dom-40, dom-49 | 디지로카 Las Vegas 카드가 아닌 롯데카드 이용금액, 모든 무이자할부 이용금액, 거래 취소금액, 국세, 지방세, 건강보… | 위 목록에 든 항목들은 혜택 적용에서 제외됩니다. 공과금, 세금, 보험, 연금, 일부 교통비, 상품권·선불카드 충전 등 많은 항목이 포함되어 있습니다. 자세한 … | - | accepted |
| u5 | dom-44, dom-45, dom-47, dom-49 | 디지로카 Las Vegas 카드로 국내 가맹점에서 5만원 이상 2~3개월 할부 결제 시 무이자 할부 혜택이 제공됩니다. | 국내 가맹점에서 '5만원' 이상을 2~3개월로 나누어 결제하면 무이자 혜택이 제공됩니다. '국내 가맹점 2~3개월 무이자 할부 혜택은 지난달 실적 조건 없이 제… | - | accepted |
| u6 | dom-67 | 디지로카 Las Vegas 카드로 결제 시, 롯데카드가 제공하는 L.POINT 적립 서비스가 제공되지 않습니다. | 이 카드로 결제하면 L.POINT 적립은 되지 않습니다. L.POINT를 기대하고 사용하면 적립이 되지 않으니 주의하세요. | - | accepted |
| u7 | dom-57, dom-58 | 해외 이용 시 별도의 수수료가 부과되오니, 상품설명서 뒷면을 확인해주세요. | 해외 사용에는 별도 수수료가 붙습니다. 해외 이용금액의 혜택 적용 기준은 '롯데카드에 접수되는 현지 매출일자'입니다. 실제 적용 여부와 날짜는 카드사 접수 후 … | - | accepted |
| u8 | dom-114 | 연체이자율: 회원별·이용상품별 약정이율+최대 3%, 법정 최고금리(연 20%) 이내 | 만약 납부를 늦추면 더 높은 이자가 붙을 수 있습니다. 안내에는 '약정이율+최대 3%, 법정 최고금리(연 20%) 이내'라고 적혀 있습니다. 연체 관련 내용은 … | - | accepted |
| u9 | dom-121 | ※ 카드출시일 : 2024년 05월 31일 | 이 카드는 '2024년 05월 31일'에 출시되었다고 표기되어 있습니다. 출시일 정보입니다. | - | accepted |

### 운영 통제 (판정 대상 아님)

- 화면: AI 생성 고지, 원문 보기 전환, 오류 신고
- 거버넌스: 사람 승인, 변경 관리, 프로필 검토

## 7. 자동 검증 결과

- 통과: None
- 실패 모듈: 없음
- 검증 루프: None회 (최대 2회)
- 중단 사유: 비용 한도 도달 — run budget $0.15 reached ($0.150892) before PlainJudgments
- 재시도 이력: 없음


## 8. 비용과 소요시간

아래 수치는 **이 문서를 만든 실행**에서 발생한 것입니다.

- 모델 호출 26회, 입력 293,274 tokens, 출력 38,787 tokens
- 비용 $0.150892 (약 211.2원, 1400.0원/$ 가정)
- 소요시간 410.8초
- 상한: {'max_calls': 60, 'max_usd': 0.15}
- 단계별: discover 11회 $0.0496, case_link 8회 $0.0257, ExplanationJudgments 1회 $0.0212, EvidenceCardDrafts 1회 $0.0152, PersonaUnitDrafts 1회 $0.0118, DisplayLabels 1회 $0.0117, DisplayVerdicts 1회 $0.0094, ClassifyAnswer 1회 $0.0058, vision 1회 $0.0003

## 9. 한계와 가정

- 이 검토는 공개된 광고성 화면을 대상으로 하며, 청약 단계 설명화면은 범위에 없습니다. 설명의무 기준은 준용해 품질 기준으로 적용했습니다.
- 자동 검증은 인용 근거의 존재와 모듈 간 모순만 확인합니다. 통과가 법률 준수를 보증하지 않습니다.
- 3 images in the selected html, 3 without alt text; text inside images is not measurable. Flagged by the model: none
- CSS background images and overlapping img bounds flag risky blocks; captured crops are checked by vision for E04/E05. Pseudo-elements and image-only text remain unmeasured.
- 가정: E02 says 8pt on A4. A web page has no paper size, so the node uses computed CSS px x 0.75 >= 8pt at the captured viewport.
- 가정: No threshold in the rubric. The node uses the WCAG 2.1 SC 1.4.3 AA ratio: 4.5:1 for normal text, 3.0:1 for large text (>= 24px, or >= 18.66px and weight >= 700). Text and background colors come from the snapshot (blended background when captured); Image-backed blocks are checked from saved rendered…
- 독자 맞춤 설명은 독자 프로필 nemotron:0851bae336c84f3698ea0f6fcb0d03e4 vt1@ada0f5b(ai-drafted, 적용) 기준의 보조 설명이며, 원문을 대신하거나 독자의 자격·혜택·상환액을 판단하지 않습니다.
- 조사 공백 1건(claim_without_visible_condition)은 누락의 증거가 아니라 확인하지 못한 범위입니다.

## 10. 페이지 수집 agent 기록

- 상태: 완료, 중단 사유: full_coverage
- 조사 범위(전 → 후): {'hidden_text_blocks': 66, 'visible_text_blocks': 28, 'candidate_controls': 7, 'open_gaps': 68} → {'hidden_text_blocks': 0, 'visible_text_blocks': 94, 'candidate_controls': 7, 'open_gaps': 0}
- `조사 불충분`은 누락의 증거가 아닙니다. 보이지 않은 조건은 위반이 아니라 조사 공백으로 남깁니다.

| 공백 | 종류 | 상태 | 내용 | 닫은 행동 |
|---|---|---|---|---|
| gap-1 | unexpanded_control | closed | div.collapse.collapse-arrow > input:nth-of-type(1) not yet expanded | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-2 | unexpanded_control | closed | input.min-h-12 not yet expanded | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-3 | hidden_text | closed | hidden text: '디지로카 Las Vegas 국내외 가맹점 결제일 할인' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-4 | hidden_text | closed | hidden text: '건당 결제 금액, 할인율, 월 통합 할인한도로 구성된 표' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-5 | hidden_text | closed | hidden text: '건당 결제 금액' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-6 | hidden_text | closed | hidden text: '월 통합 할인한도' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-7 | hidden_text | closed | hidden text: '10만원 이상 ~ 30만원 미만' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-8 | hidden_text | closed | hidden text: '30만원 이상 ~ 50만원 미만' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-9 | hidden_text | closed | hidden text: '실적조건 없이 혜택을 제공합니다.' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-10 | hidden_text | closed | hidden text: '디지로카 Las Vegas 할인 공통기준' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-11 | hidden_text | closed | hidden text: '롯데카드에 등록된 가맹점 및 업종을 기준으로 혜택이 제공됩니다.' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-12 | hidden_text | closed | hidden text: '할인 적용 제외 대상' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-13 | hidden_text | closed | hidden text: '디지로카 Las Vegas 카드가 아닌 롯데카드 이용금액, 모든 무이자할부 이용금액, 거래 취소금액, 국세,' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-14 | hidden_text | closed | hidden text: '디지로카 Las Vegas 카드로 국내 가맹점에서 5만원 이상 2~3개월 할부 결제 시 무이자 할부 혜택이 ' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-15 | hidden_text | closed | hidden text: '국내 가맹점 2~3개월 무이자 할부 혜택은 지난달 실적 조건 없이 제공됩니다.' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-16 | hidden_text | closed | hidden text: '해외 및 일시불 이용 건을 할부로 전환하거나, 할부 개월 수 변경 시 무이자 할부 혜택이 제공되지 않습니다.' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-17 | hidden_text | closed | hidden text: '무이자 할부 혜택이 제공된 결제 건은 다른 결제일 할인 및 포인트 적립 혜택이 제공되지 않습니다.' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-18 | hidden_text | closed | hidden text: '무이자 할부 적용 제외 대상' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-19 | hidden_text | closed | hidden text: '디지로카 Las Vegas 카드가 아닌 롯데카드 이용금액, 국세, 지방세, 건강보험, 국민연금, 고용보험, ' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-20 | hidden_text | closed | hidden text: '롯데카드의 다른 결제일 할인(청구할인) 혜택과 중복 시 할인금액이 큰 혜택이 제공됩니다.' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-21 | hidden_text | closed | hidden text: '(중복 혜택 적용 불가)' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-22 | hidden_text | closed | hidden text: '본인카드와 가족카드의 월 할인한도는 합산되며, 남은 월 할인한도는 이월되지 않습니다.' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-23 | hidden_text | closed | hidden text: '할부 결제 건은 이용일을 기준으로 전체 이용금액에 대하여 할인 혜택이 제공됩니다.' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-24 | hidden_text | closed | hidden text: '건당 결제 금액은 롯데카드에 접수된 건당 금액 기준으로 혜택이 제공됩니다. (항공, 철도 등 일부 가맹점의 ' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-25 | hidden_text | closed | hidden text: '해외 이용 시 별도의 수수료가 부과되오니, 상품설명서 뒷면을 확인해주세요.' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-26 | hidden_text | closed | hidden text: '해외 이용금액은 롯데카드에 접수되는 현지 매출일자를 기준으로 혜택이 제공되며, 롯데카드에 접수된 후 확인 가' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-27 | hidden_text | closed | hidden text: '한달 동안 이용한 금액이 다음 달에 결제되는 결제 건은(이동통신 등) 롯데카드에 접수되는 일자를 기준으로 혜' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-28 | hidden_text | closed | hidden text: '승인시점 기준으로 남은 할인한도 내에서 할인 혜택이 제공됩니다.' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-29 | hidden_text | closed | hidden text: '할인 혜택이 제공된 결제 건을 취소하는 경우 취소 건이 롯데카드에 접수된 후(약2~3일 소요) 할인 한도가 ' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-30 | hidden_text | closed | hidden text: '할인한도가 복원되기 전의 결제 건은 승인 시점 기준 할인한도로 할인 혜택이 제공되며, 한도 복원 후에' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-31 | hidden_text | closed | hidden text: '즉시 할인이 되지 않을 수 있습니다.' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-32 | hidden_text | closed | hidden text: '결제 취소 건 접수 내역은 롯데카드 홈페이지( ) 에서 회원가입 후 MY > 이용내역(매출전표) > 정상·취' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-33 | hidden_text | closed | hidden text: 'www.lottecard.co.kr' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-34 | hidden_text | closed | hidden text: '롯데멤버스㈜ 고객정보 제공에 동의하신 회원만 L.POINT 회원가입이 가능합니다.' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-35 | hidden_text | closed | hidden text: 'L.POINT는 L.POINT 제휴사 이용 시 결제금액에 따라 적립받고, 현금처럼 사용 가능한 포인트 입니다' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-36 | hidden_text | closed | hidden text: '디지로카 Las Vegas 카드로 결제 시, 롯데카드가 제공하는 L.POINT 적립 서비스가 제공되지 않습니' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-37 | hidden_text | closed | hidden text: 'L.POINT의 사용과 적립에 관한 자세한 내용은 L.POINT 홈페이지()에서 확인할 수 있습니다.' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-38 | hidden_text | closed | hidden text: 'www.lpoint.com' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-39 | hidden_text | closed | hidden text: '해외 겸용(MASTER,VISA,AMEX)' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-40 | hidden_text | closed | hidden text: '가족카드 발급 시 본인카드의 제휴 연회비가 청구됩니다.' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-41 | hidden_text | closed | hidden text: '카드 연회비(기본 연회비+제휴 연회비)는 카드 별로 청구됩니다.' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-42 | hidden_text | closed | hidden text: '회원이 유효기간이 다가오기 전에 카드를 해지하는 경우, 연회비 반환 금액은 회원이 카드사와 계약을 해지한 날' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-43 | hidden_text | closed | hidden text: '신규 가입연도의 카드 발행, 배송 등 카드발급에 소요된 비용은 반환금액에서 제외되며, 제휴연회비가 있는 경우' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-44 | hidden_text | closed | hidden text: '연회비는 계약을 해지한 날부터 영업일 기준 10일 이내 반환하여 드립니다.단, 부가서비스 제공내역 확인에 시' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-45 | hidden_text | closed | hidden text: '가족카드 연회비는 각 상품별 연회비 부과기준을 따르며, 가족카드 발급매수는 제한이 없습니다.' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-46 | hidden_text | closed | hidden text: '가족카드의 부가서비스 이용 조건 및 제공 범위는 본인카드의 이용 조건 및 제공 범위와 동일하며 본인카드와 합' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-47 | hidden_text | closed | hidden text: '가족카드 연말정산 시 가족카드 신용카드 등 이용금액은 가족카드 명의자(카드에 표기된 이름)의 신용카드 등 이' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-48 | hidden_text | closed | hidden text: '가족회원이 카드사용 내역에 대한 알림을 받고자 하는 경우 고객센터(1588-8100)에서 별도 신청해야 합니' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-49 | hidden_text | closed | hidden text: '가족카드 이용대금명세서는 본인회원이 지정한 주소 및 방법으로 발송됩니다.' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-50 | hidden_text | closed | hidden text: '가족카드 이용으로 적립된 롯데카드 포인트는 양도가 불가하며, 본인회원 포인트로 합산되어 적립·사용 가능합니다' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-51 | hidden_text | closed | hidden text: '이혼, 사망, 파양 등 가족관계 변동 시 본인회원 또는 가족회원이 고객센터(1588-8100) 및 홈페이지·' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-52 | hidden_text | closed | hidden text: '가족관계 변동이 되었음에도 가족카드를 정지 또는 해지하지 않은 경우 본인회원에게 의도하지 않은 카드사용 및 ' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-53 | hidden_text | closed | hidden text: '본인회원이 요청할 경우 가족회원의 동의없이 가족카드가 한도감액·정지·해지될 수 있습니다.' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-54 | hidden_text | closed | hidden text: '추가적인 혜택(포인트 및 할인혜택 등)에는 제공조건 및 한도 등이 적용됩니다.' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-55 | hidden_text | closed | hidden text: '카드 이용 시 제공되는 추가적인 혜택은 카드 신규출시 이후 3년 이상 축소·폐지 없이 유지됩니다.' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-56 | hidden_text | closed | hidden text: '상기에도 불구하고, 다음과 같은 사유가 발생한 경우 카드사는 추가적인 혜택을 변경할 수 있습니다.' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-57 | hidden_text | closed | hidden text: '① 카드사의 휴업·파산·경영상의 위기 등에 따른 불가피한 경우' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-58 | hidden_text | closed | hidden text: '② 제휴업체의 휴업·파산·경영상의 위기로 인해 불가피하게 부가서비스를 축소·변경하는 경우로서 다른 제휴업체를' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-59 | hidden_text | closed | hidden text: '③ 제휴업체가 카드사의 의사에 반하여 해당 부가서비스를 축소하거나 변경 시, 당초 부가서비스에 상응하는 다른' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-60 | hidden_text | closed | hidden text: '④ 부가서비스를 3년 이상 제공한 상태에서 해당 부가서비스로 인해 상품의 수익성이 현저히 낮아진 경우' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-61 | hidden_text | closed | hidden text: '카드사가 부가서비스를 변경하는 경우에는 변경 사유, 변경 내용 등을 사유발생 즉시 아래의 고지 방법 중 2가' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-62 | hidden_text | closed | hidden text: '고지방법: 서면교부, 우편 또는 전자우편, 전화 또는 팩스, 휴대폰 메시지 또는 이에 준하는 전자적 의사표시' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-63 | hidden_text | closed | hidden text: '결제일 카드대금 납부: 결제계좌 개설기관의 영업 마감시간(16시) 이후 결제계좌에 입금된 금액은 개설기관의 ' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-64 | hidden_text | closed | hidden text: '다수의 신용카드 발급은 개인 신용평점, 이용한도 등에 영향을 미칠 수 있습니다.' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-65 | hidden_text | closed | hidden text: '계약체결 전 금융상품설명서와 약관을 확인하시기 바랍니다.' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-66 | hidden_text | closed | hidden text: '신용카드 발급이 부적정한 경우(개인신용평점 낮음 등) 카드발급이 제한될 수 있습니다.' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-67 | hidden_text | closed | hidden text: '카드이용대금과 이에 수반되는 모든 수수료를 지정된 대금결제일에 상환해야 합니다.' | interact expand div.collapse.collapse-arrow > input:nth-of-… |
| gap-68 | hidden_text | closed | hidden text: '금융소비자는 금소법 제19조 제1항에 따라 해당상품 또는 서비스에 대하여 설명을 받을 권리가 있으며, 그 설' | interact expand div.collapse.collapse-arrow > input:nth-of-… |

| 턴 | 도구 | 인자 | 대상 공백 | 결과 |
|---|---|---|---|---|
| 1 | inspect_page | {} |  | - |
| 2 | interact | {"action": "expand", "selector": "div.collapse.collapse-arrow > input… | gap-1 | 새 증거 |
| 3 | inspect_page | {} |  | - |
| 4 | submit_rule | {"product_name": "디지로카 Las Vegas", "summary": "Selectors that capture… |  | - |
| 5 | probe_selector | {"selectors": ["h3.tit", "h1", "h2", "div.detail h2", "div.detail h3"… |  | - |
| 6 | submit_rule | {"product_name": "디지로카 Las Vegas", "summary": "Selectors capturing th… |  | - |
| 7 | submit_rule | {"product_name": "디지로카 Las Vegas", "summary": "Selectors capturing th… |  | - |
| 8 | submit_rule | {"product_name": "디지로카 Las Vegas", "summary": "Selectors capturing th… |  | - |
| 9 | submit_rule | {"product_name": "디지로카 Las Vegas", "summary": "Selectors capturing th… |  | - |
| 10 | submit_rule | {"product_name": "디지로카 Las Vegas", "summary": "Selectors capturing th… |  | - |
| 11 | submit_rule | {"product_name": "디지로카 Las Vegas", "summary": "Selectors capturing th… |  | - |

## 11. 증거 카드와 조사 공백

- 상태: 완료, 카드 18건, 검증 탈락 0건
- 카드는 원문 인용과 출처(`dom-N`)가 코드로 재확인된 사실 단위이며, 법률 판단이 아닙니다.

| 카드 | 종류 | 인용 | 조건 | 예외 | 출처 | 가시성 |
|---|---|---|---|---|---|---|
| c1 | benefit_claim | 100,000원 |  |  | dom-10 | default_visible |
| c2 | benefit_claim | 결제금액 최대 2% |  |  | dom-14 | default_visible |
| c3 | benefit_claim | 최대 10만원 할인 |  |  | dom-15 | default_visible |
| c4 | benefit_claim | * 건당 결제금액별로 0.5%~2% 할인율 적용 |  |  | dom-16 | default_visible |
| c5 | condition | 실적조건 없이 혜택을 제공합니다. |  |  | dom-37 | revealed |
| c6 | exception | 디지로카 Las Vegas 카드가 아닌 롯데카드 이용금액, 모든 무이자할부 이용금액, 거래 취소금액, 국세, 지방세, 건강보… |  |  | dom-40 | default_visible |
| c7 | benefit_claim | 디지로카 Las Vegas 카드로 국내 가맹점에서 5만원 이상 2~3개월 할부 결제 시 무이자 할부 혜택이 제공됩니다. |  |  | dom-44 | default_visible |
| c8 | condition | 국내 가맹점 2~3개월 무이자 할부 혜택은 지난달 실적 조건 없이 제공됩니다. | 지난달 실적 조건 없이 |  | dom-45 | default_visible |
| c9 | exception | 무이자 할부 혜택이 제공된 결제 건은 다른 결제일 할인 및 포인트 적립 혜택이 제공되지 않습니다. |  |  | dom-47 | default_visible |
| c10 | exception | 디지로카 Las Vegas 카드가 아닌 롯데카드 이용금액, 국세, 지방세, 건강보험, 국민연금, 고용보험, 산재보험, 초·중… |  |  | dom-49 | default_visible |
| c11 | condition | 롯데카드의 다른 결제일 할인(청구할인) 혜택과 중복 시 할인금액이 큰 혜택이 제공됩니다. (중복 혜택 적용 불가) | (중복 혜택 적용 불가) |  | dom-53 | default_visible |
| c12 | condition | 본인카드와 가족카드의 월 할인한도는 합산되며, 남은 월 할인한도는 이월되지 않습니다. |  |  | dom-54 | default_visible |
| c13 | condition | 건당 결제 금액은 롯데카드에 접수된 건당 금액 기준으로 혜택이 제공됩니다. (항공, 철도 등 일부 가맹점의 사정에 따라 결제… |  |  | dom-56 | revealed |
| c14 | warning | 해외 이용 시 별도의 수수료가 부과되오니, 상품설명서 뒷면을 확인해주세요. |  |  | dom-57 | revealed |
| c15 | condition | 해외 이용금액은 롯데카드에 접수되는 현지 매출일자를 기준으로 혜택이 제공되며, 롯데카드에 접수된 후 확인 가능합니다. |  |  | dom-58 | revealed |
| c16 | exception | 디지로카 Las Vegas 카드로 결제 시, 롯데카드가 제공하는 L.POINT 적립 서비스가 제공되지 않습니다. |  |  | dom-67 | default_visible |
| c17 | rate_claim | 연체이자율: 회원별·이용상품별 약정이율+최대 3%, 법정 최고금리(연 20%) 이내 |  |  | dom-114 | default_visible |
| c18 | footnote | ※ 카드출시일 : 2024년 05월 31일 |  |  | dom-121 | default_visible |

| 공백 | 종류 | 상태 | 관련 카드 |
|---|---|---|---|
| - | claim_without_visible_condition | open | c1, c2, c3, c4, c7, c17 |

## 12. 참고 사례 (판정에 사용하지 않음)

- 아래 사례는 비슷한 표시 유형을 찾아 참고로만 연결한 것입니다. 이 검토의 적합·부적합 판정은 사례와 무관하게 루브릭과 페이지 인용으로만 정해졌습니다.
- 상태: 부분 완료 (사례 연결이 턴 한도 8로 중단되어 그때까지 검증된 연결만 보고함), 후보 13건, 연결 agent(검색 5회, 읽기 5회, 중단 사유 max_turns), 사례 출처 db
- 연결은 agent가 제안하고, 코드가 페이지 인용과 사례 인용을 원문에서 다시 찾아 확인한 것만 남겼습니다.

| 사례 | 카드 | 페이지 인용 | 사례 인용 | 중요한 차이 | 페이지 단독 판단 | 공식 출처 |
|---|---|---|---|---|---|---|
| case.crefia_ad_type_unconditional_discount | c5, c8 | 국내 가맹점 2~3개월 무이자 할부 혜택은 지난달 실적 조건 없이 제공됩니다. | 단, 할인한도나 실적 조건이 없는 경우 '한도 조건 없이 할인되는 카드', '실적 조건없이 할인 되는 카드… | 페이지에는 혜택 제외 대상(대상 가맹점·공과금 등)을 상세히 나열(c10)하고 있음 — 사례는 제외대상 존재 여부를 문제로 삼음; 카드의 무이… | full | https://customer.crefia.or.kr/common/forward.xx?url=%2Fcustomer%2Freceipt%2FfalseHype%2FfalseHypeCase |
| case.fss_20241007_interest_free_benefit_exclusion | c9, c7, c10 | 무이자할부 혜택이 제공된 결제 건은 다른 결제일 할인 및 포인트 적립 혜택이 제공되지 않습니다. | 또한, 무이자할부를 이용할 경우에는 실적 산정, 포인트·마일리지 적립 및 할인 등이 제외되는 조건의 신용카… | 사례는 안내 누락을 문제삼았으나 페이지에는 무이자할부 시 제외된다는 문구(c9)를 명시하고 있음; 페이지의 제외대상 목록(c10)은 사례의 일… | full | https://www.fss.or.kr/fss/bbs/B0000188/view.do?nttId=187481&menuNo=200218 |
| case.kca_20170930_telco_card_addon_ad_conceal | c2, c3, c4, c1 | 최대 10만원 할인 | 제휴카드의 최대 할인금액 등 소비자에게 유리한 정보는 매우 큰 글자로 강조되어 있는 반면, 소비자에게 불리… | 사례는 옥외광고(통신단말기) 조사 결과로 상품유형은 유추에 해당함, 본 페이지는 신용카드 상품 설명 페이지임(product_basis 유추);… | full | https://www.kca.go.kr/smartconsumer/sub.do?menukey=7301&mode=view&no=1002635168&page=11&cate=00000057 |

---

이 문서는 자동 검토 결과입니다(ai-generated). 게시 여부의 최종 판단은 컴플라이언스 담당자가 합니다.
