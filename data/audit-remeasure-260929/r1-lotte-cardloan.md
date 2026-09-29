---
ai-generated: true
human-review: false
---

# 금융상품 판매화면 검토 결과

- 판정: **판정 불가**
- 조치 방침: judge_explanation_duty 단계에서 실행이 중단되어(비용 한도 도달) 자동 판정을 내리지 않았습니다.
- 대상 화면: https://www.lottecard.co.kr/app/LPFINFA_V100.lc
- 상품명: 신차일시불(캐시백)
- 상품유형/화면유형: 신용카드 / 상품광고
- 분류 근거: 해당 인용문은 차량 대금을 '롯데카드 일시불 결제'할 때 제공되는 캐시백 혜택을 설명하고 있어, 신용카드의 일시불 결제 관련 혜택을 안내하는 페이지임을 보여줍니다.
- 페이지 수집: 조사 불충분 (submitted_with_gaps)
- 에이전트 실행: 페이지 탐색 agent 9턴(submitted_with_gaps) · 사례 연결 agent 8턴(max_turns) · 독자 선택 상품유형 기본 조건

## 1. 담당자 조치 목록

1. 검토 중단(비용 한도 도달): run budget $0.15 reached ($0.157917) before FidelityDiffs
2. 페이지 수집 조사 불충분(submitted_with_gaps): 열린 조사 공백 112건을 사람이 화면에서 확인
3. 한도를 조정해 재실행하거나 사람이 페이지 전체를 직접 검토

## 2. 검토 요약

| 검토 영역 | 검토 항목 | 위반·반려 | 판정 불가·차이 |
|---|---|---|---|
| 표시방법 | 8 | 1 | 2 |
| 설명의무(원문) | 0/0 | 0 | 0 |
| 설명의무(독자 맞춤 설명) | 0/0 | 0 | 0 |
| 독자 맞춤 설명 | 29 | 0 | 0 |

부적합 1건 중 위반 1건, 권고 미충족 0건입니다. 광고 규정과 협회 표시 규정은 공개 상품 페이지(광고)에 직접 적용되어 위반으로 읽고, 설명의무 항목은 계약 권유 단계의 의무를 광고 화면에 준용한 것이어서 권고 미충족으로 읽습니다.

## 3. 확인이 필요한 항목

| 항목 | 대상 | 판정 | 구분 | 사유 | 인용 |
|---|---|---|---|---|---|
| E05 | 판매 화면 표시방법 | 판정 불가 | - | a pass would be unproven: image-backed text without a readable crop: ['b20']; contrast unmeasured: ['b20'] |  |
| E07 | 판매 화면 표시방법 | 부적합 | 위반(협회 자율규제) | 여러 의무표시사항(예: b60~b67 등)이 접힌 영역/숨김 상태로 캡처되었고 measures의 revealed_by_action에 사용자 확장으로 나타난 항목들이 있어 페이지에서 쉽게 확인할 수 없게 숨겨두었습니다. | 부여된 오토구매한도 내에서 오토캐시백과 오토할부를 각각 이용할 수 있습니다. / 오토캐시백과 오토할부 동시 이용을 원하실 경우, 롯데카드 오토… |
| E08 | 판매 화면 표시방법 | 판정 불가 | - | 요율(최저/최고)과 짝이 되는 주요 정보(최고금리·조건 등)의 병기 여부를 확인할 수 있는 근거가 measures나 blocks에 없어 판단할 수 없습니다. |  |

## 4. 표시방법 검토 상세

| 항목 | 판정 | 근거 블록 | 사유 |
|---|---|---|---|
| E01 | 적합 | b22, b23, b33, b76, b77, b53, b54 | 혜택 문구는 최대 30.0pt(예: b22)·큰 제목(예: b23, b33) 등으로 표시되고 불이익·유의사항은 최대 13.5pt 수준(예: b76, b77, b53, b54)으로 측정되어 글자 크기·대비에서 혜택이 더 크게 표시되어 균형을 잃지 않았습니다. |
| E02 | 적합 | b50 | all 14 labelled block(s) measured within the threshold (min 11.25pt) |
| E03 | 적합 | b76, b77, b78, b79, b80, b82, b83, b84 | 연체이자율 및 경고문구들은 굵은 서체(w600, 예: b76~b80) 또는 배경음영(예: b82~b84)으로 다른 안내문과 구별되어 있습니다. |
| E04 | 적합 | b65 | all 6 labelled block(s) measured within the threshold (min contrast 8.59) |
| E05 | 판정 불가 |  | a pass would be unproven: image-backed text without a readable crop: ['b20']; contrast unmeasured: ['b20'] |
| E06 | 적합 | b61, b64, b65, b71, b73, b74, b75, b76, b82, b83, b84 | 측정된 의무표시문은 기호는 없으나 모두 줄바꿈으로 문장마다 분리되어 있어(단일 문단에 이어 붙여 있지 않음) 문장마다 줄바꿈으로 구분되어 있습니다. |
| E07 | 부적합 | b60, b61, b62, b63, b64, b65, b66, b67 | 여러 의무표시사항(예: b60~b67 등)이 접힌 영역/숨김 상태로 캡처되었고 measures의 revealed_by_action에 사용자 확장으로 나타난 항목들이 있어 페이지에서 쉽게 확인할 수 없게 숨겨두었습니다. |
| E08 | 판정 불가 |  | 요율(최저/최고)과 짝이 되는 주요 정보(최고금리·조건 등)의 병기 여부를 확인할 수 있는 근거가 measures나 blocks에 없어 판단할 수 없습니다. |

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
| u1 | dom-1 | 새 차 살 때, 롯데카드 결제하면, 캐시백 혜택 | 새 차를 살 때 롯데카드로 결제하면 캐시백을 받을 수 있다는 안내입니다. 단, 아래 조건들을 지켜야 합니다. | - | accepted |
| u2 | dom-2 | 오토캐시백 프로모션 사전신청 후, 본인명의 롯데카드 일시불 결제 | 먼저 오토캐시백 프로모션에 사전신청을 해야 합니다. 그다음 본인 명의 롯데카드로 일시불로 결제해야 혜택 대상입니다. | - | accepted |
| u3 | dom-3 | 캐시백최대1.4% | 받을 수 있는 캐시백은 문구대로 '캐시백최대1.4%'입니다. 구체적인 비율은 아래 항목들을 보세요. | 받는 돈은 서랍에 넣어 두었다가 나중에 꺼내는 '작은 돌려받음' 같은 … | accepted |
| u4 | dom-32 | 5천만원 이상 : 1.4% | 구매 금액이 5천만원 이상인 경우 표기대로 '5천만원 이상 : 1.4%'가 적용됩니다. | 캐시백 비율은 사고 난 금액표에 적힌 숫자와 같습니다. 표시된 대로만 … | accepted |
| u5 | dom-33 | 4천만원 이상 : 1.4% | 구매 금액이 4천만원 이상인 경우 표기대로 '4천만원 이상 : 1.4%'가 적용됩니다. | 캐시백 비율은 사고 난 금액표에 적힌 숫자와 같습니다. 표시된 대로만 … | accepted |
| u6 | dom-34 | 3천만원 이상 : 1.4% | 구매 금액이 3천만원 이상인 경우 표기대로 '3천만원 이상 : 1.4%'가 적용됩니다. | 캐시백 비율은 사고 난 금액표에 적힌 숫자와 같습니다. 표시된 대로만 … | accepted |
| u7 | dom-35 | 2천만원 이상 : 1.4% | 구매 금액이 2천만원 이상인 경우 표기대로 '2천만원 이상 : 1.4%'가 적용됩니다. | 캐시백 비율은 사고 난 금액표에 적힌 숫자와 같습니다. 표시된 대로만 … | accepted |
| u8 | dom-36 | 1천만원 이상 : 1.4% | 구매 금액이 1천만원 이상인 경우 표기대로 '1천만원 이상 : 1.4%'가 적용됩니다. | 캐시백 비율은 사고 난 금액표에 적힌 숫자와 같습니다. 표시된 대로만 … | accepted |
| u9 | dom-37 | 1천만원 미만 : 1.4% | 구매 금액이 1천만원 미만인 경우에도 '1천만원 미만 : 1.4%'가 적용된다고 적혀 있습니다. | 어떤 금액대든 표에 적힌 비율을 따라갑니다. | accepted |
| u10 | dom-38 | 체크카드로 결제 시 구매금액 관계없이 0.5% 캐시백이 제공됩니다. | 체크카드로 결제하면 '구매금액 관계없이' 0.5% 캐시백이 제공됩니다. 즉 금액과 상관없이 0.5%가 적용된다고 적혀 있습니다. | 어떤 물건을 사도 일정한 비율을 돌려받는 우편엽서 같은 느낌입니다. | accepted |
| u11 | dom-42 | 전액기존한도/부분선입금 : 청구서 결제일(상환완료) + 7일 이내(전표접수, 휴무일에 따라 변경가능) | 신용카드로 전액 기존한도 또는 부분 선입금한 경우 캐시백은 '청구서 결제일(상환완료) + 7일 이내'에 지급됩니다. 다만 전표 접수나 휴무일에 따라 달라질 수 … | - | accepted |
| u12 | dom-43 | 전액선입금 : 승인전표매입(상환완료) + 7일 이내 | 카드값을 전액 선입금한 경우에는 '승인전표매입(상환완료) + 7일 이내'에 캐시백이 지급된다고 적혀 있습니다. | - | accepted |
| u13 | dom-47 | 승인전표매입 + 6일 이내 캐시백 지급(전표접수, 휴무일에 따라 변경가능) | 체크카드로 결제한 경우 캐시백은 '승인전표매입 + 6일 이내'에 지급됩니다. 전표 접수나 휴무일에 따라 달라질 수 있습니다. | - | accepted |
| u14 | dom-49 | 전담상담센터를 통해 오토구매한도를 부여받은 후, 오토캐시백을 신청하시기 바랍니다. | 오토캐시백을 신청하려면 먼저 전담상담센터에서 '오토구매한도'를 받아야 한다고 적혀 있습니다. 이 절차를 거친 뒤 신청해야 합니다. | - | accepted |
| u15 | dom-50 | 오토캐시백 신청되지 않은 차량구매 건은 캐시백이 제공되지 않습니다. | 오토캐시백을 따로 '신청하지 않은' 차량 구매는 캐시백 대상이 아닙니다. 신청을 안 하면 혜택이 나오지 않습니다. | - | accepted |
| u16 | dom-53 | 오토캐시백 신청 후 신청금액 이하로 처음 결제되는 일시불 금액 기준으로 오토캐시백이 적용됩니다.(이후 결제 건은 오토캐시백이… | 오토캐시백은 '신청한 금액 이하로 처음 결제되는 일시불 금액'에만 적용된다고 적혀 있습니다. 그 뒤에 추가로 결제한 건에는 오토캐시백이 적용되지 않습니다. | - | accepted |
| u17 | dom-54 | 법인, 가족회원은 제외되며, 롯데카드 심사 자격기준에 의해 이용이 제한될 수 있습니다. | 서비스 대상에서 '법인'과 '가족회원'은 제외된다고 적혀 있습니다. 또한 롯데카드의 심사 기준에 따라 이용이 제한될 수 있다고 안내되어 있습니다. | - | accepted |
| u18 | dom-55 | 롯데카드에 국산차 또는 수입차 가맹점으로 등록되어 있는 곳에서 결제하는 경우에만 오토캐시백이 제공됩니다. | 오토캐시백은 '롯데카드에 국산차 또는 수입차 가맹점으로 등록된 곳'에서 결제해야만 적용됩니다. 등록되지 않은 곳에서는 해당되지 않습니다. | - | accepted |
| u19 | dom-56 | 차량구매대금이 청구되는 달의 결제금액이 연체될 경우, 캐시백을 지급하지 않습니다.(연체일수 금액무관) | 만약 차량 구매대금이 청구되는 달에 결제금액이 연체되면, 캐시백을 지급하지 않는다고 적혀 있습니다. '(연체일수 금액무관)'이라는 문구도 포함되어 있습니다. | - | accepted |
| u20 | dom-57 | 대금결제일 이전에 선입금해도 원 대금결제월을 기준으로 캐시백을 지급합니다. | 대금을 결제일 이전에 미리 낸다고 해도, 캐시백은 원래의 '대금결제월'을 기준으로 지급한다고 적혀 있습니다. 미리 내도 지급 기준 달이 바뀌지 않습니다. | - | accepted |
| u21 | dom-59 | 매출취소 시, 이미 지급된 캐시백 금액은 현금으로 청구됩니다.(체크카드는 이미 지급된 캐시백 금액 차감 후 환불) | 결제가 취소되면 이미 받은 캐시백은 다시 청구됩니다. 체크카드는 이미 받은 캐시백을 차감한 뒤 환불한다고 적혀 있습니다. 취소 시 돈이 다시 나올 수 있습니다. | - | accepted |
| u22 | dom-60 | 오토캐시백과 오토할부, 오토세이브, 선포인트 등을 함께 이용할 경우, 이용금액별로 각각 결제해야 합니다. | 오토캐시백을 다른 서비스(오토할부, 오토세이브, 선포인트 등)와 함께 쓰면, 각각의 이용금액을 따로따로 결제해야 한다고 적혀 있습니다. | - | accepted |
| u23 | dom-61 | 법인, 선불, 기프트, 가족카드는 서비스 이용대상에서 제외됩니다. | 법인카드, 선불카드, 기프트카드, 가족카드는 이 서비스 대상에서 제외된다고 분명히 적혀 있습니다. | - | accepted |
| u24 | dom-62 | 오토캐시백 이용금액은 각종 포인트.마일리지 적립, 할인, 세이브.선포인트.일부결제금액이월약정 서비스에 적용되지 않습니다. | 오토캐시백으로 인정되는 이용금액은 포인트·마일리지 적립이나 할인, 세이브·선포인트, 일부결제금액이월약정 등 다른 적립이나 할인 서비스에 적용되지 않는다고 적혀 … | - | accepted |
| u25 | dom-68 | 연체이자율 : 회원별, 이용상품별 약정이율 + 최대3%, 법정 최고금리(연 20%) 이내 | 연체가 생기면 적용되는 이자율은 '회원별·상품별 약정이율에 최대3%를 더한 범위'이며, 법정 최고금리인 '연 20%' 이내라고 적혀 있습니다. | - | accepted |
| u26 | dom-70 | 일시불 거래 연체 시 : 거래 발생 시점의 최소기간(2개월)유이자 할부 금리 | 일시불 거래를 연체하면 적용되는 이율은 '거래가 발생한 시점의 최소기간(2개월) 유이자 할부 금리'라고 적혀 있습니다. | - | accepted |
| u27 | dom-74 | 상환능력에 비해 신용카드 사용액이 과도할 경우 귀하의 개인 신용평점이 하락할 수 있습니다. | 카드 사용액이 갚을 능력보다 많으면 '개인 신용평점이 하락할 수 있다'고 경고하고 있습니다. 많이 쓰면 신용등급에 나쁜 영향이 날 수 있습니다. | - | accepted |
| u28 | dom-75 | 개인 신용평점 하락 시 금융거래 관련된 불이익이 발생할 수 있습니다. | 신용평점이 내려가면 은행 거래 등에서 불이익이 생길 수 있다고 적혀 있습니다. 신용이 중요하다는 경고입니다. | - | accepted |
| u29 | dom-76 | 일정기간 원리금을 연체할 경우, 모든 원리금을 변제할 의무가 발생할 수 있습니다. | 만약 일정 기간 동안 원리금을 갚지 않으면 '모든 원리금을 변제할 의무가 발생할 수 있다'고 적혀 있습니다. 연체가 길어지면 큰 의무가 생길 수 있습니다. | - | accepted |

### 운영 통제 (판정 대상 아님)

- 화면: AI 생성 고지, 원문 보기 전환, 오류 신고
- 거버넌스: 사람 승인, 변경 관리, 프로필 검토

## 7. 자동 검증 결과

- 통과: None
- 실패 모듈: 없음
- 검증 루프: None회 (최대 2회)
- 중단 사유: 비용 한도 도달 — run budget $0.15 reached ($0.157917) before FidelityDiffs
- 재시도 이력: 없음


## 8. 비용과 소요시간

아래 수치는 **이 문서를 만든 실행**에서 발생한 것입니다.

- 모델 호출 25회, 입력 241,429 tokens, 출력 48,780 tokens
- 비용 $0.157917 (약 221.1원, 1400.0원/$ 가정)
- 소요시간 564.2초
- 상한: {'max_calls': 60, 'max_usd': 0.15}
- 단계별: ExplanationJudgments 2회 $0.0344, discover 9회 $0.0326, case_link 8회 $0.0261, EvidenceCardDrafts 1회 $0.0166, PersonaUnitDrafts 1회 $0.0146, DisplayLabels 1회 $0.0097, DisplayVerdicts 1회 $0.0089, PlainJudgments 1회 $0.0085, ClassifyAnswer 1회 $0.0065

## 9. 한계와 가정

- 이 검토는 공개된 광고성 화면을 대상으로 하며, 청약 단계 설명화면은 범위에 없습니다. 설명의무 기준은 준용해 품질 기준으로 적용했습니다.
- 자동 검증은 인용 근거의 존재와 모듈 간 모순만 확인합니다. 통과가 법률 준수를 보증하지 않습니다.
- 0 images in the selected html, 0 without alt text; text inside images is not measurable. Flagged by the model: none
- CSS background images and overlapping img bounds flag risky blocks; captured crops are checked by vision for E04/E05. Pseudo-elements and image-only text remain unmeasured.
- 가정: E02 says 8pt on A4. A web page has no paper size, so the node uses computed CSS px x 0.75 >= 8pt at the captured viewport.
- 가정: No threshold in the rubric. The node uses the WCAG 2.1 SC 1.4.3 AA ratio: 4.5:1 for normal text, 3.0:1 for large text (>= 24px, or >= 18.66px and weight >= 700). Text and background colors come from the snapshot (blended background when captured); Image-backed blocks are checked from saved rendered…
- 독자 맞춤 설명은 독자 프로필 nemotron:0851bae336c84f3698ea0f6fcb0d03e4 vt1@ada0f5b(ai-drafted, 적용) 기준의 보조 설명이며, 원문을 대신하거나 독자의 자격·혜택·상환액을 판단하지 않습니다.
- 조사 공백 113건(claim_without_visible_condition, hidden_text, unexpanded_control)은 누락의 증거가 아니라 확인하지 못한 범위입니다.

## 10. 페이지 수집 agent 기록

- 상태: 조사 불충분, 중단 사유: submitted_with_gaps
- 조사 범위(전 → 후): {'hidden_text_blocks': 109, 'visible_text_blocks': 105, 'candidate_controls': 28, 'open_gaps': 134} → {'hidden_text_blocks': 87, 'visible_text_blocks': 127, 'candidate_controls': 26, 'open_gaps': 112}
- `조사 불충분`은 누락의 증거가 아닙니다. 보이지 않은 조건은 위반이 아니라 조사 공백으로 남깁니다.

| 공백 | 종류 | 상태 | 내용 | 닫은 행동 |
|---|---|---|---|---|
| gap-1 | unexpanded_control | open | 개인 not yet expanded |  |
| gap-2 | unexpanded_control | open | 법인 not yet expanded |  |
| gap-3 | unexpanded_control | open | 가맹점 not yet expanded |  |
| gap-4 | unexpanded_control | open | 인증센터 not yet expanded |  |
| gap-5 | unexpanded_control | open | 상품공시실 not yet expanded |  |
| gap-6 | unexpanded_control | open | 금융소비자보호포털 not yet expanded |  |
| gap-7 | unexpanded_control | open | 모바일 not yet expanded |  |
| gap-8 | unexpanded_control | open | MY not yet expanded |  |
| gap-9 | unexpanded_control | open | 혜택 not yet expanded |  |
| gap-10 | unexpanded_control | open | 카드 not yet expanded |  |
| gap-11 | unexpanded_control | open | 금융 not yet expanded |  |
| gap-12 | unexpanded_control | open | 라이프 not yet expanded |  |
| gap-13 | unexpanded_control | open | 자동차 not yet expanded |  |
| gap-14 | unexpanded_control | open | 고객센터 not yet expanded |  |
| gap-15 | unexpanded_control | open | 반드시 확인하세요! 전담상담센터를 통해 오토구매한도를 부여받은 후, 오토 not yet expanded |  |
| gap-16 | unexpanded_control | open | 반드시 확인하세요! 전담상담센터를 통해 오토구매한도를 부여받은 후, 오토 not yet expanded |  |
| gap-17 | unexpanded_control | open | 반드시 확인하세요! not yet expanded |  |
| gap-18 | unexpanded_control | open | 공지사항 not yet expanded |  |
| gap-19 | unexpanded_control | open | 이용약관 not yet expanded |  |
| gap-20 | unexpanded_control | open | 개인정보처리방침 not yet expanded |  |
| gap-21 | unexpanded_control | open | 고객권리안내 not yet expanded |  |
| gap-22 | unexpanded_control | open | 윤리경영 not yet expanded |  |
| gap-23 | unexpanded_control | open | 회사소개 not yet expanded |  |
| gap-24 | unexpanded_control | open | 소비자보호포털 not yet expanded |  |
| gap-25 | unexpanded_control | open | FAQ not yet expanded |  |
| gap-26 | unexpanded_control | open | 전자민원접수 not yet expanded |  |
| gap-27 | hidden_text | open | hidden text: 'MY 한눈에 보기' |  |
| gap-28 | hidden_text | open | hidden text: '업종별 특별한도' |  |
| gap-29 | hidden_text | open | hidden text: '가족카드 이용한도 변경' |  |
| gap-30 | hidden_text | open | hidden text: '이용내역(매출전표)' |  |
| gap-31 | hidden_text | open | hidden text: '세금 신고용 이용내역' |  |
| gap-32 | hidden_text | open | hidden text: '교통ㆍ하이패스 이용내역' |  |
| gap-33 | hidden_text | open | hidden text: '일부결제금액이월약정(리볼빙)' |  |
| gap-34 | hidden_text | open | hidden text: '포인트연계할부(세이브)' |  |
| gap-35 | hidden_text | open | hidden text: '가상계좌 신청ㆍ조회' |  |
| gap-36 | hidden_text | open | hidden text: '이용금액 입금내역' |  |
| gap-37 | hidden_text | open | hidden text: '포인트플러스 GRANDE카드 선결제' |  |
| gap-38 | hidden_text | open | hidden text: '카드비밀번호 등록ㆍ변경' |  |
| gap-39 | hidden_text | open | hidden text: '명세서수령방법 변경' |  |
| gap-40 | hidden_text | open | hidden text: '나의정보 조회ㆍ변경' |  |
| gap-41 | hidden_text | open | hidden text: '교통ㆍ하이패스 이용내역' |  |
| gap-42 | hidden_text | open | hidden text: '가족카드 이용한도' |  |
| gap-43 | hidden_text | open | hidden text: '단기카드대출 신청' |  |
| gap-44 | hidden_text | open | hidden text: '친구에게 카드추천(이벤트)' |  |
| gap-45 | hidden_text | open | hidden text: '이벤트 당첨확인' |  |
| gap-46 | hidden_text | open | hidden text: '포인트·마일리지' |  |
| gap-47 | hidden_text | open | hidden text: '포인트 이용안내' |  |
| gap-48 | hidden_text | open | hidden text: '연간서비스이용내역' |  |
| gap-49 | hidden_text | open | hidden text: '고유가 피해지원금' |  |
| gap-50 | hidden_text | open | hidden text: '교육급여 바우처' |  |
| gap-51 | hidden_text | open | hidden text: '소상공인 경영안정 바우처' |  |
| gap-52 | hidden_text | open | hidden text: '디지로카 City Edition' |  |
| gap-53 | hidden_text | open | hidden text: '디지로카 발견 Edition' |  |
| gap-54 | hidden_text | open | hidden text: 'LOCA LIKIT' |  |
| gap-55 | hidden_text | open | hidden text: '롯데백화점 AVENUEL카드' |  |
| gap-56 | hidden_text | open | hidden text: '디지로카 카드픽' |  |
| gap-57 | hidden_text | open | hidden text: '내 카드 한도 미리보기' |  |
| gap-58 | hidden_text | open | hidden text: '상품권·기프트카드' |  |
| gap-59 | hidden_text | open | hidden text: '신청내역ㆍ배송 조회' |  |
| gap-60 | hidden_text | open | hidden text: '잔액ㆍ이용내역 조회' |  |
| gap-61 | hidden_text | open | hidden text: '환불ㆍ포인트전환ㆍ기부' |  |
| gap-62 | hidden_text | open | hidden text: '인터넷사용 비밀번호ㆍ소득공제 등록' |  |
| gap-63 | hidden_text | open | hidden text: '티니패스 카드(용돈카드)' |  |
| gap-64 | hidden_text | open | hidden text: '카드 발급·수령' |  |
| gap-65 | hidden_text | open | hidden text: 'LOCA MONEY-단기카드대출' |  |
| gap-66 | hidden_text | open | hidden text: 'LOCA MONEY-장기카드대출' |  |
| gap-67 | hidden_text | open | hidden text: 'LOCA MONEY-마이너스카드' |  |
| gap-68 | hidden_text | open | hidden text: '일부결제금액이월약정(리볼빙)' |  |
| gap-69 | hidden_text | open | hidden text: '정보조회·변경·해지' |  |
| gap-70 | hidden_text | open | hidden text: '내구재(일반/오토)' |  |
| gap-71 | hidden_text | open | hidden text: '임대주택전세대출' |  |
| gap-72 | hidden_text | open | hidden text: '생활문화 서비스' |  |
| gap-73 | hidden_text | open | hidden text: '요금납부 서비스' |  |
| gap-74 | hidden_text | open | hidden text: '프리미엄 서비스' |  |
| gap-75 | hidden_text | open | hidden text: '채무면제ㆍ유예상품' |  |
| gap-76 | hidden_text | open | hidden text: '해외이용 서비스' |  |
| gap-77 | hidden_text | open | hidden text: '해외이용 안심설정' |  |
| gap-78 | hidden_text | open | hidden text: '해외 원화승인 차단' |  |
| gap-79 | hidden_text | open | hidden text: '해외이용 사전할부예약' |  |
| gap-80 | hidden_text | open | hidden text: '모바일해외안심카드' |  |
| gap-81 | hidden_text | open | hidden text: '온라인 고객상담' |  |
| gap-82 | hidden_text | open | hidden text: '자주 하는 질문(FAQ)' |  |
| gap-83 | hidden_text | open | hidden text: '장애인 회원 상담 안내' |  |
| gap-84 | hidden_text | open | hidden text: '분실신고ㆍ재발급' |  |
| gap-85 | hidden_text | open | hidden text: '타사카드 분실신고 조회' |  |
| gap-86 | hidden_text | open | hidden text: '웹사이트 보안프로그램' |  |
| gap-87 | hidden_text | open | hidden text: 'ARS번호 이용안내' |  |
| gap-88 | hidden_text | open | hidden text: '로카페이 이용안내' |  |
| gap-89 | hidden_text | open | hidden text: '개인신용정보관리보호' |  |
| gap-90 | hidden_text | open | hidden text: '결제승인 이의제기' |  |
| gap-91 | hidden_text | open | hidden text: '부채증명서 발급 신청' |  |
| gap-92 | hidden_text | open | hidden text: '증명서 발급내역' |  |
| gap-93 | hidden_text | open | hidden text: '추천카드 TOP5' |  |
| gap-94 | hidden_text | open | hidden text: '행복을 주는 롯데카드 차트 접기' |  |
| gap-95 | hidden_text | open | hidden text: '통합검색 검색어 입력' |  |
| gap-96 | hidden_text | open | hidden text: 'undefined' |  |
| gap-97 | hidden_text | closed | hidden text: '전담상담센터를 통해 오토구매한도를 부여받은 후, 오토캐시백을 신청하시기 바랍니다.' | interact expand ul.car.toggleList (gap gap-15) |
| gap-98 | hidden_text | closed | hidden text: '오토캐시백 신청되지 않은 차량구매 건은 캐시백이 제공되지 않습니다.' | interact expand ul.car.toggleList (gap gap-15) |
| gap-99 | hidden_text | closed | hidden text: '부여된 오토구매한도 내에서 오토캐시백과 오토할부를 각각 이용할 수 있습니다.' | interact expand ul.car.toggleList (gap gap-15) |
| gap-100 | hidden_text | closed | hidden text: '오토캐시백과 오토할부 동시 이용을 원하실 경우, 롯데카드 오토콜센터(1577-2200)로 문의주시기 바랍니다' | interact expand ul.car.toggleList (gap gap-15) |
| gap-101 | hidden_text | closed | hidden text: '오토캐시백 신청 후 신청금액 이하로 처음 결제되는 일시불 금액 기준으로 오토캐시백이 적용됩니다.(이후 결제 ' | interact expand ul.car.toggleList (gap gap-15) |
| gap-102 | hidden_text | closed | hidden text: '법인, 가족회원은 제외되며, 롯데카드 심사 자격기준에 의해 이용이 제한될 수 있습니다.' | interact expand ul.car.toggleList (gap gap-15) |
| gap-103 | hidden_text | closed | hidden text: '롯데카드에 국산차 또는 수입차 가맹점으로 등록되어 있는 곳에서 결제하는 경우에만 오토캐시백이 제공됩니다.' | interact expand ul.car.toggleList (gap gap-15) |
| gap-104 | hidden_text | closed | hidden text: '차량구매대금이 청구되는 달의 결제금액이 연체될 경우, 캐시백을 지급하지 않습니다.(연체일수 금액무관)' | interact expand ul.car.toggleList (gap gap-15) |
| gap-105 | hidden_text | closed | hidden text: '대금결제일 이전에 선입금해도 원 대금결제월을 기준으로 캐시백을 지급합니다. 예) 원 대금결제월이 02.15인' | interact expand ul.car.toggleList (gap gap-15) |
| gap-106 | hidden_text | closed | hidden text: '매출취소 시, 이미 지급된 캐시백 금액은 현금으로 청구됩니다.(체크카드는 이미 지급된 캐시백 금액 차감 후 ' | interact expand ul.car.toggleList (gap gap-15) |
| gap-107 | hidden_text | closed | hidden text: '오토캐시백과 오토할부, 오토세이브, 선포인트 등을 함께 이용할 경우, 이용금액별로 각각 결제해야 합니다.' | interact expand ul.car.toggleList (gap gap-15) |
| gap-108 | hidden_text | closed | hidden text: '오토캐시백 이용금액은 각종 포인트.마일리지 적립, 할인, 세이브.선포인트.일부결제금액이월약정 서비스에 적용되' | interact expand ul.car.toggleList (gap gap-15) |
| gap-109 | hidden_text | closed | hidden text: '계약체결 전 금융상품설명서와 약관을 확인하시기 바랍니다.' | interact expand ul.car.toggleList (gap gap-15) |
| gap-110 | hidden_text | closed | hidden text: '서비스 제공 업종은 롯데카드에 등록된 가맹점 업종을 기준으로 합니다.' | interact expand ul.car.toggleList (gap gap-15) |
| gap-111 | hidden_text | closed | hidden text: '신용카드 발급이 부적정한 경우(개인신용평점 낮음 등) 카드발급이 제한될 수 있습니다.' | interact expand ul.car.toggleList (gap gap-15) |
| gap-112 | hidden_text | closed | hidden text: '카드이용대금과 이에 수반되는 모든 수수료를 지정된 대금 결제일에 상환해야 합니다.' | interact expand ul.car.toggleList (gap gap-15) |
| gap-113 | hidden_text | closed | hidden text: '금융소비자는 금소법 제19조 제1항에 따라 해당상품 또는 서비스에 대하여 설명을 받을 권리가 있습니다.' | interact expand ul.car.toggleList (gap gap-15) |
| gap-114 | hidden_text | closed | hidden text: '연체이자율 : 회원별, 이용상품별 약정이율 + 최대3%, 법정 최고금리(연 20%) 이내' | interact expand ul.car.toggleList (gap gap-15) |
| gap-115 | hidden_text | closed | hidden text: '단, 연체발생시점에 약정이율이 없는 경우 아래와 같이 약정이율을 적용' | interact expand ul.car.toggleList (gap gap-15) |
| gap-116 | hidden_text | closed | hidden text: '일시불 거래 연체 시 : 거래 발생 시점의 최소기간(2개월)유이자 할부 금리' | interact expand ul.car.toggleList (gap gap-15) |
| gap-117 | hidden_text | closed | hidden text: '무이자 할부 거래 연체 시 : 거래 발생 시점의 동일한 할부계약기간의 유이자 할부 금리' | interact expand ul.car.toggleList (gap gap-15) |
| gap-118 | hidden_text | closed | hidden text: '한국은행에서 매월 발표하는 가장 최근의 비은행 금융기관 가중평균대출금리(신규대출기준)' | interact expand ul.car.toggleList (gap gap-15) |
| gap-119 | hidden_text | open | hidden text: '롯데인터넷면세점' |  |
| gap-120 | hidden_text | open | hidden text: '롯데그린파트너십' |  |
| gap-121 | hidden_text | open | hidden text: 'B2B 구매시스템' |  |
| gap-122 | hidden_text | open | hidden text: '롯데스카이힐 C.C' |  |
| gap-123 | hidden_text | open | hidden text: '사이버인재개발원' |  |
| gap-124 | hidden_text | open | hidden text: '롯데유통사업본부' |  |
| gap-125 | hidden_text | open | hidden text: '롯데주류BG-처음처럼' |  |
| gap-126 | hidden_text | open | hidden text: '롯데주류BG-와인' |  |
| gap-127 | hidden_text | open | hidden text: '롯데칠성음료 기업' |  |
| gap-128 | hidden_text | open | hidden text: '롯데후레쉬델리카' |  |
| gap-129 | hidden_text | open | hidden text: '캐논코리아비즈니스솔루션' |  |
| gap-130 | hidden_text | open | hidden text: '크리스피크림도넛' |  |
| gap-131 | hidden_text | open | hidden text: '후지필름 인터넷사진관' |  |
| gap-132 | hidden_text | open | hidden text: 'T.G.I.Friday’s' |  |
| gap-133 | hidden_text | open | hidden text: '롯데미소금융재단' |  |
| gap-134 | hidden_text | open | hidden text: 'MENU open' |  |

| 턴 | 도구 | 인자 | 대상 공백 | 결과 |
|---|---|---|---|---|
| 1 | inspect_page | {} |  | 새 증거 |
| 2 | probe_selector | {"selectors": ["div.container", "div.LP_cont", "div.contents", "div.s… |  | 새 증거 |
| 3 | submit_rule | {"product_name": "신차일시불(캐시백)", "summary": "Select all on-page text de… |  | 새 증거 |
| 4 | submit_rule | {"product_name": "신차일시불(캐시백)", "summary": "Select all on-page text de… |  | 새 증거 |
| 5 | interact | {"action": "expand", "selector": "ul.car.toggleList", "gap_id": "gap-… | gap-15 | 새 증거 |
| 6 | inspect_page | {} |  | 새 증거 |
| 7 | submit_rule | {"product_name": "신차일시불(캐시백)", "summary": "Selectors that capture the… |  | 새 증거 |
| 8 | submit_rule | {"product_name": "신차일시불(캐시백)", "summary": "Selectors that capture the… |  | 새 증거 |
| 9 | submit_rule | {"product_name": "신차일시불(캐시백)", "summary": "Selectors capture the main… |  | 새 증거 |

## 11. 증거 카드와 조사 공백

- 상태: 완료, 카드 31건, 검증 탈락 0건
- 카드는 원문 인용과 출처(`dom-N`)가 코드로 재확인된 사실 단위이며, 법률 판단이 아닙니다.

| 카드 | 종류 | 인용 | 조건 | 예외 | 출처 | 가시성 |
|---|---|---|---|---|---|---|
| c1 | benefit_claim | 새 차 살 때, 롯데카드 결제하면, 캐시백 혜택 |  |  | dom-1 | default_visible |
| c2 | condition | 오토캐시백 프로모션 사전신청 후, 본인명의 롯데카드 일시불 결제 |  |  | dom-2 | default_visible |
| c3 | benefit_claim | 캐시백최대1.4% |  |  | dom-3 | default_visible |
| c4 | benefit_claim | 5천만원 이상 : 1.4% |  |  | dom-32 | default_visible |
| c5 | benefit_claim | 4천만원 이상 : 1.4% |  |  | dom-33 | default_visible |
| c6 | benefit_claim | 3천만원 이상 : 1.4% |  |  | dom-34 | default_visible |
| c7 | benefit_claim | 2천만원 이상 : 1.4% |  |  | dom-35 | default_visible |
| c8 | benefit_claim | 1천만원 이상 : 1.4% |  |  | dom-36 | default_visible |
| c9 | benefit_claim | 1천만원 미만 : 1.4% |  |  | dom-37 | default_visible |
| c10 | benefit_claim | 체크카드로 결제 시 구매금액 관계없이 0.5% 캐시백이 제공됩니다. | 구매금액 관계없이 |  | dom-38 | default_visible |
| c11 | condition | 전액기존한도/부분선입금 : 청구서 결제일(상환완료) + 7일 이내(전표접수, 휴무일에 따라 변경가능) | (전표접수, 휴무일에 따라 변경가능) |  | dom-42 | default_visible |
| c12 | condition | 전액선입금 : 승인전표매입(상환완료) + 7일 이내 |  |  | dom-43 | default_visible |
| c13 | condition | 승인전표매입 + 6일 이내 캐시백 지급(전표접수, 휴무일에 따라 변경가능) | (전표접수, 휴무일에 따라 변경가능) |  | dom-47 | default_visible |
| c14 | condition | 전담상담센터를 통해 오토구매한도를 부여받은 후, 오토캐시백을 신청하시기 바랍니다. |  |  | dom-49 | default_visible |
| c15 | exception | 오토캐시백 신청되지 않은 차량구매 건은 캐시백이 제공되지 않습니다. |  |  | dom-50 | default_visible |
| c16 | condition | 오토캐시백 신청 후 신청금액 이하로 처음 결제되는 일시불 금액 기준으로 오토캐시백이 적용됩니다.(이후 결제 건은 오토캐시백이… |  | (이후 결제 건은 오토캐시백이 적용되지 않습니다.) | dom-53 | default_visible |
| c17 | exception | 법인, 가족회원은 제외되며, 롯데카드 심사 자격기준에 의해 이용이 제한될 수 있습니다. | 롯데카드 심사 자격기준에 의해 이용이 제한될 수 있습니다. | 법인, 가족회원은 제외되며 | dom-54 | default_visible |
| c18 | condition | 롯데카드에 국산차 또는 수입차 가맹점으로 등록되어 있는 곳에서 결제하는 경우에만 오토캐시백이 제공됩니다. |  |  | dom-55 | default_visible |
| c19 | exception | 차량구매대금이 청구되는 달의 결제금액이 연체될 경우, 캐시백을 지급하지 않습니다.(연체일수 금액무관) |  | (연체일수 금액무관) | dom-56 | default_visible |
| c20 | condition | 대금결제일 이전에 선입금해도 원 대금결제월을 기준으로 캐시백을 지급합니다. |  |  | dom-57 | default_visible |
| c21 | exception | 매출취소 시, 이미 지급된 캐시백 금액은 현금으로 청구됩니다.(체크카드는 이미 지급된 캐시백 금액 차감 후 환불) |  | (체크카드는 이미 지급된 캐시백 금액 차감 후 환불) | dom-59 | default_visible |
| c22 | condition | 오토캐시백과 오토할부, 오토세이브, 선포인트 등을 함께 이용할 경우, 이용금액별로 각각 결제해야 합니다. |  |  | dom-60 | default_visible |
| c23 | exception | 법인, 선불, 기프트, 가족카드는 서비스 이용대상에서 제외됩니다. |  |  | dom-61 | default_visible |
| c24 | exception | 오토캐시백 이용금액은 각종 포인트.마일리지 적립, 할인, 세이브.선포인트.일부결제금액이월약정 서비스에 적용되지 않습니다. |  |  | dom-62 | default_visible |
| c25 | rate_claim | 연체이자율 : 회원별, 이용상품별 약정이율 + 최대3%, 법정 최고금리(연 20%) 이내 |  |  | dom-68 | default_visible |
| c26 | rate_claim | 일시불 거래 연체 시 : 거래 발생 시점의 최소기간(2개월)유이자 할부 금리 |  |  | dom-70 | revealed |
| c27 | rate_claim | 무이자 할부 거래 연체 시 : 거래 발생 시점의 동일한 할부계약기간의 유이자 할부 금리 |  |  | dom-71 | revealed |
| c28 | rate_claim | 그 외의 경우 : 약정이율은 상법상 상시법정이율과 상호금융 가계자금대출금리*중 높은 금리 적용 |  |  | dom-72 | revealed |
| c29 | warning | 상환능력에 비해 신용카드 사용액이 과도할 경우 귀하의 개인 신용평점이 하락할 수 있습니다. |  |  | dom-74 | default_visible |
| c30 | warning | 개인 신용평점 하락 시 금융거래 관련된 불이익이 발생할 수 있습니다. |  |  | dom-75 | default_visible |
| c31 | warning | 일정기간 원리금을 연체할 경우, 모든 원리금을 변제할 의무가 발생할 수 있습니다. |  |  | dom-76 | default_visible |

| 공백 | 종류 | 상태 | 관련 카드 |
|---|---|---|---|
| gap-1 | unexpanded_control | open |  |
| gap-2 | unexpanded_control | open |  |
| gap-3 | unexpanded_control | open |  |
| gap-4 | unexpanded_control | open |  |
| gap-5 | unexpanded_control | open |  |
| gap-6 | unexpanded_control | open |  |
| gap-7 | unexpanded_control | open |  |
| gap-8 | unexpanded_control | open |  |
| gap-9 | unexpanded_control | open |  |
| gap-10 | unexpanded_control | open |  |
| gap-11 | unexpanded_control | open |  |
| gap-12 | unexpanded_control | open |  |
| gap-13 | unexpanded_control | open |  |
| gap-14 | unexpanded_control | open |  |
| gap-15 | unexpanded_control | open |  |
| gap-16 | unexpanded_control | open |  |
| gap-17 | unexpanded_control | open |  |
| gap-18 | unexpanded_control | open |  |
| gap-19 | unexpanded_control | open |  |
| gap-20 | unexpanded_control | open |  |
| gap-21 | unexpanded_control | open |  |
| gap-22 | unexpanded_control | open |  |
| gap-23 | unexpanded_control | open |  |
| gap-24 | unexpanded_control | open |  |
| gap-25 | unexpanded_control | open |  |
| gap-26 | unexpanded_control | open |  |
| gap-27 | hidden_text | open |  |
| gap-28 | hidden_text | open |  |
| gap-29 | hidden_text | open |  |
| gap-30 | hidden_text | open |  |
| gap-31 | hidden_text | open |  |
| gap-32 | hidden_text | open |  |
| gap-33 | hidden_text | open |  |
| gap-34 | hidden_text | open |  |
| gap-35 | hidden_text | open |  |
| gap-36 | hidden_text | open |  |
| gap-37 | hidden_text | open |  |
| gap-38 | hidden_text | open |  |
| gap-39 | hidden_text | open |  |
| gap-40 | hidden_text | open |  |
| gap-41 | hidden_text | open |  |
| gap-42 | hidden_text | open |  |
| gap-43 | hidden_text | open |  |
| gap-44 | hidden_text | open |  |
| gap-45 | hidden_text | open |  |
| gap-46 | hidden_text | open |  |
| gap-47 | hidden_text | open |  |
| gap-48 | hidden_text | open |  |
| gap-49 | hidden_text | open |  |
| gap-50 | hidden_text | open |  |
| gap-51 | hidden_text | open |  |
| gap-52 | hidden_text | open |  |
| gap-53 | hidden_text | open |  |
| gap-54 | hidden_text | open |  |
| gap-55 | hidden_text | open |  |
| gap-56 | hidden_text | open |  |
| gap-57 | hidden_text | open |  |
| gap-58 | hidden_text | open |  |
| gap-59 | hidden_text | open |  |
| gap-60 | hidden_text | open |  |
| gap-61 | hidden_text | open |  |
| gap-62 | hidden_text | open |  |
| gap-63 | hidden_text | open |  |
| gap-64 | hidden_text | open |  |
| gap-65 | hidden_text | open |  |
| gap-66 | hidden_text | open |  |
| gap-67 | hidden_text | open |  |
| gap-68 | hidden_text | open |  |
| gap-69 | hidden_text | open |  |
| gap-70 | hidden_text | open |  |
| gap-71 | hidden_text | open |  |
| gap-72 | hidden_text | open |  |
| gap-73 | hidden_text | open |  |
| gap-74 | hidden_text | open |  |
| gap-75 | hidden_text | open |  |
| gap-76 | hidden_text | open |  |
| gap-77 | hidden_text | open |  |
| gap-78 | hidden_text | open |  |
| gap-79 | hidden_text | open |  |
| gap-80 | hidden_text | open |  |
| gap-81 | hidden_text | open |  |
| gap-82 | hidden_text | open |  |
| gap-83 | hidden_text | open |  |
| gap-84 | hidden_text | open |  |
| gap-85 | hidden_text | open |  |
| gap-86 | hidden_text | open |  |
| gap-87 | hidden_text | open |  |
| gap-88 | hidden_text | open |  |
| gap-89 | hidden_text | open |  |
| gap-90 | hidden_text | open |  |
| gap-91 | hidden_text | open |  |
| gap-92 | hidden_text | open |  |
| gap-93 | hidden_text | open |  |
| gap-94 | hidden_text | open |  |
| gap-95 | hidden_text | open |  |
| gap-96 | hidden_text | open |  |
| gap-119 | hidden_text | open |  |
| gap-120 | hidden_text | open |  |
| gap-121 | hidden_text | open |  |
| gap-122 | hidden_text | open |  |
| gap-123 | hidden_text | open |  |
| gap-124 | hidden_text | open |  |
| gap-125 | hidden_text | open |  |
| gap-126 | hidden_text | open |  |
| gap-127 | hidden_text | open |  |
| gap-128 | hidden_text | open |  |
| gap-129 | hidden_text | open |  |
| gap-130 | hidden_text | open |  |
| gap-131 | hidden_text | open |  |
| gap-132 | hidden_text | open |  |
| gap-133 | hidden_text | open |  |
| gap-134 | hidden_text | open |  |
| - | claim_without_visible_condition | open | c1, c3, c4, c5, c6, c7, c8, c9, c25, c26, c27, c28 |

## 12. 참고 사례 (판정에 사용하지 않음)

- 아래 사례는 비슷한 표시 유형을 찾아 참고로만 연결한 것입니다. 이 검토의 적합·부적합 판정은 사례와 무관하게 루브릭과 페이지 인용으로만 정해졌습니다.
- 상태: 부분 완료 (사례 연결이 턴 한도 8로 중단되어 그때까지 검증된 연결만 보고함), 후보 18건, 연결 agent(검색 6회, 읽기 5회, 중단 사유 max_turns), 사례 출처 db
- 연결은 agent가 제안하고, 코드가 페이지 인용과 사례 인용을 원문에서 다시 찾아 확인한 것만 남겼습니다.

| 사례 | 카드 | 페이지 인용 | 사례 인용 | 중요한 차이 | 페이지 단독 판단 | 공식 출처 |
|---|---|---|---|---|---|---|
| case.crefia_ad_type_unconditional_discount | c3 | 캐시백최대1.4% | 허위·과장 주요 사례 ③ 할인 제외 대상 가맹점이 존재하고 있으나 '무조건 0.7% 할인 되는 카드' 등의… | 제품유형 동일(할인/캐시백 카드)이며, 본 페이지는 다른 카드들에서 사전신청·가맹점등록·연체시 미지급 등 여러 적용조건을 별도 문구로 제시하고… | full | https://customer.crefia.or.kr/common/forward.xx?url=%2Fcustomer%2Freceipt%2FfalseHype%2FfalseHypeCase |
| case.kca_20170930_cardco_homepage_addon_disclosure | c3, c11, c13, c2 | 캐시백최대1.4% | (필요 이용 실적 표시 미흡) 18 개 제휴 신용카드 중 11 개(61.1%)가 할인서비스를 받기 위한 이… | 케이스는 여러 카드사의 전체 홈페이지 첫페이지 표기 실태를 분석한 연구보고서 성격이며 본 페이지는 한 상품의 개별 안내임.; 페이지 내 일부 … | full | https://www.kca.go.kr/smartconsumer/sub.do?menukey=7301&mode=view&no=1002635168&page=11&cate=00000057 |
| case.fsc_20210608_ad_guideline_benefit_disadvantage_balance | c3, c11, c13, c19, c29, c30 | 캐시백최대1.4% | ㅇ 금소법령에서는 광고 시 글자의 색깔·크기 또는 음성의 속도·크기 등을 해당 금융상품으로 인해 소비자가 … | 케이스는 광고방법(글자 크기·색상 등) 전반의 가이드라인을 제시하는 문서이며, 본 페이지의 카드 문구는 혜택·유의사항이 텍스트로 포함되어 있으… | full | https://www.fsc.go.kr/no010101/76045 |

---

이 문서는 자동 검토 결과입니다(ai-generated). 게시 여부의 최종 판단은 컴플라이언스 담당자가 합니다.
