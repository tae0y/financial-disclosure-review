---
ai-generated: true
human-review: false
---

# 금융상품 판매화면 검토 결과

- 판정: **판정 불가**
- 조치 방침: generate_persona_explanation 단계에서 실행이 중단되어(비용 한도 도달) 자동 판정을 내리지 않았습니다.
- 대상 화면: https://www.shinhancard.com/pconts/html/card/apply/credit/2013774_2207.html
- 상품명: 신한카드 Hi-Point Plan
- 상품유형/화면유형: 신용카드 / 상품광고
- 분류 근거: 인용문에 '신용카드 발급'이라는 표현이 포함되어 있어 해당 페이지는 신용카드의 발급·혜택·연회비 등 신용카드 상품 안내임을 직접적으로 보여줍니다.
- 페이지 수집: 조사 불충분 (repeated_action)
- 에이전트 실행: 페이지 탐색 agent 16턴(repeated_action) · 사례 연결 agent 8턴(max_turns) · 독자 선택 실행 안 됨

## 1. 담당자 조치 목록

1. 검토 중단(비용 한도 도달): run budget $0.15 reached ($0.155391) before PersonaUnitDrafts
2. 페이지 수집 조사 불충분(repeated_action): 열린 조사 공백 82건을 사람이 화면에서 확인
3. 한도를 조정해 재실행하거나 사람이 페이지 전체를 직접 검토

## 2. 검토 요약

| 검토 영역 | 검토 항목 | 위반·반려 | 판정 불가·차이 |
|---|---|---|---|
| 표시방법 | 8 | 3 | 4 |
| 설명의무(원문) | 0/0 | 0 | 0 |
| 설명의무(독자 맞춤 설명) | 0/0 | 0 | 0 |
| 독자 맞춤 설명 | 0 | 0 | 0 |

부적합 3건 중 위반 3건, 권고 미충족 0건입니다. 광고 규정과 협회 표시 규정은 공개 상품 페이지(광고)에 직접 적용되어 위반으로 읽고, 설명의무 항목은 계약 권유 단계의 의무를 광고 화면에 준용한 것이어서 권고 미충족으로 읽습니다.

## 3. 확인이 필요한 항목

| 항목 | 대상 | 판정 | 구분 | 사유 | 인용 |
|---|---|---|---|---|---|
| E01 | 판매 화면 표시방법 | 부적합 | 위반(법령) | 혜택 문구(b31, b34, b14 등)는 12–13.5pt(굵은 글씨 포함)로 눈에 띄게 표시된 반면 연회비 등 불이익 관련 문구(b19, b21)는 9–10.5pt로 작게 표기되어 글자 색·크기의 균형을 잃었습니다. | 포인트 적립 서비스 / 포인트 리필 서비스 / 최대 1.5% 적립 / 연회비 / 2만원 (기본) |
| E02 | 판매 화면 표시방법 | 판정 불가 | - | a pass would be unproven: 2 labelled block(s) never visible |  |
| E03 | 판매 화면 표시방법 | 부적합 | 위반(협회 자율규제) | 연체이자율 관련 문구(b61 등)는 굵게(w500) 표시되어 구별되나 일부 경고문구(b66, b67)는 굵기가 기준(300)과 같아 다른 안내문과 구별되지 않습니다. | 연체이자율은 ‘회원별, 이용상품별 약정금리+최대 연 3%, 법정 최고금리(연 20%)이내'에서 적용됩니다. 단, 연체 발생 시점에 약정금리가 … |
| E04 | 판매 화면 표시방법 | 판정 불가 | - | a pass would be unproven: image-backed text without a readable crop: ['b70']; contrast unmeasured: ['b70'] |  |
| E05 | 판매 화면 표시방법 | 판정 불가 | - | a pass would be unproven: 2 labelled block(s) never visible; image-backed text without a readable crop: ['b70', 'b71']; contrast unmeasured: ['b70', 'b71'] |  |
| E06 | 판매 화면 표시방법 | 부적합 | 위반(협회 자율규제) | 의무표시사항 중 b29와 b54가 분리 기호·줄바꿈 없이 이어져 있어 문장마다 기호 또는 줄바꿈으로 구분되어 있지 않습니다. | 유의사항 / 카드사가 부가서비스를 변경하는 경우에는 부가서비스 변경 사유, 변경 내용 등을 사유발생 즉시 아래 고지방법 중 서로 다른 2가지 … |
| E07 | 판매 화면 표시방법 | 판정 불가 | - | 숨김 여부 판정에 필요한 사용자 조작으로 드러난 D 블록 근거가 없으므로 접힌 영역·팝업 등으로 숨겼는지 판단할 수 없습니다. |  |

## 4. 표시방법 검토 상세

| 항목 | 판정 | 근거 블록 | 사유 |
|---|---|---|---|
| E01 | 부적합 | b31, b34, b14, b19, b21 | 혜택 문구(b31, b34, b14 등)는 12–13.5pt(굵은 글씨 포함)로 눈에 띄게 표시된 반면 연회비 등 불이익 관련 문구(b19, b21)는 9–10.5pt로 작게 표기되어 글자 색·크기의 균형을 잃었습니다. |
| E02 | 판정 불가 |  | a pass would be unproven: 2 labelled block(s) never visible |
| E03 | 부적합 | b61, b66, b67 | 연체이자율 관련 문구(b61 등)는 굵게(w500) 표시되어 구별되나 일부 경고문구(b66, b67)는 굵기가 기준(300)과 같아 다른 안내문과 구별되지 않습니다. |
| E04 | 판정 불가 |  | a pass would be unproven: image-backed text without a readable crop: ['b70']; contrast unmeasured: ['b70'] |
| E05 | 판정 불가 |  | a pass would be unproven: 2 labelled block(s) never visible; image-backed text without a readable crop: ['b70', 'b71']; contrast unmeasured: ['b70', 'b71'] |
| E06 | 부적합 | b29, b54 | 의무표시사항 중 b29와 b54가 분리 기호·줄바꿈 없이 이어져 있어 문장마다 기호 또는 줄바꿈으로 구분되어 있지 않습니다. |
| E07 | 판정 불가 |  | 숨김 여부 판정에 필요한 사용자 조작으로 드러난 D 블록 근거가 없으므로 접힌 영역·팝업 등으로 숨겼는지 판단할 수 없습니다. |
| E08 | 적합 | b14, b32, b116 | 최대 수치 표기(b14 등)와 그에 대응하는 적용조건·한도 설명(b32, b116)이 함께 표기되어 있어 짝이 되는 주요 정보가 제공됩니다. |

## 5. 설명의무 검토 상세 (원문 대비 독자 맞춤 설명)

(해당 항목 없음)

- F01–F19·F21·F22는 같은 의무를 담은 설명 코드(설명01–19·27·28)와 한 주제입니다. 표에는 둘 다 남기고, 조치 목록에서는 같은 판정이면 한 번만 셉니다.

## 6. 독자 맞춤 설명 결과

(해당 항목 없음)

## 7. 자동 검증 결과

- 통과: None
- 실패 모듈: 없음
- 검증 루프: None회 (최대 2회)
- 중단 사유: 비용 한도 도달 — run budget $0.15 reached ($0.155391) before PersonaUnitDrafts
- 재시도 이력: 없음


## 8. 비용과 소요시간

아래 수치는 **이 문서를 만든 실행**에서 발생한 것입니다.

- 모델 호출 29회, 입력 427,891 tokens, 출력 24,210 tokens
- 비용 $0.155391 (약 217.5원, 1400.0원/$ 가정)
- 소요시간 331.4초
- 상한: {'max_calls': 60, 'max_usd': 0.15}
- 단계별: discover 16회 $0.0847, case_link 8회 $0.0270, EvidenceCardDrafts 1회 $0.0160, DisplayLabels 1회 $0.0111, DisplayVerdicts 1회 $0.0101, ClassifyAnswer 1회 $0.0060, vision 1회 $0.0004

## 9. 한계와 가정

- 이 검토는 공개된 광고성 화면을 대상으로 하며, 청약 단계 설명화면은 범위에 없습니다. 설명의무 기준은 준용해 품질 기준으로 적용했습니다.
- 자동 검증은 인용 근거의 존재와 모듈 간 모순만 확인합니다. 통과가 법률 준수를 보증하지 않습니다.
- 10 images in the selected html, 7 without alt text; text inside images is not measurable. Flagged by the model: none
- CSS background images and overlapping img bounds flag risky blocks; captured crops are checked by vision for E04/E05. Pseudo-elements and image-only text remain unmeasured.
- 가정: E02 says 8pt on A4. A web page has no paper size, so the node uses computed CSS px x 0.75 >= 8pt at the captured viewport.
- 가정: No threshold in the rubric. The node uses the WCAG 2.1 SC 1.4.3 AA ratio: 4.5:1 for normal text, 3.0:1 for large text (>= 24px, or >= 18.66px and weight >= 700). Text and background colors come from the snapshot (blended background when captured); Image-backed blocks are checked from saved rendered…
- 조사 공백 83건(claim_without_visible_condition, hidden_text, unexpanded_control)은 누락의 증거가 아니라 확인하지 못한 범위입니다.

## 10. 페이지 수집 agent 기록

- 상태: 조사 불충분, 중단 사유: repeated_action
- 조사 범위(전 → 후): {'hidden_text_blocks': 79, 'visible_text_blocks': 86, 'candidate_controls': 3, 'open_gaps': 74} → {'hidden_text_blocks': 89, 'visible_text_blocks': 76, 'candidate_controls': 3, 'open_gaps': 82}
- `조사 불충분`은 누락의 증거가 아닙니다. 보이지 않은 조건은 위반이 아니라 조사 공백으로 남깁니다.

| 공백 | 종류 | 상태 | 내용 | 닫은 행동 |
|---|---|---|---|---|
| gap-1 | unexpanded_control | closed | 주요 혜택 not yet expanded | interact expand a.shc-tab__btn:not(.is-active) (gap gap-2) |
| gap-2 | unexpanded_control | open | 유의사항 not yet expanded |  |
| gap-3 | unexpanded_control | closed | 부가서비스 변경가능 사유 not yet expanded | interact expand #accordion1 (gap gap-3) |
| gap-4 | hidden_text | open | hidden text: '2026.09.29 13:46:22' |  |
| gap-5 | hidden_text | open | hidden text: '주요 혜택 상세 목록' |  |
| gap-6 | hidden_text | open | hidden text: '온라인 신청하기' |  |
| gap-7 | hidden_text | open | hidden text: '2026.01.08 - class삭제 or 수정 내게 맞는 카드 찾기' |  |
| gap-8 | hidden_text | open | hidden text: '2026.01.08 - size-56-> size-28' |  |
| gap-9 | hidden_text | open | hidden text: '포인트 적립 서비스 적립률 및 월 통합 적립 한도' |  |
| gap-10 | hidden_text | open | hidden text: '월 이용금액(일시불+할부), 50만원 미만, 50만원 이상 100만원 미만, 100만원 이상 150만원 미만' |  |
| gap-11 | hidden_text | open | hidden text: '포인트 적립 서비스 적립률 및 월 통합 적립 한도' |  |
| gap-12 | hidden_text | open | hidden text: '전월 이용금액(일시불+할부)' |  |
| gap-13 | hidden_text | open | hidden text: '50만원 이상100만원 미만' |  |
| gap-14 | hidden_text | open | hidden text: '100만원 이상150만원 미만' |  |
| gap-15 | hidden_text | open | hidden text: '150만원 이상' |  |
| gap-16 | hidden_text | open | hidden text: '통합 적립 한도' |  |
| gap-17 | hidden_text | open | hidden text: '특별 적립 영역' |  |
| gap-18 | hidden_text | open | hidden text: '영역, 서비스 대상으로 구성된 표입니다.' |  |
| gap-19 | hidden_text | open | hidden text: '특별 적립 영역 안내' |  |
| gap-20 | hidden_text | open | hidden text: '롯데마트, 이마트' |  |
| gap-21 | hidden_text | open | hidden text: '다이소, 올리브영' |  |
| gap-22 | hidden_text | open | hidden text: 'SK에너지, GS칼텍스' |  |
| gap-23 | hidden_text | open | hidden text: '스타벅스, 이디야, 커피빈, 투썸플레이스, 폴바셋, 메가커피' |  |
| gap-24 | hidden_text | open | hidden text: 'SKT, LG U+, KT 통신요금 자동납부' |  |
| gap-25 | hidden_text | open | hidden text: '기본 적립과 특별 적립을 통합하여 월 5만 포인트 한도까지 적립됩니다.' |  |
| gap-26 | hidden_text | open | hidden text: '기본 적립과 특별 적립은 중복 적용되지 않으며, 특별 적립 영역 가맹점은 기본 적립 대상에서 제외됩니다.' |  |
| gap-27 | hidden_text | open | hidden text: '해외이용금액의 경우 해외서비스수수료는 적립되지 않습니다.' |  |
| gap-28 | hidden_text | open | hidden text: '해외 일시불 거래 후 할부로 전환(유이자 할부 전환 포함)하는 경우는 적립되지 않습니다.' |  |
| gap-29 | hidden_text | open | hidden text: '해외 현금인출 이용금액은 적립되지 않습니다.' |  |
| gap-30 | hidden_text | open | hidden text: '해외 이용 시 별도의 수수료가 부과됩니다. 자세한 내용은 안내장 뒷면 해외이용 확인사항을 확인해주세요.' |  |
| gap-31 | hidden_text | open | hidden text: '특별 적립 영역은 오프라인 매장 이용 시에만 적립되며, 백화점, 할인점, 면세점, 공항 등 입점 매장 이용금' |  |
| gap-32 | hidden_text | open | hidden text: '마트 영역은 대상 가맹점 외 창고형 할인매장(트레이더스 홀세일클럽 등), 기업형 슈퍼마켓(이마트 에브리데이,' |  |
| gap-33 | hidden_text | open | hidden text: '마트 영역은 주차비, 문화센터 및 마트 내 입점된 임대 매장 이용 시에는 적립되지 않습니다.' |  |
| gap-34 | hidden_text | open | hidden text: '주유 영역은 휘발유, 경유, 등유만 적립되며 LPG 이용금액은 적립되지 않습니다.' |  |
| gap-35 | hidden_text | open | hidden text: '카페 영역은 스타벅스 사이렌오더 등 스마트 오더 이용 시에도 적립됩니다.' |  |
| gap-36 | hidden_text | open | hidden text: '해외 스타벅스 가맹점 구매 금액 및 스타벅스 홈페이지/앱 내 선물하기 이용금액은 특별 적립되지 않습니다.' |  |
| gap-37 | hidden_text | open | hidden text: '통신요금 자동납부 금액만 특별 적립되며, 자동납부 외 이용금액 및 알뜰폰 · 선불폰 · 결합상품(TV, 인터' |  |
| gap-38 | hidden_text | open | hidden text: '포인트 리필 서비스는 전월 실적 조건없이 월 1회에 한해 제공됩니다.' |  |
| gap-39 | hidden_text | open | hidden text: '서비스 대상 거래가 발생한 월의 다음달 20일(휴일인 경우, 다음 영업일)에 포인트가 적립됩니다.' |  |
| gap-40 | hidden_text | open | hidden text: '포인트 적립 전 서비스 대상 거래가 부분 또는 전체 취소되어 해당 거래 건의 최종 포인트 사용 금액이 1만원' |  |
| gap-41 | hidden_text | open | hidden text: '신한카드 Hi-Point Plan 서비스 적용 기준' |  |
| gap-42 | hidden_text | open | hidden text: '서비스는 카드 이용 시 제공되는 포인트, 캐시백, 할인 혜택 등을 의미합니다.' |  |
| gap-43 | hidden_text | open | hidden text: '온라인 결제가 제공되는 서비스는 해당 업체 사이트(앱)에 직접 접속하여 이용하는 경우에만 서비스가 적용됩니다' |  |
| gap-44 | hidden_text | open | hidden text: '가맹점 정보가 해당 업체가 아닌 결제대행업체(PG) 또는 간편결제 전용 가맹점으로 확인되는 경우 ‘결제대행업' |  |
| gap-45 | hidden_text | open | hidden text: '서비스가 제공된 결제 건이 취소될 경우, 이미 제공된 서비스 또는 향후 제공될 서비스 금액에서 우선 차감되며' |  |
| gap-46 | hidden_text | open | hidden text: '서비스가 적용된 거래가 해당월에 취소된 경우 서비스 횟수 및 한도가 복원됩니다.' |  |
| gap-47 | hidden_text | open | hidden text: '서비스 제외 대상은 아래와 같습니다.' |  |
| gap-48 | hidden_text | open | hidden text: '단기카드대출(현금서비스), 장기카드대출(카드론)' |  |
| gap-49 | hidden_text | open | hidden text: '연회비, 각종 수수료/이자(할부수수료, 연체이자 등)' |  |
| gap-50 | hidden_text | open | hidden text: '기프트카드/선불카드 구매 · 충전금액' |  |
| gap-51 | hidden_text | open | hidden text: '지방세, 국세, 세외수입(환경개선부담금, 과태료/범칙금/벌금, 여권 발급비용, 우편요금, 국가 공공기관 · ' |  |
| gap-52 | hidden_text | open | hidden text: '4대보험(국민연금, 고용보험, 건강보험, 산재보험)' |  |
| gap-53 | hidden_text | open | hidden text: '유치원/초중고 납입금(스쿨뱅킹), 대학(원)등록금' |  |
| gap-54 | hidden_text | open | hidden text: '아파트관리비, 도시가스, 전기요금, TV수신료, 수도요금' |  |
| gap-55 | hidden_text | open | hidden text: '포인트 사용거래 중 포인트금액' |  |
| gap-56 | hidden_text | open | hidden text: '무이자할부(슬림할부 등 부분 무이자 포함) 이용거래' |  |
| gap-57 | hidden_text | open | hidden text: '상품권/선불전자지급수단 구매 · 충전금액' |  |
| gap-58 | hidden_text | open | hidden text: '포인트/캐시/사이버머니/예치금 등 전자지급(결제)수단 구매 · 충전금액' |  |
| gap-59 | hidden_text | open | hidden text: '신한카드 Hi-Point Plan 서비스 이외의 프로모션 할인이 적용된 거래' |  |
| gap-60 | hidden_text | open | hidden text: '의약품 전용몰(도매몰), 제약회사 업종 이용금액' |  |
| gap-61 | hidden_text | open | hidden text: '신차판매 업종 이용금액' |  |
| gap-62 | hidden_text | open | hidden text: '전월 이용금액 기준' |  |
| gap-63 | hidden_text | open | hidden text: '전월 이용금액은 ‘신한카드 Hi-Point Plan’의 전월(1일~말일) 거래 시점 이용금액(일시불+할부)을' |  |
| gap-64 | hidden_text | open | hidden text: '해외 이용금액은 매입일자를 기준으로 반영됩니다.' |  |
| gap-65 | hidden_text | open | hidden text: '교통카드 이용금액은 전전월 이용금액이 전월 이용금액에 반영됩니다.(단, 모바일 후불 교통카드 이용금액은 전월' |  |
| gap-66 | hidden_text | open | hidden text: '본인카드와 가족카드의 전월 이용금액 및 월별 적립 한도는 합산 적용됩니다.' |  |
| gap-67 | hidden_text | open | hidden text: '거래 후 취소금액은 국내 거래의 경우 최초 승인된 달의 이용금액에서, 해외 거래의 경우 취소 전표가 매입된 ' |  |
| gap-68 | hidden_text | open | hidden text: '서비스가 제공된 이후 결제 취소 등의 사유로 서비스 제공 조건을 미충족하게 되는 경우, 서비스 차액이 청구되' |  |
| gap-69 | hidden_text | open | hidden text: '신한카드 Hi-Point Plan 최초 신규 발급 회원*은 카드 사용 등록한 월(간편결제 등록 포함)의 다음' |  |
| gap-70 | hidden_text | open | hidden text: '전월 이용금액 제외 대상은 아래와 같습니다.' |  |
| gap-71 | hidden_text | open | hidden text: '상품권/선불전자지급수단 구매 · 충전금액' |  |
| gap-72 | hidden_text | open | hidden text: '포인트/캐시/사이버머니/예치금 등 전자지급(결제)수단 구매 · 충전금액' |  |
| gap-73 | hidden_text | open | hidden text: '의약품 전용몰(도매몰), 제약회사 업종 이용금액' |  |
| gap-74 | hidden_text | open | hidden text: '신차판매 업종 이용금액' |  |
| gap-75 | hidden_text | open | hidden text: '카드 이용 시 제공되는 포인트 및 할인 혜택 등의 부가서비스는 카드 신규출시(2026.06.09) 이후 3년' |  |
| gap-76 | hidden_text | open | hidden text: '상기에도 불구하고, 다음과 같은 사유가 발생한 경우 카드사는 부가서비스를 변경할 수 있습니다.' |  |
| gap-77 | hidden_text | open | hidden text: '2026.05.14 문구 수정' |  |
| gap-78 | hidden_text | open | hidden text: '카드사의 휴업·파산·경영상의 위기 등에 따른 불가피한 경우' |  |
| gap-79 | hidden_text | open | hidden text: '제휴업체의 휴업·파산·경영상의 위기로 인해 불가피하게 부가서비스를 축소·변경하는 경우로서 다른 제휴업체를 통' |  |
| gap-80 | hidden_text | open | hidden text: '제휴업체가 카드사의 의사에 반하여 해당 부가서비스를 축소하거나 변경 시, 당초 부가서비스에 상응하는 다른 부' |  |
| gap-81 | hidden_text | open | hidden text: '부가서비스를 3년 이상 제공한 상태에서 해당 부가서비스로 인해 카드의 수익성이 현저히 낮아진 경우' |  |
| gap-82 | hidden_text | open | hidden text: '카드사가 부가서비스를 변경하는 경우에는 부가서비스 변경 사유, 변경 내용 등을 사유발생 즉시 아래 고지방법 ' |  |
| gap-83 | hidden_text | open | hidden text: '2026.05.14 문구 수정' |  |
| gap-84 | hidden_text | open | hidden text: '고지 방법: 서면 교부, 우편 또는 전자우편, 전화 또는 팩스, 휴대폰 메시지 또는 이에 준하는 전자적 의사' |  |

| 턴 | 도구 | 인자 | 대상 공백 | 결과 |
|---|---|---|---|---|
| 1 | inspect_page | {} |  | - |
| 2 | interact | {"action": "expand", "selector": "a.shc-tab__btn:not(.is-active)", "g… | gap-2 | - |
| 3 | interact | {"action": "expand", "selector": "#accordion1", "gap_id": "gap-3", "e… | gap-3 | 새 증거 |
| 4 | inspect_page | {} |  | - |
| 5 | submit_rule | {"product_name": "신한카드 Hi-Point Plan", "summary": "Selectors that cap… |  | - |
| 6 | probe_selector | {"selectors": ["main h1", "h1", "header h1", ".print-content__date", … |  | - |
| 7 | submit_rule | {"product_name": "신한카드 Hi-Point Plan", "summary": "CSS selectors capt… |  | - |
| 8 | submit_rule | {"product_name": "신한카드 Hi-Point Plan", "summary": "CSS selectors capt… |  | - |
| 9 | interact | {"action": "expand", "selector": "a.shc-tab__btn:not(.is-active)", "g… | gap-2 | 거부: repeated expand 'a.shc-tab__btn:not(.is-active)' … |
| 10 | submit_rule | {"product_name": "신한카드 Hi-Point Plan", "summary": "Selectors that cap… |  | - |
| 12 | interact | {"action": "expand", "selector": "a.shc-tab__btn", "gap_id": "gap-2",… | gap-2 | 거부: exploration closed: repeated_action; submit_rule … |
| 13 | inspect_page | {} |  | - |
| 14 | submit_rule | {"product_name": "신한카드 Hi-Point Plan", "summary": "CSS selectors capt… |  | - |
| 15 | probe_selector | {"selectors": ["h2.sr-only:nth-of-type(3)", "h2.sr-only:last-of-type"… |  | - |
| 16 | submit_rule | {"product_name": "신한카드 Hi-Point Plan", "summary": "CSS selectors capt… |  | - |

## 11. 증거 카드와 조사 공백

- 상태: 완료, 카드 33건, 검증 탈락 0건
- 카드는 원문 인용과 출처(`dom-N`)가 코드로 재확인된 사실 단위이며, 법률 판단이 아닙니다.

| 카드 | 종류 | 인용 | 조건 | 예외 | 출처 | 가시성 |
|---|---|---|---|---|---|---|
| c1 | footnote | 신한카드 Hi-Point Plan |  |  | dom-0 | default_visible |
| c2 | footnote | 쓰는 만큼 쌓이고, 필요할 땐 채워지고 |  |  | dom-1 | default_visible |
| c3 | benefit_claim | 국내/외 가맹점 최대 1.5% 적립 |  |  | dom-2 | default_visible |
| c4 | benefit_claim | 생활밀착 최대5%적립 월 최대 5만 포인트 |  |  | dom-3 | default_visible |
| c5 | fee_claim | 국내전용 2만원 (기본) |  |  | dom-6 | default_visible |
| c6 | fee_claim | Mastercard 2만3천원 (기본) |  |  | dom-7 | default_visible |
| c7 | fee_claim | Visa 2만3천원 (기본) |  |  | dom-8 | default_visible |
| c8 | benefit_claim | 신규 고객 전용 이벤트 연회비 100% 캐시백 |  |  | dom-9 | default_visible |
| c9 | benefit_claim | 기본 적립 : 국내/외 이용금액 최대 1.5% 마이신한포인트 적립 |  |  | dom-13 | default_visible |
| c10 | benefit_claim | 특별 적립 : 생활 밀착 가맹점 최대 5% 마이신한포인트 적립 |  |  | dom-14 | default_visible |
| c11 | benefit_claim | 마이신한포인트 1만 포인트 이상 사용 결제 시 1천 포인트 리필 적립(월 1회) |  |  | dom-16 | default_visible |
| c12 | fee_claim | 가족카드는 연회비가 없습니다.(단, 가족카드 단독으로 발급받을 경우 연회비가 부과됩니다.) |  | (단, 가족카드 단독으로 발급받을 경우 연회비가 부과됩니다.) | dom-22 | default_visible |
| c13 | eligibility | 후불교통 기능이 있는 카드로만 신청 가능합니다. |  |  | dom-23 | default_visible |
| c14 | eligibility | 신한카드 Hi-Point Plan은 1인 2장 이상 중복 발급 및 소지가 불가합니다.(제휴상품 포함) |  |  | dom-24 | default_visible |
| c15 | benefit_claim | 해외겸용(Mastercard, VISA)은 컨택리스 결제를 지원합니다. |  |  | dom-25 | default_visible |
| c16 | condition | 카드 이용 시 제공되는 포인트 및 할인 혜택 등의 부가서비스는 카드 신규출시(2026.06.09) 이후 3년 이상 축소·폐지… |  |  | dom-28 | default_visible |
| c17 | footnote | 카드 출시 일자: 2026.06.09 |  |  | dom-38 | default_visible |
| c18 | benefit_claim | 기본 적립과 특별 적립을 통합하여 월 5만 포인트 한도까지 적립됩니다. |  |  | dom-92 | hidden |
| c19 | exception | 기본 적립과 특별 적립은 중복 적용되지 않으며, 특별 적립 영역 가맹점은 기본 적립 대상에서 제외됩니다. |  | 특별 적립 영역 가맹점은 기본 적립 대상에서 제외됩니다. | dom-93 | hidden |
| c20 | exception | 해외이용금액의 경우 해외서비스수수료는 적립되지 않습니다. |  |  | dom-94 | hidden |
| c21 | exception | 해외 일시불 거래 후 할부로 전환(유이자 할부 전환 포함)하는 경우는 적립되지 않습니다. | (유이자 할부 전환 포함) |  | dom-95 | hidden |
| c22 | exception | 해외 현금인출 이용금액은 적립되지 않습니다. |  |  | dom-96 | hidden |
| c23 | condition | 특별 적립 영역은 오프라인 매장 이용 시에만 적립되며, 백화점, 할인점, 면세점, 공항 등 입점 매장 이용금액은 적립되지 않… | 오프라인 매장 이용 시에만 적립되며 | 백화점, 할인점, 면세점, 공항 등 입점 매장 이용금액은 적립되지 않습… | dom-98 | hidden |
| c24 | exception | 마트 영역은 대상 가맹점 외 창고형 할인매장(트레이더스 홀세일클럽 등), 기업형 슈퍼마켓(이마트 에브리데이, 롯데슈퍼 등) … |  |  | dom-99 | hidden |
| c25 | exception | 마트 영역은 주차비, 문화센터 및 마트 내 입점된 임대 매장 이용 시에는 적립되지 않습니다. |  |  | dom-100 | hidden |
| c26 | exception | 주유 영역은 휘발유, 경유, 등유만 적립되며 LPG 이용금액은 적립되지 않습니다. |  | LPG 이용금액은 적립되지 않습니다. | dom-101 | hidden |
| c27 | benefit_claim | 카페 영역은 스타벅스 사이렌오더 등 스마트 오더 이용 시에도 적립됩니다. |  |  | dom-102 | hidden |
| c28 | exception | 해외 스타벅스 가맹점 구매 금액 및 스타벅스 홈페이지/앱 내 선물하기 이용금액은 특별 적립되지 않습니다. |  |  | dom-103 | hidden |
| c29 | condition | 통신요금 자동납부 금액만 특별 적립되며, 자동납부 외 이용금액 및 알뜰폰 · 선불폰 · 결합상품(TV, 인터넷, 유선전화 등… | 통신요금 자동납부 금액만 특별 적립되며 | 자동납부 외 이용금액 및 알뜰폰 · 선불폰 · 결합상품(TV, 인터넷,… | dom-104 | hidden |
| c30 | condition | 포인트 리필 서비스는 전월 실적 조건없이 월 1회에 한해 제공됩니다. | 전월 실적 조건없이 |  | dom-105 | default_visible |
| c31 | condition | 서비스 대상 거래가 발생한 월의 다음달 20일(휴일인 경우, 다음 영업일)에 포인트가 적립됩니다. | (휴일인 경우, 다음 영업일) |  | dom-106 | hidden |
| c32 | condition | 전월 이용금액은 ‘신한카드 Hi-Point Plan’의 전월(1일~말일) 거래 시점 이용금액(일시불+할부)을 기준으로 반영됩… | (1일~말일) |  | dom-132 | default_visible |
| c33 | condition | 신한카드 Hi-Point Plan 최초 신규 발급 회원*은 카드 사용 등록한 월(간편결제 등록 포함)의 다음달(등록월+1개월… | (간편결제 등록 포함) | 단, 해당 기간에 100만원 이상 이용할 경우 그 구간에 맞는 서비스가… | dom-139 | default_visible |

| 공백 | 종류 | 상태 | 관련 카드 |
|---|---|---|---|
| gap-2 | unexpanded_control | open |  |
| gap-4 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-5 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-6 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-7 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-8 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-9 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-10 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-11 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-12 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-13 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-14 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-15 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-16 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-17 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-18 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-19 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-20 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-21 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-22 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-23 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-24 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-25 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-26 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-27 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-28 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-29 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-30 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-31 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-32 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-33 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-34 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-35 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-36 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-37 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-38 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-39 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-40 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-41 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-42 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-43 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-44 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-45 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-46 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-47 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-48 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-49 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-50 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-51 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-52 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-53 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-54 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-55 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-56 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-57 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-58 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-59 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-60 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-61 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-62 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-63 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-64 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-65 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-66 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-67 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-68 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-69 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-70 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-71 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-72 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-73 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-74 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-75 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-76 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-77 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-78 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-79 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-80 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-81 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-82 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-83 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| gap-84 | hidden_text | open | c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c31 |
| - | claim_without_visible_condition | open | c3, c4, c8, c9, c10, c11, c15, c18, c27 |

## 12. 참고 사례 (판정에 사용하지 않음)

- 아래 사례는 비슷한 표시 유형을 찾아 참고로만 연결한 것입니다. 이 검토의 적합·부적합 판정은 사례와 무관하게 루브릭과 페이지 인용으로만 정해졌습니다.
- 상태: 부분 완료 (사례 연결이 턴 한도 8로 중단되어 그때까지 검증된 연결만 보고함), 후보 13건, 연결 agent(검색 7회, 읽기 5회, 중단 사유 max_turns), 사례 출처 db
- 연결은 agent가 제안하고, 코드가 페이지 인용과 사례 인용을 원문에서 다시 찾아 확인한 것만 남겼습니다.

| 사례 | 카드 | 페이지 인용 | 사례 인용 | 중요한 차이 | 페이지 단독 판단 | 공식 출처 |
|---|---|---|---|---|---|---|
| case.fss_20241007_addon_limit_restore | c4, c18 | 생활밀착 최대5%적립 월 최대 5만 포인트 | (예) 결제금액의 5% 포인트 적립(月 결제금액 20만원까지) → 월별 제공한도 10,000원. | 사례는 결제취소·한도복원 시 적립 누락 등 운영상 미이행을 지적함; 본 페이지는 혜택과 월한도를 안내하고 있으나 결제취소 처리나 한도 복원 시… | partial — 페이지 단독 판단 불가 | https://www.fss.or.kr/fss/bbs/B0000188/view.do?nttId=187481&menuNo=200218 |
| case.crefia_ad_type_unconditional_discount | c10, c23 | 특별 적립 : 생활 밀착 가맹점 최대 5% 마이신한포인트 적립 | 허위·과장 주요 사례 ③ 할인 제외 대상 가맹점이 존재하고 있으나 '무조건 0.7% 할인 되는 카드' 등의… | 협회 사례는 '무조건 할인' 등 절대적 표현을 문제 삼음; 본 페이지는 '최대 5% 적립'이라 표현하여 절대적 무조건 표현은 아님.; 페이지는… | full | https://customer.crefia.or.kr/common/forward.xx?url=%2Fcustomer%2Freceipt%2FfalseHype%2FfalseHypeCase |
| case.fss_20241007_interest_free_benefit_exclusion | c21, c22, c20 | 해외 일시불 거래 후 할부로 전환(유이자 할부 전환 포함)하는 경우는 적립되지 않습니다. | 또한, 무이자할부를 이용할 경우에는 실적 산정, 포인트·마일리지 적립 및 할인 등이 제외되는 조건의 신용카… | 사례는 미안내로 인한 소비자 오인 문제를 지적; 본 페이지는 적립 제외 조항을 명시하고 있어 안내는 되어 있음.; page_only_detec… | full | https://www.fss.or.kr/fss/bbs/B0000188/view.do?nttId=187481&menuNo=200218 |

---

이 문서는 자동 검토 결과입니다(ai-generated). 게시 여부의 최종 판단은 컴플라이언스 담당자가 합니다.
