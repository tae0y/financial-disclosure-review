---
ai-generated: true
human-review: false
---

# 금융상품 판매화면 검토 결과

- 판정: **판정 불가**
- 조치 방침: judge_explanation_duty 단계에서 실행이 중단되어(비용 한도 도달) 자동 판정을 내리지 않았습니다.
- 대상 화면: https://www.shinhancard.com/pconts/html/card/apply/credit/2013774_2207.html
- 상품명: 신한카드 Hi-Point Plan
- 상품유형/화면유형: 신용카드 / 상품광고
- 분류 근거: 인용문에 '신용카드 발급'이라는 문구가 명확히 있어 이 페이지는 특정 신용카드의 발급·혜택·연회비 등을 안내하는 신용카드 상품 페이지임을 보여줍니다.
- 페이지 수집: 완료 (reachable_coverage)
- 에이전트 실행: 페이지 탐색 agent 10턴(reachable_coverage) · 사례 연결 agent 8턴(max_turns) · 독자 선택 상품유형 기본 조건

## 1. 담당자 조치 목록

1. 검토 중단(비용 한도 도달): run budget $0.15 reached ($0.155067) before FidelityDiffs
2. 한도를 조정해 재실행하거나 사람이 페이지 전체를 직접 검토

## 2. 검토 요약

| 검토 영역 | 검토 항목 | 위반·반려 | 판정 불가·차이 |
|---|---|---|---|
| 표시방법 | 8 | 0 | 4 |
| 설명의무(원문) | 0/0 | 0 | 0 |
| 설명의무(독자 맞춤 설명) | 0/0 | 0 | 0 |
| 독자 맞춤 설명 | 17 | 2 | 0 |

## 3. 확인이 필요한 항목

| 항목 | 대상 | 판정 | 구분 | 사유 | 인용 |
|---|---|---|---|---|---|
| E02 | 판매 화면 표시방법 | 판정 불가 | - | a pass would be unproven: 3 labelled block(s) never visible |  |
| E04 | 판매 화면 표시방법 | 판정 불가 | - | a pass would be unproven: 1 labelled block(s) never visible; image-backed text without a readable crop: ['b69']; contrast unmeasured: ['b69'] |  |
| E05 | 판매 화면 표시방법 | 판정 불가 | - | a pass would be unproven: 3 labelled block(s) never visible; image-backed text without a readable crop: ['b69']; contrast unmeasured: ['b69'] |  |
| E07 | 판매 화면 표시방법 | 판정 불가 | - | 초기 캡처에서 보이지 않는 H 표기 블록들만 존재하고(D로 사용자가 나타낸 증거가 없음) 사용자가 실제로 페이지에서 해당 정보들을 '숨김'으로 접했는지 확인할 수 있는 D 블록 근거가 없습니다. |  |
| 원문 대체 | 독자 맞춤 설명 dom-110,dom-111,dom-116,dom-117,dom-118,dom-119,dom-94,dom-95,dom-96 | 원문 대체 | - | exact_fact를 근거 원문에서 확인할 수 없음 |  |
| 원문 대체 | 독자 맞춤 설명 dom-28,dom-34,dom-38 | 원문 대체 | - | 근거 원문에 없는 수치: 2026, 9 |  |

## 4. 표시방법 검토 상세

| 항목 | 판정 | 근거 블록 | 사유 |
|---|---|---|---|
| E01 | 적합 | b13, b26, b31, b18, b20 | 혜택 문구(예: b13, b26, b31)는 상대적으로 큰 글자(최대 13.5pt, 최소 10.5pt)와 높은 명암(예: b13 cr5.34, b26 cr16.03)로 강조되어 있고, 불이익 표기(예: b18, b20)는 더 작은 글자(9.0–10.5pt)와 회색 계열 색상으로 덜 강조되어 있어 균형을 잃지 않았습니다. |
| E02 | 판정 불가 |  | a pass would be unproven: 3 labelled block(s) never visible |
| E03 | 적합 | b60, b61, b62, b67, b68, b69 | 연체·경고문구들(b60,b61,b62,b67,b68,b69)은 기준(기본 weight 300)에 비해 굵은 글씨(w500)로 표시되어 다른 안내문과 구별되어 있습니다. |
| E04 | 판정 불가 |  | a pass would be unproven: 1 labelled block(s) never visible; image-backed text without a readable crop: ['b69']; contrast unmeasured: ['b69'] |
| E05 | 판정 불가 |  | a pass would be unproven: 3 labelled block(s) never visible; image-backed text without a readable crop: ['b69']; contrast unmeasured: ['b69'] |
| E06 | 적합 | b55, b56, b57, b58, b59, b60, b61, b62, b63, b65, b66, b67, b68 | 의무표시 항목들이 문장별로 줄바꿈되어 각 블록이 단독 한 줄(b55, b56, b57, b58, b59, b60, b61, b62, b63, b65, b66, b67, b68)로 분리되어 있습니다. |
| E07 | 판정 불가 |  | 초기 캡처에서 보이지 않는 H 표기 블록들만 존재하고(D로 사용자가 나타낸 증거가 없음) 사용자가 실제로 페이지에서 해당 정보들을 '숨김'으로 접했는지 확인할 수 있는 D 블록 근거가 없습니다. |
| E08 | 적합 | b13, b31, b32, b60 | 혜택의 최대치 표기(예: b13 '최대 1.5% 적립')와 그 적용 조건·세부사항(b31, b32) 및 관련 이자·수수료 안내(b60)가 같은 페이지에 함께 제시되어 있어 짝이 되는 주요 정보를 누락하지 않았습니다. |

## 5. 설명의무 검토 상세 (원문 대비 독자 맞춤 설명)

(해당 항목 없음)

- F01–F19·F21·F22는 같은 의무를 담은 설명 코드(설명01–19·27·28)와 한 주제입니다. 표에는 둘 다 남기고, 조치 목록에서는 같은 판정이면 한 번만 셉니다.

## 6. 독자 맞춤 설명 결과

- 상태: 완료 (2개 단위는 코드 검증에 걸려 원문으로 대체됨)
- 독자 프로필: nemotron:0851bae336c84f3698ea0f6fcb0d03e4 vt1@ada0f5b (nvidia/Nemotron-Personas-Korea rev=ada0f5b uuid=0851bae336c84f3698ea0f6fcb0d03e4 (CC-BY-4.0), ai-drafted, 적용)
- 독자 선택: 상품유형 기본 조건, 조건 {'age_min': 20}, 일치 989509행
- 금융 익숙도: 낮음 (행 속성 추정)
- 독자 개요(합성 페르소나): 93세 남자 · 학력 초등학교 · 직업 무직 · 전북 거주 · 가구 배우자와 거주 이창식 씨는 전주에서 아내와 거주하며 신문 읽기와 소소한 집수리를 즐기는, 엄격한 자기관리와 성실함을 삶의 훈장으로 여기는 93세 어르신입니다.
- 원문 사실(exact_fact)은 설명 옆에 그대로 남습니다. 위험 개념에는 비유를 쓰지 않습니다.

| 단위 | 출처 | 원 사실 | 설명 | 비유 | 상태 |
|---|---|---|---|---|---|
| u1 | dom-0 | 신한카드 Hi-Point Plan | 이 카드의 이름입니다. 안내문이나 고객센터에서 같은 이름으로 확인하세요. | - | accepted |
| u2 | dom-6 | 국내전용 2만원 (기본) | 국내전용 카드의 기본 연회비는 "2만원"입니다. 연회비가 얼마인지 알고 싶을 때 금액이 이 표시와 같은지 확인하세요. | - | accepted |
| u3 | dom-7 | Mastercard 2만3천원 (기본) | 해외겸용(Mastercard) 기본 연회비는 "2만3천원"입니다. 카드 종류에 따라 연회비가 달라집니다. | - | accepted |
| u4 | dom-8 | Visa 2만3천원 (기본) | 해외겸용(Visa) 기본 연회비는 "2만3천원"입니다. 어떤 국제 브랜드인지 확인하세요. | - | accepted |
| u5 | dom-9 | 신규 고객 전용 이벤트 연회비 100% 캐시백 | 신규 고객 전용 이벤트로 연회비를 "100% 캐시백"해 준다고 안내되어 있습니다. 안내문에 적힌 '신규 고객 전용'이라는 문구를 먼저 확인하세요. | 이벤트로 연회비를 돌려받는 것은 일시적으로 낸 돈을 나중에 그대로 돌려… | accepted |
| u6 | dom-21 | 연회비는 기본 연회비와 서비스 연회비를 합산해 카드별로 청구됩니다. | 청구되는 연회비는 '기본 연회비'와 '서비스 연회비'를 더한 금액입니다. 한 번에 묶어서 청구됩니다. | - | accepted |
| u7 | dom-22 | 가족카드는 연회비가 없습니다.(단, 가족카드 단독으로 발급받을 경우 연회비가 부과됩니다.) | 가족카드는 보통 연회비가 없다고 명시되어 있습니다. 다만 가족카드를 혼자 따로 발급받으면 연회비가 붙을 수 있다는 점을 확인하세요. | - | accepted |
| u8 | dom-13, dom-14, dom-92, dom-93 | 기본 적립 : 국내/외 이용금액 최대 1.5% 마이신한포인트 적립 특별 적립 : 생활 밀착 가맹점 최대 5% 마이신한포인트 … | 기본적으로는 사용액에 따라 포인트를 적립합니다. 특별 가맹점에서는 더 높은 적립률을 줍니다. 두 종류 적립을 합쳐 한 달에 "월 5만 포인트"까지만 모아집니다.… | - | accepted |
| u9 | dom-68, dom-69, dom-70, dom-71, dom-73, dom-74, dom-75 | 0.5% 1% 1.3% 1.5% 2% 3.5% 5% | 상품 안내표에 여러 적립률 항목이 숫자 형태로 표시되어 있습니다. 각 항목은 위에 적힌 퍼센트 값들입니다. 어느 거래에 어떤 비율이 적용되는지는 안내문에서 해당… | - | accepted |
| u10 | dom-16, dom-105, dom-106, dom-107 | 마이신한포인트 1만 포인트 이상 사용 결제 시 1천 포인트 리필 적립(월 1회) 포인트 리필 서비스는 전월 실적 조건없이 월… | 마이신한포인트를 "1만 포인트" 이상 써서 결제하면 한 달에 한 번 "1천 포인트"를 더 줍니다. 이 리필은 전월 실적을 따지지 않습니다. 리필 포인트는 대상 … | - | accepted |
| u11 | dom-110, dom-111, dom-116, dom-117, dom-118, dom-119, dom-94, dom-95, dom-96 | 온라인 결제가 제공되는 서비스는 해당 업체 사이트(앱)에 직접 접속하여 이용하는 경우에만 서비스가 적용됩니다. 가맹점 정보가… | 서비스 적용에서 제외되는 항목들이 여러 가지 있습니다. 온라인 혜택은 반드시 업체 사이트나 앱에 직접 들어가 결제해야 적용됩니다. 결제대행(PG)이나 간편결제 … | - | reverted |
| u12 | dom-28, dom-34, dom-38 | 카드 이용 시 제공되는 포인트 및 할인 혜택 등의 부가서비스는 카드 신규출시(2026.06.09) 이후 3년 이상 축소·폐지… | 카드는 2026년 6월 9일에 출시되었습니다. 출시 후 최소 "3년" 동안은 포인트·할인 같은 부가서비스를 줄이거나 없애지 않겠다고 안내되어 있습니다. 다만 부… | - | reverted |
| u13 | dom-132, dom-135 | 전월 이용금액은 ‘신한카드 Hi-Point Plan’의 전월(1일~말일) 거래 시점 이용금액(일시불+할부)을 기준으로 반영됩… | 전월 실적은 매달 1일부터 말일까지의 거래 금액(일시불과 할부 모두)을 따집니다. 본인 카드와 가족카드의 이용금액과 한도는 합쳐서 봅니다. 가족카드로 쓰면 전체… | - | accepted |
| u14 | dom-23 | 후불교통 기능이 있는 카드로만 신청 가능합니다. | 이 카드는 '후불교통 기능이 있는 카드'로만 신청할 수 있다고 적혀 있습니다. 신청 전에 본인의 카드 옵션을 확인하세요. | - | accepted |
| u15 | dom-24 | 신한카드 Hi-Point Plan은 1인 2장 이상 중복 발급 및 소지가 불가합니다.(제휴상품 포함) | 한 사람당 이 카드를 두 장 이상 가질 수 없다고 명시되어 있습니다. 제휴상품도 포함됩니다. 중복 발급 여부를 확인하세요. | - | accepted |
| u16 | dom-25 | 해외겸용(Mastercard, VISA)은 컨택리스 결제를 지원합니다. | 해외겸용 카드(Mastercard, VISA)는 비접촉 결제(카드를 대고 결제하는 방식)를 지원한다고 적혀 있습니다. 편하게 쓸 수 있는 기능입니다. | - | accepted |
| u17 | dom-41 | 연체이자율은 ‘회원별, 이용상품별 약정금리+최대 연 3%, 법정 최고금리(연 20%)이내'에서 적용됩니다. 단, 연체 발생 … | 돈을 제때 못 내면 적용되는 연체이자율은 '약정금리+최대 연 3%' 범위 안에서 정해집니다. 다만 법이 정한 최고금리(연 "20%")를 넘지 않습니다. 연체가 … | - | accepted |

### 운영 통제 (판정 대상 아님)

- 화면: AI 생성 고지, 원문 보기 전환, 오류 신고
- 거버넌스: 사람 승인, 변경 관리, 프로필 검토

## 7. 자동 검증 결과

- 통과: None
- 실패 모듈: 없음
- 검증 루프: None회 (최대 2회)
- 중단 사유: 비용 한도 도달 — run budget $0.15 reached ($0.155067) before FidelityDiffs
- 재시도 이력: 없음


## 8. 비용과 소요시간

아래 수치는 **이 문서를 만든 실행**에서 발생한 것입니다.

- 모델 호출 26회, 입력 285,578 tokens, 출력 41,835 tokens
- 비용 $0.155067 (약 217.1원, 1400.0원/$ 가정)
- 소요시간 467.0초
- 상한: {'max_calls': 60, 'max_usd': 0.15}
- 단계별: discover 10회 $0.0399, case_link 8회 $0.0264, ExplanationJudgments 1회 $0.0206, EvidenceCardDrafts 1회 $0.0167, PersonaUnitDrafts 1회 $0.0158, DisplayVerdicts 1회 $0.0104, DisplayLabels 1회 $0.0100, PlainJudgments 1회 $0.0091, ClassifyAnswer 1회 $0.0059, vision 1회 $0.0003

## 9. 한계와 가정

- 이 검토는 공개된 광고성 화면을 대상으로 하며, 청약 단계 설명화면은 범위에 없습니다. 설명의무 기준은 준용해 품질 기준으로 적용했습니다.
- 자동 검증은 인용 근거의 존재와 모듈 간 모순만 확인합니다. 통과가 법률 준수를 보증하지 않습니다.
- 10 images in the selected html, 7 without alt text; text inside images is not measurable. Flagged by the model: none
- CSS background images and overlapping img bounds flag risky blocks; captured crops are checked by vision for E04/E05. Pseudo-elements and image-only text remain unmeasured.
- 가정: E02 says 8pt on A4. A web page has no paper size, so the node uses computed CSS px x 0.75 >= 8pt at the captured viewport.
- 가정: No threshold in the rubric. The node uses the WCAG 2.1 SC 1.4.3 AA ratio: 4.5:1 for normal text, 3.0:1 for large text (>= 24px, or >= 18.66px and weight >= 700). Text and background colors come from the snapshot (blended background when captured); Image-backed blocks are checked from saved rendered…
- 독자 맞춤 설명 2개 단위는 검사를 통과하지 못해 원문 문장으로 되돌렸습니다.
- 독자 맞춤 설명은 독자 프로필 nemotron:0851bae336c84f3698ea0f6fcb0d03e4 vt1@ada0f5b(ai-drafted, 적용) 기준의 보조 설명이며, 원문을 대신하거나 독자의 자격·혜택·상환액을 판단하지 않습니다.
- 조사 공백 82건(claim_without_visible_condition, hidden_text)은 누락의 증거가 아니라 확인하지 못한 범위입니다.

## 10. 페이지 수집 agent 기록

- 상태: 완료, 중단 사유: reachable_coverage
- 조사 범위(전 → 후): {'hidden_text_blocks': 79, 'visible_text_blocks': 86, 'candidate_controls': 3, 'open_gaps': 74} → {'hidden_text_blocks': 89, 'visible_text_blocks': 76, 'candidate_controls': 3, 'open_gaps': 81}
- `조사 불충분`은 누락의 증거가 아닙니다. 보이지 않은 조건은 위반이 아니라 조사 공백으로 남깁니다.
- 한계: 열 수 있는 컨트롤을 모두 시도해도 보이지 않은 숨김 글 80건은 상태 판단에서 제외했습니다. 이 글에 조건·예외가 있다면 이 검토는 확인하지 못했습니다.

| 공백 | 종류 | 상태 | 내용 | 닫은 행동 |
|---|---|---|---|---|
| gap-1 | unexpanded_control | closed | 주요 혜택 not yet expanded | interact expand a.shc-tab__btn.is-active (gap gap-1) |
| gap-2 | unexpanded_control | closed | 유의사항 not yet expanded | interact expand a.shc-tab__btn.is-active (gap gap-1) |
| gap-3 | unexpanded_control | closed | 부가서비스 변경가능 사유 not yet expanded | interact expand #accordion1 (gap gap-3) |
| gap-4 | hidden_text | open | hidden text: '2026.09.29 14:07:56' |  |
| gap-5 | hidden_text | unresolved | hidden text: '주요 혜택 상세 목록' |  |
| gap-6 | hidden_text | unresolved | hidden text: '온라인 신청하기' |  |
| gap-7 | hidden_text | unresolved | hidden text: '2026.01.08 - class삭제 or 수정 내게 맞는 카드 찾기' |  |
| gap-8 | hidden_text | unresolved | hidden text: '2026.01.08 - size-56-> size-28' |  |
| gap-9 | hidden_text | unresolved | hidden text: '포인트 적립 서비스 적립률 및 월 통합 적립 한도' |  |
| gap-10 | hidden_text | unresolved | hidden text: '월 이용금액(일시불+할부), 50만원 미만, 50만원 이상 100만원 미만, 100만원 이상 150만원 미만' |  |
| gap-11 | hidden_text | unresolved | hidden text: '포인트 적립 서비스 적립률 및 월 통합 적립 한도' |  |
| gap-12 | hidden_text | unresolved | hidden text: '전월 이용금액(일시불+할부)' |  |
| gap-13 | hidden_text | unresolved | hidden text: '50만원 이상100만원 미만' |  |
| gap-14 | hidden_text | unresolved | hidden text: '100만원 이상150만원 미만' |  |
| gap-15 | hidden_text | unresolved | hidden text: '150만원 이상' |  |
| gap-16 | hidden_text | unresolved | hidden text: '통합 적립 한도' |  |
| gap-17 | hidden_text | unresolved | hidden text: '특별 적립 영역' |  |
| gap-18 | hidden_text | unresolved | hidden text: '영역, 서비스 대상으로 구성된 표입니다.' |  |
| gap-19 | hidden_text | unresolved | hidden text: '특별 적립 영역 안내' |  |
| gap-20 | hidden_text | unresolved | hidden text: '롯데마트, 이마트' |  |
| gap-21 | hidden_text | unresolved | hidden text: '다이소, 올리브영' |  |
| gap-22 | hidden_text | unresolved | hidden text: 'SK에너지, GS칼텍스' |  |
| gap-23 | hidden_text | unresolved | hidden text: '스타벅스, 이디야, 커피빈, 투썸플레이스, 폴바셋, 메가커피' |  |
| gap-24 | hidden_text | unresolved | hidden text: 'SKT, LG U+, KT 통신요금 자동납부' |  |
| gap-25 | hidden_text | unresolved | hidden text: '기본 적립과 특별 적립을 통합하여 월 5만 포인트 한도까지 적립됩니다.' |  |
| gap-26 | hidden_text | unresolved | hidden text: '기본 적립과 특별 적립은 중복 적용되지 않으며, 특별 적립 영역 가맹점은 기본 적립 대상에서 제외됩니다.' |  |
| gap-27 | hidden_text | unresolved | hidden text: '해외이용금액의 경우 해외서비스수수료는 적립되지 않습니다.' |  |
| gap-28 | hidden_text | unresolved | hidden text: '해외 일시불 거래 후 할부로 전환(유이자 할부 전환 포함)하는 경우는 적립되지 않습니다.' |  |
| gap-29 | hidden_text | unresolved | hidden text: '해외 현금인출 이용금액은 적립되지 않습니다.' |  |
| gap-30 | hidden_text | unresolved | hidden text: '해외 이용 시 별도의 수수료가 부과됩니다. 자세한 내용은 안내장 뒷면 해외이용 확인사항을 확인해주세요.' |  |
| gap-31 | hidden_text | unresolved | hidden text: '특별 적립 영역은 오프라인 매장 이용 시에만 적립되며, 백화점, 할인점, 면세점, 공항 등 입점 매장 이용금' |  |
| gap-32 | hidden_text | unresolved | hidden text: '마트 영역은 대상 가맹점 외 창고형 할인매장(트레이더스 홀세일클럽 등), 기업형 슈퍼마켓(이마트 에브리데이,' |  |
| gap-33 | hidden_text | unresolved | hidden text: '마트 영역은 주차비, 문화센터 및 마트 내 입점된 임대 매장 이용 시에는 적립되지 않습니다.' |  |
| gap-34 | hidden_text | unresolved | hidden text: '주유 영역은 휘발유, 경유, 등유만 적립되며 LPG 이용금액은 적립되지 않습니다.' |  |
| gap-35 | hidden_text | unresolved | hidden text: '카페 영역은 스타벅스 사이렌오더 등 스마트 오더 이용 시에도 적립됩니다.' |  |
| gap-36 | hidden_text | unresolved | hidden text: '해외 스타벅스 가맹점 구매 금액 및 스타벅스 홈페이지/앱 내 선물하기 이용금액은 특별 적립되지 않습니다.' |  |
| gap-37 | hidden_text | unresolved | hidden text: '통신요금 자동납부 금액만 특별 적립되며, 자동납부 외 이용금액 및 알뜰폰 · 선불폰 · 결합상품(TV, 인터' |  |
| gap-38 | hidden_text | unresolved | hidden text: '포인트 리필 서비스는 전월 실적 조건없이 월 1회에 한해 제공됩니다.' |  |
| gap-39 | hidden_text | unresolved | hidden text: '서비스 대상 거래가 발생한 월의 다음달 20일(휴일인 경우, 다음 영업일)에 포인트가 적립됩니다.' |  |
| gap-40 | hidden_text | unresolved | hidden text: '포인트 적립 전 서비스 대상 거래가 부분 또는 전체 취소되어 해당 거래 건의 최종 포인트 사용 금액이 1만원' |  |
| gap-41 | hidden_text | unresolved | hidden text: '신한카드 Hi-Point Plan 서비스 적용 기준' |  |
| gap-42 | hidden_text | unresolved | hidden text: '서비스는 카드 이용 시 제공되는 포인트, 캐시백, 할인 혜택 등을 의미합니다.' |  |
| gap-43 | hidden_text | unresolved | hidden text: '온라인 결제가 제공되는 서비스는 해당 업체 사이트(앱)에 직접 접속하여 이용하는 경우에만 서비스가 적용됩니다' |  |
| gap-44 | hidden_text | unresolved | hidden text: '가맹점 정보가 해당 업체가 아닌 결제대행업체(PG) 또는 간편결제 전용 가맹점으로 확인되는 경우 ‘결제대행업' |  |
| gap-45 | hidden_text | unresolved | hidden text: '서비스가 제공된 결제 건이 취소될 경우, 이미 제공된 서비스 또는 향후 제공될 서비스 금액에서 우선 차감되며' |  |
| gap-46 | hidden_text | unresolved | hidden text: '서비스가 적용된 거래가 해당월에 취소된 경우 서비스 횟수 및 한도가 복원됩니다.' |  |
| gap-47 | hidden_text | unresolved | hidden text: '서비스 제외 대상은 아래와 같습니다.' |  |
| gap-48 | hidden_text | unresolved | hidden text: '단기카드대출(현금서비스), 장기카드대출(카드론)' |  |
| gap-49 | hidden_text | unresolved | hidden text: '연회비, 각종 수수료/이자(할부수수료, 연체이자 등)' |  |
| gap-50 | hidden_text | unresolved | hidden text: '기프트카드/선불카드 구매 · 충전금액' |  |
| gap-51 | hidden_text | unresolved | hidden text: '지방세, 국세, 세외수입(환경개선부담금, 과태료/범칙금/벌금, 여권 발급비용, 우편요금, 국가 공공기관 · ' |  |
| gap-52 | hidden_text | unresolved | hidden text: '4대보험(국민연금, 고용보험, 건강보험, 산재보험)' |  |
| gap-53 | hidden_text | unresolved | hidden text: '유치원/초중고 납입금(스쿨뱅킹), 대학(원)등록금' |  |
| gap-54 | hidden_text | unresolved | hidden text: '아파트관리비, 도시가스, 전기요금, TV수신료, 수도요금' |  |
| gap-55 | hidden_text | unresolved | hidden text: '포인트 사용거래 중 포인트금액' |  |
| gap-56 | hidden_text | unresolved | hidden text: '무이자할부(슬림할부 등 부분 무이자 포함) 이용거래' |  |
| gap-57 | hidden_text | unresolved | hidden text: '상품권/선불전자지급수단 구매 · 충전금액' |  |
| gap-58 | hidden_text | unresolved | hidden text: '포인트/캐시/사이버머니/예치금 등 전자지급(결제)수단 구매 · 충전금액' |  |
| gap-59 | hidden_text | unresolved | hidden text: '신한카드 Hi-Point Plan 서비스 이외의 프로모션 할인이 적용된 거래' |  |
| gap-60 | hidden_text | unresolved | hidden text: '의약품 전용몰(도매몰), 제약회사 업종 이용금액' |  |
| gap-61 | hidden_text | unresolved | hidden text: '신차판매 업종 이용금액' |  |
| gap-62 | hidden_text | unresolved | hidden text: '전월 이용금액 기준' |  |
| gap-63 | hidden_text | unresolved | hidden text: '전월 이용금액은 ‘신한카드 Hi-Point Plan’의 전월(1일~말일) 거래 시점 이용금액(일시불+할부)을' |  |
| gap-64 | hidden_text | unresolved | hidden text: '해외 이용금액은 매입일자를 기준으로 반영됩니다.' |  |
| gap-65 | hidden_text | unresolved | hidden text: '교통카드 이용금액은 전전월 이용금액이 전월 이용금액에 반영됩니다.(단, 모바일 후불 교통카드 이용금액은 전월' |  |
| gap-66 | hidden_text | unresolved | hidden text: '본인카드와 가족카드의 전월 이용금액 및 월별 적립 한도는 합산 적용됩니다.' |  |
| gap-67 | hidden_text | unresolved | hidden text: '거래 후 취소금액은 국내 거래의 경우 최초 승인된 달의 이용금액에서, 해외 거래의 경우 취소 전표가 매입된 ' |  |
| gap-68 | hidden_text | unresolved | hidden text: '서비스가 제공된 이후 결제 취소 등의 사유로 서비스 제공 조건을 미충족하게 되는 경우, 서비스 차액이 청구되' |  |
| gap-69 | hidden_text | unresolved | hidden text: '신한카드 Hi-Point Plan 최초 신규 발급 회원*은 카드 사용 등록한 월(간편결제 등록 포함)의 다음' |  |
| gap-70 | hidden_text | unresolved | hidden text: '전월 이용금액 제외 대상은 아래와 같습니다.' |  |
| gap-71 | hidden_text | unresolved | hidden text: '상품권/선불전자지급수단 구매 · 충전금액' |  |
| gap-72 | hidden_text | unresolved | hidden text: '포인트/캐시/사이버머니/예치금 등 전자지급(결제)수단 구매 · 충전금액' |  |
| gap-73 | hidden_text | unresolved | hidden text: '의약품 전용몰(도매몰), 제약회사 업종 이용금액' |  |
| gap-74 | hidden_text | unresolved | hidden text: '신차판매 업종 이용금액' |  |
| gap-75 | hidden_text | unresolved | hidden text: '카드 이용 시 제공되는 포인트 및 할인 혜택 등의 부가서비스는 카드 신규출시(2026.06.09) 이후 3년' |  |
| gap-76 | hidden_text | unresolved | hidden text: '상기에도 불구하고, 다음과 같은 사유가 발생한 경우 카드사는 부가서비스를 변경할 수 있습니다.' |  |
| gap-77 | hidden_text | unresolved | hidden text: '2026.05.14 문구 수정' |  |
| gap-78 | hidden_text | unresolved | hidden text: '카드사의 휴업·파산·경영상의 위기 등에 따른 불가피한 경우' |  |
| gap-79 | hidden_text | unresolved | hidden text: '제휴업체의 휴업·파산·경영상의 위기로 인해 불가피하게 부가서비스를 축소·변경하는 경우로서 다른 제휴업체를 통' |  |
| gap-80 | hidden_text | unresolved | hidden text: '제휴업체가 카드사의 의사에 반하여 해당 부가서비스를 축소하거나 변경 시, 당초 부가서비스에 상응하는 다른 부' |  |
| gap-81 | hidden_text | unresolved | hidden text: '부가서비스를 3년 이상 제공한 상태에서 해당 부가서비스로 인해 카드의 수익성이 현저히 낮아진 경우' |  |
| gap-82 | hidden_text | unresolved | hidden text: '카드사가 부가서비스를 변경하는 경우에는 부가서비스 변경 사유, 변경 내용 등을 사유발생 즉시 아래 고지방법 ' |  |
| gap-83 | hidden_text | unresolved | hidden text: '2026.05.14 문구 수정' |  |
| gap-84 | hidden_text | unresolved | hidden text: '고지 방법: 서면 교부, 우편 또는 전자우편, 전화 또는 팩스, 휴대폰 메시지 또는 이에 준하는 전자적 의사' |  |

| 턴 | 도구 | 인자 | 대상 공백 | 결과 |
|---|---|---|---|---|
| 1 | inspect_page | {} |  | - |
| 2 | probe_selector | {"selectors": ["h1", ".shc-article__title", "a.shc-tab__btn.is-active… |  | - |
| 3 | interact | {"action": "expand", "selector": "a.shc-tab__btn.is-active", "gap_id"… | gap-1 | - |
| 4 | inspect_page | {} |  | - |
| 5 | interact | {"action": "expand", "selector": "#accordion1", "gap_id": "gap-3", "e… | gap-3 | 새 증거 |
| 6 | inspect_page | {} |  | - |
| 7 | submit_rule | {"product_name": "신한카드 Hi-Point Plan", "summary": "Selectors that cap… |  | - |
| 8 | submit_rule | {"product_name": "신한카드 Hi-Point Plan", "summary": "Selectors capturin… |  | - |
| 9 | submit_rule | {"product_name": "신한카드 Hi-Point Plan", "summary": "Selectors capturin… |  | - |
| 10 | submit_rule | {"product_name": "신한카드 Hi-Point Plan", "summary": "Selectors capturin… |  | - |

## 11. 증거 카드와 조사 공백

- 상태: 완료, 카드 40건, 검증 탈락 0건
- 카드는 원문 인용과 출처(`dom-N`)가 코드로 재확인된 사실 단위이며, 법률 판단이 아닙니다.

| 카드 | 종류 | 인용 | 조건 | 예외 | 출처 | 가시성 |
|---|---|---|---|---|---|---|
| c1 | footnote | 신한카드 Hi-Point Plan |  |  | dom-0 | default_visible |
| c2 | fee_claim | 국내전용 2만원 (기본) |  |  | dom-6 | default_visible |
| c3 | fee_claim | Mastercard 2만3천원 (기본) |  |  | dom-7 | default_visible |
| c4 | fee_claim | Visa 2만3천원 (기본) |  |  | dom-8 | default_visible |
| c5 | benefit_claim | 신규 고객 전용 이벤트 연회비 100% 캐시백 |  |  | dom-9 | default_visible |
| c6 | benefit_claim | 기본 적립 : 국내/외 이용금액 최대 1.5% 마이신한포인트 적립 |  |  | dom-13 | default_visible |
| c7 | benefit_claim | 특별 적립 : 생활 밀착 가맹점 최대 5% 마이신한포인트 적립 |  |  | dom-14 | default_visible |
| c8 | benefit_claim | 마이신한포인트 1만 포인트 이상 사용 결제 시 1천 포인트 리필 적립(월 1회) |  |  | dom-16 | default_visible |
| c9 | fee_claim | 연회비는 기본 연회비와 서비스 연회비를 합산해 카드별로 청구됩니다. |  |  | dom-21 | default_visible |
| c10 | eligibility | 가족카드는 연회비가 없습니다.(단, 가족카드 단독으로 발급받을 경우 연회비가 부과됩니다.) |  |  | dom-22 | default_visible |
| c11 | eligibility | 후불교통 기능이 있는 카드로만 신청 가능합니다. |  |  | dom-23 | default_visible |
| c12 | eligibility | 신한카드 Hi-Point Plan은 1인 2장 이상 중복 발급 및 소지가 불가합니다.(제휴상품 포함) |  |  | dom-24 | default_visible |
| c13 | benefit_claim | 해외겸용(Mastercard, VISA)은 컨택리스 결제를 지원합니다. |  |  | dom-25 | default_visible |
| c14 | footnote | 카드 이용 시 제공되는 포인트 및 할인 혜택 등의 부가서비스는 카드 신규출시(2026.06.09) 이후 3년 이상 축소·폐지… |  |  | dom-28 | default_visible |
| c15 | condition | 카드사가 부가서비스를 변경하는 경우에는 부가서비스 변경 사유, 변경 내용 등을 사유발생 즉시 아래 고지방법 중 서로 다른 2… |  |  | dom-34 | default_visible |
| c16 | footnote | 카드 출시 일자: 2026.06.09 |  |  | dom-38 | default_visible |
| c17 | warning | 연체이자율은 ‘회원별, 이용상품별 약정금리+최대 연 3%, 법정 최고금리(연 20%)이내'에서 적용됩니다. 단, 연체 발생 … |  |  | dom-41 | default_visible |
| c18 | rate_claim | 0.5% |  |  | dom-68 | hidden |
| c19 | rate_claim | 1% |  |  | dom-69 | hidden |
| c20 | rate_claim | 1.3% |  |  | dom-70 | hidden |
| c21 | rate_claim | 1.5% |  |  | dom-71 | hidden |
| c22 | rate_claim | 2% |  |  | dom-73 | hidden |
| c23 | rate_claim | 3.5% |  |  | dom-74 | hidden |
| c24 | rate_claim | 5% |  |  | dom-75 | hidden |
| c25 | benefit_claim | 기본 적립과 특별 적립을 통합하여 월 5만 포인트 한도까지 적립됩니다. |  |  | dom-92 | hidden |
| c26 | condition | 기본 적립과 특별 적립은 중복 적용되지 않으며, 특별 적립 영역 가맹점은 기본 적립 대상에서 제외됩니다. |  |  | dom-93 | hidden |
| c27 | exception | 해외이용금액의 경우 해외서비스수수료는 적립되지 않습니다. |  |  | dom-94 | hidden |
| c28 | exception | 해외 일시불 거래 후 할부로 전환(유이자 할부 전환 포함)하는 경우는 적립되지 않습니다. |  |  | dom-95 | hidden |
| c29 | exception | 해외 현금인출 이용금액은 적립되지 않습니다. |  |  | dom-96 | hidden |
| c30 | benefit_claim | 포인트 리필 서비스는 전월 실적 조건없이 월 1회에 한해 제공됩니다. |  |  | dom-105 | default_visible |
| c31 | condition | 서비스 대상 거래가 발생한 월의 다음달 20일(휴일인 경우, 다음 영업일)에 포인트가 적립됩니다. |  |  | dom-106 | hidden |
| c32 | exception | 포인트 적립 전 서비스 대상 거래가 부분 또는 전체 취소되어 해당 거래 건의 최종 포인트 사용 금액이 1만원 미만이 되는 경… |  |  | dom-107 | default_visible |
| c33 | condition | 온라인 결제가 제공되는 서비스는 해당 업체 사이트(앱)에 직접 접속하여 이용하는 경우에만 서비스가 적용됩니다. |  |  | dom-110 | hidden |
| c34 | exception | 가맹점 정보가 해당 업체가 아닌 결제대행업체(PG) 또는 간편결제 전용 가맹점으로 확인되는 경우 ‘결제대행업체’ 또는 ‘간편… |  |  | dom-111 | hidden |
| c35 | exception | 단기카드대출(현금서비스), 장기카드대출(카드론) |  |  | dom-116 | hidden |
| c36 | exception | 연회비, 각종 수수료/이자(할부수수료, 연체이자 등) |  |  | dom-117 | default_visible |
| c37 | exception | 기프트카드/선불카드 구매 · 충전금액 |  |  | dom-118 | hidden |
| c38 | exception | 지방세, 국세, 세외수입(환경개선부담금, 과태료/범칙금/벌금, 여권 발급비용, 우편요금, 국가 공공기관 · 공공단체에서 개설… |  |  | dom-119 | hidden |
| c39 | condition | 전월 이용금액은 ‘신한카드 Hi-Point Plan’의 전월(1일~말일) 거래 시점 이용금액(일시불+할부)을 기준으로 반영됩… |  |  | dom-132 | default_visible |
| c40 | condition | 본인카드와 가족카드의 전월 이용금액 및 월별 적립 한도는 합산 적용됩니다. |  |  | dom-135 | hidden |

| 공백 | 종류 | 상태 | 관련 카드 |
|---|---|---|---|
| gap-4 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-5 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-6 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-7 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-8 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-9 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-10 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-11 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-12 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-13 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-14 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-15 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-16 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-17 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-18 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-19 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-20 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-21 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-22 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-23 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-24 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-25 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-26 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-27 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-28 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-29 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-30 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-31 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-32 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-33 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-34 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-35 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-36 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-37 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-38 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-39 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-40 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-41 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-42 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-43 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-44 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-45 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-46 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-47 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-48 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-49 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-50 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-51 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-52 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-53 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-54 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-55 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-56 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-57 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-58 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-59 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-60 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-61 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-62 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-63 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-64 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-65 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-66 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-67 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-68 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-69 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-70 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-71 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-72 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-73 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-74 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-75 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-76 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-77 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-78 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-79 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-80 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-81 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-82 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-83 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| gap-84 | hidden_text | unresolved | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31, c33, c34, c35, c37, c38, c40 |
| - | claim_without_visible_condition | open | c5, c6, c7, c8, c13, c18, c19, c20, c21, c22, c23, c24, c25, c30 |

## 12. 참고 사례 (판정에 사용하지 않음)

- 아래 사례는 비슷한 표시 유형을 찾아 참고로만 연결한 것입니다. 이 검토의 적합·부적합 판정은 사례와 무관하게 루브릭과 페이지 인용으로만 정해졌습니다.
- 상태: 부분 완료 (사례 연결이 턴 한도 8로 중단되어 그때까지 검증된 연결만 보고함), 후보 15건, 연결 agent(검색 7회, 읽기 5회, 중단 사유 max_turns), 사례 출처 db
- 연결은 agent가 제안하고, 코드가 페이지 인용과 사례 인용을 원문에서 다시 찾아 확인한 것만 남겼습니다.

| 사례 | 카드 | 페이지 인용 | 사례 인용 | 중요한 차이 | 페이지 단독 판단 | 공식 출처 |
|---|---|---|---|---|---|---|
| case.kca_20170930_cardco_homepage_addon_disclosure | c6, c7, c21, c24, c25, c30 | 기본 적립 : 국내/외 이용금액 최대 1.5% 마이신한포인트 적립 | (필요 이용 실적 표시 미흡) 18 개 제휴 신용카드 중 11 개(61.1%)가 할인서비스를 받기 위한 이… | 페이지에는 월 통합 적립 한도(c25), 리필 조건·예외(c8,c32), 서비스 제외 항목(c27~c29,c36~c38) 등 적용 조건이 상세… | full | https://www.kca.go.kr/smartconsumer/sub.do?menukey=7301&mode=view&no=1002635168&page=11&cate=00000057 |
| case.crefia_ad_type_unconditional_discount | c30, c6, c7 | 포인트 리필 서비스는 전월 실적 조건없이 월 1회에 한해 제공됩니다. | 허위·과장 주요 사례 ③ 할인 제외 대상 가맹점이 존재하고 있으나 '무조건 0.7% 할인 되는 카드' 등의… | 사례는 할인 제외 대상 가맹점 존재에도 '무조건' 표현 사용을 문제 삼은 것으로, 본 페이지는 리필 서비스에 대해 '전월 실적 조건없이'라고 … | full | https://customer.crefia.or.kr/common/forward.xx?url=%2Fcustomer%2Freceipt%2FfalseHype%2FfalseHypeCase |
| case.fss_20241007_interest_free_benefit_exclusion | c27, c28, c30, c26 | 해외이용금액의 경우 해외서비스수수료는 적립되지 않습니다. | 또한, 무이자할부를 이용할 경우에는 실적 산정, 포인트·마일리지 적립 및 할인 등이 제외되는 조건의 신용카… | 본 페이지는 해외서비스수수료·할부 전환·현금인출 등 적립 제외 항목(c27~c29,c28)을 명시하고 있어, 사례의 '미안내' 문제와는 차이가… | full | https://www.fss.or.kr/fss/bbs/B0000188/view.do?nttId=187481&menuNo=200218 |

---

이 문서는 자동 검토 결과입니다(ai-generated). 게시 여부의 최종 판단은 컴플라이언스 담당자가 합니다.
