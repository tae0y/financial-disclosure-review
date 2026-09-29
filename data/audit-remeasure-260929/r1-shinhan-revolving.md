---
ai-generated: true
human-review: false
---

# 금융상품 판매화면 검토 결과

- 판정: **판정 불가**
- 조치 방침: judge_explanation_duty 단계에서 실행이 중단되어(비용 한도 도달) 자동 판정을 내리지 않았습니다.
- 대상 화면: https://www.shinhancard.com/pconts/html/finance/revolving/CONFM60030/CONFM60030R01.html
- 상품명: 일부결제금액이월약정(리볼빙)
- 상품유형/화면유형: 리볼빙 / 업무광고
- 분류 근거: 본문에 '일부결제금액이월약정(리볼빙) 과 리볼빙은 같은 표현입니다.'라고 명시되어 있어 이 페이지의 세부 상품 유형이 리볼빙임이 명확합니다.
- 페이지 수집: 조사 불충분 (no_viable_control)
- 에이전트 실행: 페이지 탐색 agent 13턴(no_viable_control) · 사례 연결 agent 5턴(finished) · 독자 선택 agent 2턴(chosen)

## 1. 담당자 조치 목록

1. 검토 중단(비용 한도 도달): run budget $0.15 reached ($0.158885) before ExplanationJudgments
2. 페이지 수집 조사 불충분(no_viable_control): 열린 조사 공백 40건을 사람이 화면에서 확인
3. 한도를 조정해 재실행하거나 사람이 페이지 전체를 직접 검토

## 2. 검토 요약

| 검토 영역 | 검토 항목 | 위반·반려 | 판정 불가·차이 |
|---|---|---|---|
| 표시방법 | 8 | 5 | 1 |
| 설명의무(원문) | 0/0 | 0 | 0 |
| 설명의무(독자 맞춤 설명) | 0/0 | 0 | 0 |
| 독자 맞춤 설명 | 24 | 1 | 0 |

부적합 5건 중 위반 5건, 권고 미충족 0건입니다. 광고 규정과 협회 표시 규정은 공개 상품 페이지(광고)에 직접 적용되어 위반으로 읽고, 설명의무 항목은 계약 권유 단계의 의무를 광고 화면에 준용한 것이어서 권고 미충족으로 읽습니다.

## 3. 확인이 필요한 항목

| 항목 | 대상 | 판정 | 구분 | 사유 | 인용 |
|---|---|---|---|---|---|
| E01 | 판매 화면 표시방법 | 부적합 | 위반(법령) | 혜택 문구(b25, b29)는 13.5pt 굵은 글씨로 눈에 띄는 반면 불이익·수수료 문구(b26, b30, b51, b52)는 10.5pt로 가늘거나 회색 계열로 표시되어 글자 크기·색 대비에서 혜택이 더 도드라져 균형을 잃었습니다. | 최소금액만 내도 카드값은 연체되지 않아요 / 언제든 내 상황에 맞게 결제비율을 바꿀 수 있어요 / DSR 산정에서 제외돼요 / 생활패턴에 맞게… |
| E02 | 판매 화면 표시방법 | 판정 불가 | - | a pass would be unproven: 6 labelled block(s) never visible |  |
| E04 | 판매 화면 표시방법 | 부적합 | 위반(협회 자율규제) | measured contrast below the minimum: ['b83'] (below_contrast_min) | 이월한 금액뿐 아니라, 매달 카드값의 일부도 계속 이월되므로 상환해야 할 원금이 계속 늘어날 수 있습니다. |
| E05 | 판매 화면 표시방법 | 부적합 | 위반(협회 자율규제) | measured contrast below the minimum: ['b83'] (below_contrast_min) | 이월한 금액뿐 아니라, 매달 카드값의 일부도 계속 이월되므로 상환해야 할 원금이 계속 늘어날 수 있습니다. |
| E06 | 판매 화면 표시방법 | 부적합 | 위반(협회 자율규제) | 의무표시사항 가운데 b121(준법감시 심의필 ...)이 한 문단에 이어 붙어 있어 문장마다 기호나 줄바꿈으로 구분되어 있지 않습니다. | 준법감시 심의필 제20260311-Cpi-016호 (2026.03.11~2027.03.10) |
| E07 | 판매 화면 표시방법 | 부적합 | 위반(협회 자율규제) | 수수료·세부금액(b51, b52)과 일부 안내문(b83, b91) 등이 기본 스냅샷에서 숨겨져 있다가 사용자 조작으로(D 표시) 나타나므로 주요 정보를 접힌 영역 등으로 숨겼습니다. | 수수료 / 0원 / 이월한 금액뿐 아니라, 매달 카드값의 일부도 계속 이월되므로 상환해야 할 원금이 계속 늘어날 수 있습니다. / 최소결제금액… |
| 원문 대체 | 독자 맞춤 설명 dom-188 | 원문 대체 | - | 근거 원문에 없는 수치: 30000, 50000 |  |

## 4. 표시방법 검토 상세

| 항목 | 판정 | 근거 블록 | 사유 |
|---|---|---|---|
| E01 | 부적합 | b25, b29, b26, b30, b51, b52 | 혜택 문구(b25, b29)는 13.5pt 굵은 글씨로 눈에 띄는 반면 불이익·수수료 문구(b26, b30, b51, b52)는 10.5pt로 가늘거나 회색 계열로 표시되어 글자 크기·색 대비에서 혜택이 더 도드라져 균형을 잃었습니다. |
| E02 | 판정 불가 |  | a pass would be unproven: 6 labelled block(s) never visible |
| E03 | 적합 | b11, b109, b112, b83, b91 | 이자율 관련 표기(b11, b109, b112)는 굵은 글씨와(또는 음영 배경)로 강조되어 있고 경고문구(b83)는 붉은 색 등으로 시각적으로 구별되어 있습니다. |
| E04 | 부적합 | b83 | measured contrast below the minimum: ['b83'] (below_contrast_min) |
| E05 | 부적합 | b83 | measured contrast below the minimum: ['b83'] (below_contrast_min) |
| E06 | 부적합 | b121 | 의무표시사항 가운데 b121(준법감시 심의필 ...)이 한 문단에 이어 붙어 있어 문장마다 기호나 줄바꿈으로 구분되어 있지 않습니다. |
| E07 | 부적합 | b51, b52, b83, b91 | 수수료·세부금액(b51, b52)과 일부 안내문(b83, b91) 등이 기본 스냅샷에서 숨겨져 있다가 사용자 조작으로(D 표시) 나타나므로 주요 정보를 접힌 영역 등으로 숨겼습니다. |
| E08 | 적합 | b11, b109 | 최저·최고 금리 정보가 b11(5.4~19.9)과 b109(최저 5.4% ~ 최고 19.9%)에서 함께 제공되어 짝이 되는 주요 정보를 함께 제시하고 있습니다. |

## 5. 설명의무 검토 상세 (원문 대비 독자 맞춤 설명)

(해당 항목 없음)

- F01–F19·F21·F22는 같은 의무를 담은 설명 코드(설명01–19·27·28)와 한 주제입니다. 표에는 둘 다 남기고, 조치 목록에서는 같은 판정이면 한 번만 셉니다.

## 6. 독자 맞춤 설명 결과

- 상태: 완료 (1개 단위는 코드 검증에 걸려 원문으로 대체됨)
- 독자 프로필: nemotron:1c4fd4117b0440e6a65134c820e0bc37 vt1@ada0f5b (nvidia/Nemotron-Personas-Korea rev=ada0f5b uuid=1c4fd4117b0440e6a65134c820e0bc37 (CC-BY-4.0), ai-drafted, 적용)
- 독자 선택: 자유 문장 → 선택 agent, 조건 {'age_min': 20, 'age_max': 29}, 일치 135011행, 중단 사유 chosen
- 금융 익숙도: 낮음 (요청 문장)
- 독자 개요(합성 페르소나): 21세 남자 · 학력 2~3년제 전문대학 · 직업 미디어 콘텐츠 창작자 · 경기 거주 · 가구 부모와 동거 김우섭 씨는 일산의 다락방에서 콘텐츠를 만드는 21세 창작자로, 농구와 헬스를 즐기면서도 치킨과 흡연의 유혹을 완전히 떨치지 못한 채 소박한 성공을 꿈꾸는 청년입니다.
- 원문 사실(exact_fact)은 설명 옆에 그대로 남습니다. 위험 개념에는 비유를 쓰지 않습니다.

| 단위 | 출처 | 원 사실 | 설명 | 비유 | 상태 |
|---|---|---|---|---|---|
| u1 | dom-1 | 리볼빙 약정 고객이에요 | 이 문구는 페이지가 '리볼빙 약정 고객이에요'라고 적고 있다는 뜻입니다. 별도 표기가 없으면 여기서는 상품 설명 대상이 그런 상태임을 알리는 문장입니다. | - | accepted |
| u2 | dom-9 | 약정 결제비율 10~100 % | 약정 결제비율을 10%부터 100%까지 정할 수 있다는 뜻입니다. 몇 퍼센트를 정하느냐에 따라 매달 실제로 낼 금액이 달라집니다. | - | accepted |
| u3 | dom-10 | 금리 5.4~19.9% | 리볼빙에 적용되는 이자율(약정금리)이 5.4%에서 19.9% 범위에 있다는 뜻입니다. 구체적 수치는 개인별로 달라질 수 있습니다. | - | accepted |
| u4 | dom-11 | 약정기간 3~60 개월 | 약정 기간을 3개월부터 60개월 사이에서 정할 수 있다는 뜻입니다. 기간에 따라 매달 납부 방식과 총 이자 변화가 달라질 수 있습니다. | - | accepted |
| u5 | dom-65 | 이월한 금액뿐 아니라, 매달 카드값의 일부도 계속 이월되므로 상환해야 할 원금이 계속 늘어날 수 있습니다. | 이 문장은 이월(다음달로 넘김)을 하면 넘긴 금액뿐 아니라 매달 결제하지 않은 일부도 계속 이월될 수 있어 원금이 늘어날 수 있다고 경고하고 있습니다. | - | accepted |
| u6 | dom-69 | 미결제된 나머지 잔액은 자동으로 이월되어 연체 처리되지 않음 (이월된 금액은 다음달에 리볼빙 이자금액과 함께 청구) | 약정한 비율 이상만 내면 나머지 잔액은 자동으로 다음달로 넘어갑니다. 그 경우 즉시 '연체'로 처리되지는 않습니다. 이월된 금액은 다음달에 리볼빙 이자와 같이 … | - | accepted |
| u7 | dom-73 | 최소결제금액 중 미납된 금액만 연체 처리되어 입금될 때까지 추가인출 됨 (미납된 연체금액은 입금될 때까지 연체 이자금액 발생) | 최소결제금액 일부를 못 내면, 못 낸 부분은 연체로 처리됩니다. 그 연체금액은 입금될 때까지 계속 이자(연체이자)가 붙고 추가로 계좌에서 빼갈 수 있습니다. | - | accepted |
| u8 | dom-91 | 중도상환 수수료는 없습니다. | 약정을 중간에 끝내고 전액 갚더라도 따로 중도상환 수수료는 청구하지 않는다고 적혀 있습니다. 다만 해지 시 잔액 처리 방식은 별도로 확인해야 합니다. | - | accepted |
| u9 | dom-95 | 결제성 일부결제금액이월약정 평균 금리: 17.28% | 이 숫자는 '평균 금리'입니다. 전체 이용자 또는 계약의 평균이 17.28%라는 뜻이지, 개인별로 반드시 이 금리가 적용된다는 의미는 아닙니다. | - | accepted |
| u10 | dom-100 | 연체금리는 “약정금리+최대 3%, 법정 최고금리(연 20%)이내"에서 적용됩니다. | 연체가 생기면 보통의 약정금리에 최대 3%를 더해 연체금리를 적용한다고 적혀 있습니다. 다만 법으로 정한 연 20%를 넘지 않는 범위에서 적용됩니다. | - | accepted |
| u11 | dom-118 | 예를 들어, 70%를 약정 결제 비율로 정하면, 매달 리볼빙 이용 금액의 70%만 결제하면 돼요. | 이 예시는 약정 결제비율이 70%이면 매달 이용액의 70%만 내고 나머지를 이월할 수 있다는 뜻입니다. 나머지에는 리볼빙 이자가 붙습니다. | - | accepted |
| u12 | dom-121 | 일반 리볼빙: 1년~5년(1년 단위) | 일반 리볼빙 약정은 1년에서 5년 사이로, 1년 단위로 기간을 정할 수 있다고 적혀 있습니다. 기간 설정은 계약 내용에 따릅니다. | - | accepted |
| u13 | dom-122 | 선택형 리볼빙: 3개월~36개월(1개월 단위) | 선택형 리볼빙은 3개월에서 36개월 사이에서, 1개월 단위로 기간을 정할 수 있다는 뜻입니다. 기간이 짧을수록 이자 부담 구조가 달라질 수 있습니다. | - | accepted |
| u14 | dom-124 | 리볼빙 이용 금액 X 최소 결제 비율과 50,000원 중 큰 금액이에요. | 최소결제금액은 '(리볼빙 이용금액 × 최소결제비율)'과 50,000원 중 큰 금액으로 정한다고 적혀 있습니다. 즉 계산한 값이 50,000원보다 작으면 50,0… | - | accepted |
| u15 | dom-125 | 리볼빙은 본인 한도 내 일시불 거래에 대해서만 적용 가능해요. | 리볼빙은 '본인 한도 안에서 한 번에 결제한(일시불) 거래'에만 적용된다고 적혀 있습니다. 일부 거래 유형은 대상에서 제외될 수 있습니다. | - | accepted |
| u16 | dom-132 | 리볼빙은 본인한도 내에서 이용한 결제금액 중 미리 약정한 약정(최소)결제비율 이상 결제하면, 나머지 금액은 다음달로 이월되는… | 리볼빙 정의입니다. 약정한 비율 이상만 내면 나머지 금액을 다음달로 넘기고, 그 넘긴 금액에 대해 이자가 붙습니다. | - | accepted |
| u17 | dom-135 | 리볼빙 신규 약정은 고객님의 모든 카드에 적용되며, 카드/브랜드 단위로는 신청할 수 없습니다. | 새로 리볼빙 약정을 하면 '모든 카드'에 일괄 적용된다고 적혀 있습니다. 특정 카드 하나만 따로 신청하는 방식은 아닙니다. | - | accepted |
| u18 | dom-161 | 리볼빙을 해지하면 일부결제금액이월약정 잔액은 전액 일시청구 됩니다. | 리볼빙을 해지하면 남아 있는 이월 잔액을 한꺼번에 전액 청구한다고 적혀 있습니다. 해지 전에 잔액 처리 방식을 확인해야 합니다. | - | accepted |
| u19 | dom-171 | 약정결제비율은 최소결제비율~100단위까지 1%단위로 지정할 수 있으며 청구금액을 결정합니다. | 약정 결제비율은 최소결제비율부터 100%까지 1% 단위로 정할 수 있다고 적혀 있습니다. 이 비율이 청구금액을 결정합니다. | - | accepted |
| u20 | dom-172 | 최소결제비율은 신용도에 따라 10% 이상으로 차등 적용되어 임의로 변경할 수 없으며 최소결제금액을 결정합니다. | 최소결제비율은 신용도에 따라 '10% 이상'으로 정해진다고 적혀 있습니다. 이 비율은 임의로 바꿀 수 없고 최소 결제금액을 결정하는 기준이 됩니다. | - | accepted |
| u21 | dom-186 | ③청구금액 = (① 약정 적용 금액 x 약정결제비율) + ② 약정 미적용 금액 | 청구금액 계산식입니다. '약정 적용 금액 × 약정결제비율'에 약정 적용이 안 된 금액을 더하면 청구금액이 됩니다. | - | accepted |
| u22 | dom-187 | ④최소결제금액 = (① 약정 적용 금액 x 최소결제비율) + ② 약정 미적용 금액 | 최소결제금액 계산식입니다. '약정 적용 금액 × 최소결제비율'에 약정 미적용 금액을 더하면 최소로 내야 할 금액이 됩니다. | - | accepted |
| u23 | dom-188 | 단, (① 약정 적용 금액 x 최소결제비율)이 5만원 미만인 경우, 5만원으로 합니다. (’14년 12월 30일 이전 약정 … | 계산한 최소결제금액이 50,000원 미만이면 최소결제금액을 50,000원으로 정한다고 적혀 있습니다. 과거 약정(’14년 12월 30일 이전)은 30,000원이… | - | reverted |
| u24 | dom-196 | 약정 적용 금액 중 단기카드대출 (현금서비스) 금액은 최초결제일에 결제될 때까지 단기카드대출 (현금서비스) 이자가 부과됩니다. | 약정에 포함된 금액 중 현금서비스(단기카드대출)는 최초결제일에 결제될 때까지 별도의 현금서비스 이자가 붙는다고 적혀 있습니다. 즉 현금서비스에는 해당하는 이자 … | - | accepted |

### 운영 통제 (판정 대상 아님)

- 화면: AI 생성 고지, 원문 보기 전환, 오류 신고
- 거버넌스: 사람 승인, 변경 관리, 프로필 검토

## 7. 자동 검증 결과

- 통과: None
- 실패 모듈: 없음
- 검증 루프: None회 (최대 2회)
- 중단 사유: 비용 한도 도달 — run budget $0.15 reached ($0.158885) before ExplanationJudgments
- 재시도 이력: 없음


## 8. 비용과 소요시간

아래 수치는 **이 문서를 만든 실행**에서 발생한 것입니다.

- 모델 호출 27회, 입력 323,546 tokens, 출력 38,999 tokens
- 비용 $0.158885 (약 222.4원, 1400.0원/$ 가정)
- 소요시간 481.8초
- 상한: {'max_calls': 60, 'max_usd': 0.15}
- 단계별: discover 13회 $0.0682, ExplanationJudgments 1회 $0.0213, EvidenceCardDrafts 1회 $0.0162, case_link 5회 $0.0143, PersonaUnitDrafts 1회 $0.0131, DisplayLabels 1회 $0.0108, DisplayVerdicts 1회 $0.0077, ClassifyAnswer 1회 $0.0054, persona_select 2회 $0.0015, vision 1회 $0.0003

## 9. 한계와 가정

- 이 검토는 공개된 광고성 화면을 대상으로 하며, 청약 단계 설명화면은 범위에 없습니다. 설명의무 기준은 준용해 품질 기준으로 적용했습니다.
- 자동 검증은 인용 근거의 존재와 모듈 간 모순만 확인합니다. 통과가 법률 준수를 보증하지 않습니다.
- 5 images in the selected html, 5 without alt text; text inside images is not measurable. Flagged by the model: none
- CSS background images and overlapping img bounds flag risky blocks; captured crops are checked by vision for E04/E05. Pseudo-elements and image-only text remain unmeasured.
- 가정: E02 says 8pt on A4. A web page has no paper size, so the node uses computed CSS px x 0.75 >= 8pt at the captured viewport.
- 가정: No threshold in the rubric. The node uses the WCAG 2.1 SC 1.4.3 AA ratio: 4.5:1 for normal text, 3.0:1 for large text (>= 24px, or >= 18.66px and weight >= 700). Text and background colors come from the snapshot (blended background when captured); Image-backed blocks are checked from saved rendered…
- 독자 맞춤 설명 1개 단위는 검사를 통과하지 못해 원문 문장으로 되돌렸습니다.
- 독자 맞춤 설명은 독자 프로필 nemotron:1c4fd4117b0440e6a65134c820e0bc37 vt1@ada0f5b(ai-drafted, 적용) 기준의 보조 설명이며, 원문을 대신하거나 독자의 자격·혜택·상환액을 판단하지 않습니다.
- 조사 공백 41건(claim_without_visible_condition, hidden_text, unexpanded_control)은 누락의 증거가 아니라 확인하지 못한 범위입니다.

## 10. 페이지 수집 agent 기록

- 상태: 조사 불충분, 중단 사유: no_viable_control
- 조사 범위(전 → 후): {'hidden_text_blocks': 81, 'visible_text_blocks': 51, 'candidate_controls': 3, 'open_gaps': 68} → {'hidden_text_blocks': 74, 'visible_text_blocks': 58, 'candidate_controls': 3, 'open_gaps': 40}
- `조사 불충분`은 누락의 증거가 아닙니다. 보이지 않은 조건은 위반이 아니라 조사 공백으로 남깁니다.

| 공백 | 종류 | 상태 | 내용 | 닫은 행동 |
|---|---|---|---|---|
| gap-1 | unexpanded_control | closed | 이용 예시 not yet expanded | interact expand #accordion1 (gap gap-1) |
| gap-2 | unexpanded_control | closed | 청구금액 미만 입금 시 적용 방식 not yet expanded | interact expand #accordion2 (gap gap-2) |
| gap-3 | unexpanded_control | closed | 금리인하요구권 안내 not yet expanded | interact expand #accordion3 (gap gap-3) |
| gap-4 | hidden_text | open | hidden text: '2026.09.29 13:30:17' |  |
| gap-5 | hidden_text | open | hidden text: '고객님은리볼빙 약정 고객이에요' |  |
| gap-6 | hidden_text | open | hidden text: '약정정보 및 이용현황은이용내역에서 확인해주세요.' |  |
| gap-7 | hidden_text | open | hidden text: '일부결제금액이월약정(리볼빙)이란?' |  |
| gap-8 | hidden_text | open | hidden text: '최소 결제 금액' |  |
| gap-9 | hidden_text | open | hidden text: '리볼빙 예상적용금액' |  |
| gap-10 | hidden_text | closed | hidden text: '매달 이용 금액 100만원, 약정결제비율 30%, 금리 연 17%인 고객의 사용 예시. 매달 약정결제금액 납' | interact expand #accordion1 (gap gap-1) |
| gap-11 | hidden_text | closed | hidden text: '[REWORK 26.03.16] 마크업 하나로 사용 및 위치이동 [S] [REWORK 26.03.16] 마크' | interact expand #accordion1 (gap gap-1) |
| gap-12 | hidden_text | closed | hidden text: '1,000,000원' | interact expand #accordion1 (gap gap-1) |
| gap-13 | hidden_text | closed | hidden text: '이번달 이용금액' | interact expand #accordion1 (gap gap-1) |
| gap-14 | hidden_text | closed | hidden text: '1,000,000원' | interact expand #accordion1 (gap gap-1) |
| gap-15 | hidden_text | closed | hidden text: '지난달 이월잔액' | interact expand #accordion1 (gap gap-1) |
| gap-16 | hidden_text | closed | hidden text: '이번 달 결제 금액' | interact expand #accordion1 (gap gap-1) |
| gap-17 | hidden_text | closed | hidden text: '300,000원' | interact expand #accordion1 (gap gap-1) |
| gap-18 | hidden_text | closed | hidden text: '300,000원' | interact expand #accordion1 (gap gap-1) |
| gap-19 | hidden_text | closed | hidden text: '700,000원' | interact expand #accordion1 (gap gap-1) |
| gap-20 | hidden_text | open | hidden text: '1,700,000원' |  |
| gap-21 | hidden_text | closed | hidden text: '700,000원' | interact expand #accordion1 (gap gap-1) |
| gap-22 | hidden_text | open | hidden text: '519,781원' |  |
| gap-23 | hidden_text | open | hidden text: '510,000원' |  |
| gap-24 | hidden_text | open | hidden text: '1,190,000원' |  |
| gap-25 | hidden_text | open | hidden text: '2,190,000원' |  |
| gap-26 | hidden_text | open | hidden text: '1,190,000원' |  |
| gap-27 | hidden_text | open | hidden text: '673,627원' |  |
| gap-28 | hidden_text | open | hidden text: '657,000원' |  |
| gap-29 | hidden_text | open | hidden text: '1,533,000원' |  |
| gap-30 | hidden_text | closed | hidden text: '이월한 금액뿐 아니라, 매달 카드값의 일부도 계속 이월되므로 상환해야 할 원금이 계속 늘어날 수 있습니다.' | interact expand #accordion1 (gap gap-1) |
| gap-31 | hidden_text | closed | hidden text: '결제일 당일 약정결제비율에 따라 청구된 금액 미만으로 입금되어도 다음과 같이 적용됩니다.' | interact expand #accordion2 (gap gap-2) |
| gap-32 | hidden_text | closed | hidden text: '최소결제금액 이상 입금된 경우' | interact expand #accordion2 (gap gap-2) |
| gap-33 | hidden_text | closed | hidden text: '미결제된 나머지 잔액은 자동으로 이월되어 연체 처리되지 않음 (이월된 금액은 다음달에 리볼빙 이자금액과 함께' | interact expand #accordion2 (gap gap-2) |
| gap-34 | hidden_text | closed | hidden text: '연체된 금액이 없으므로 결제일 이후 추가인출 없음' | interact expand #accordion2 (gap gap-2) |
| gap-35 | hidden_text | closed | hidden text: '최소결제금액 미만 입금되거나 입금금액이 없는 경우' | interact expand #accordion2 (gap gap-2) |
| gap-36 | hidden_text | closed | hidden text: '최소결제금액 외 미결제된 나머지 잔액은 자동으로 이월 (이월된 금액은 다음달에 리볼빙 이자금액과 함께 청구)' | interact expand #accordion2 (gap gap-2) |
| gap-37 | hidden_text | closed | hidden text: '최소결제금액 중 미납된 금액만 연체 처리되어 입금될 때까지 추가인출 됨 (미납된 연체금액은 입금될 때까지 연' | interact expand #accordion2 (gap gap-2) |
| gap-38 | hidden_text | closed | hidden text: '금리인하요구권이란?' | interact expand #accordion3 (gap gap-3) |
| gap-39 | hidden_text | closed | hidden text: '신한카드 금융서비스를 이용하는 회원이 취업, 승진, 소득 및 재산 증가 등 신용상태가 대출 시점 대비 개선된' | interact expand #accordion3 (gap gap-3) |
| gap-40 | hidden_text | closed | hidden text: '일부결제금액이월약정(리볼빙) 약정 회원' | interact expand #accordion3 (gap gap-3) |
| gap-41 | hidden_text | closed | hidden text: '약정 시점 대비 취업, 승진 등 기타 사유로 인한 신용상태가 개선된 경우' | interact expand #accordion3 (gap gap-3) |
| gap-42 | hidden_text | closed | hidden text: '신한카드 고객센터() 홈페이지 : 고객센터 > 카드상담·신청 > 기타안내·신청 > 금리인하요구권' | interact expand #accordion3 (gap gap-3) |
| gap-43 | hidden_text | closed | hidden text: '1544‑7000' | interact expand #accordion3 (gap gap-3) |
| gap-44 | hidden_text | closed | hidden text: '필요한 경우, 관련 사항에 대한 증빙을 요청할 수 있습니다.' | interact expand #accordion3 (gap gap-3) |
| gap-45 | hidden_text | open | hidden text: '금리 할인 쿠폰이 도착했어요!' |  |
| gap-46 | hidden_text | open | hidden text: '일부결제금액이월약정(리볼빙) 신청 대상이 아니에요.' |  |
| gap-47 | hidden_text | open | hidden text: '카드값을 일부만 내고, 나머지는다음달로 미루는 결제 방식이에요' |  |
| gap-48 | hidden_text | open | hidden text: '단, 최소 결제금액 이상으로는 꼭 납부해야 하고,다음달에 수수료도 같이 부과돼요.' |  |
| gap-49 | hidden_text | open | hidden text: '최소 결제 비율' |  |
| gap-50 | hidden_text | open | hidden text: '리볼빙 이용 금액이 연체되지 않기 위해 반드시 결제해야 하는 최소 금액의 비율이에요.' |  |
| gap-51 | hidden_text | open | hidden text: '리볼빙 약정 신청 시에 카드사에서 부여하고 10%~30% 중에 신용도에 따라 차등 적용돼요.' |  |
| gap-52 | hidden_text | open | hidden text: '약정 결제 비율' |  |
| gap-53 | hidden_text | open | hidden text: '리볼빙을 이용할 때 매달 갚아야 하는 금액의 비율을 말해요.' |  |
| gap-54 | hidden_text | open | hidden text: '예를 들어, 70%를 약정 결제 비율로 정하면, 매달 리볼빙 이용 금액의 70%만 결제하면 돼요.' |  |
| gap-55 | hidden_text | open | hidden text: '최소 결제 비율 이상~100% 이하 내에서 1% 단위로 고객님이 직접 설정 가능해요.' |  |
| gap-56 | hidden_text | open | hidden text: '리볼빙 이용 금액이 이월되는 경우 이월 기간에 대해 고객님에게 부과되는 수수료에요.' |  |
| gap-57 | hidden_text | open | hidden text: '이월 잔액 X 금리 X 경과 일수 / 365일(윤년 366일)' |  |
| gap-58 | hidden_text | open | hidden text: '리볼빙 약정 적용 방식에 따라 1개월 단위 또는 1년 단위로 약정할 수 있어요.' |  |
| gap-59 | hidden_text | open | hidden text: '일반 리볼빙: 1년~5년(1년 단위)' |  |
| gap-60 | hidden_text | open | hidden text: '선택형 리볼빙: 3개월~36개월(1개월 단위)' |  |
| gap-61 | hidden_text | open | hidden text: '약정 기간이 끝나기 전까지는 약정 결제 비율을 자유롭게 변경할 수 있어요.' |  |
| gap-62 | hidden_text | open | hidden text: '최소 결제 금액' |  |
| gap-63 | hidden_text | open | hidden text: '리볼빙을 이용할 때 연체되지 않기 위해 반드시 결제해야 하는 최소한의 금액이에요.' |  |
| gap-64 | hidden_text | open | hidden text: '리볼빙 이용 금액 X 최소 결제 비율과 50,000원 중 큰 금액이에요.' |  |
| gap-65 | hidden_text | open | hidden text: '리볼빙 적용 예상 금액' |  |
| gap-66 | hidden_text | open | hidden text: '고객님의 거래 내역 중 리볼빙 적용이 가능한 내역의 금액 합산이에요.' |  |
| gap-67 | hidden_text | open | hidden text: '리볼빙은 본인 한도 내 일시불 거래에 대해서만 적용 가능해요.' |  |
| gap-68 | hidden_text | open | hidden text: '최소 결제 비율 이상~100% 이하 내에서 1% 단위로고객님이 직접 설정 가능해요.' |  |
| gap-69 | unexpanded_control | open | button.shc-ico-btn.shc-tooltip-target not yet expanded |  |

| 턴 | 도구 | 인자 | 대상 공백 | 결과 |
|---|---|---|---|---|
| 1 | inspect_page | {} |  | - |
| 2 | interact | {"action": "expand", "selector": "#accordion1", "gap_id": "gap-1", "e… | gap-1 | 새 증거 |
| 2 | interact | {"action": "expand", "selector": "#accordion2", "gap_id": "gap-2", "e… | gap-2 | 새 증거 |
| 2 | interact | {"action": "expand", "selector": "#accordion3", "gap_id": "gap-3", "e… | gap-3 | 새 증거 |
| 3 | inspect_page | {} |  | - |
| 4 | probe_selector | {"selectors": ["div.shc-article", "div.shc-article h2", "div.fn-revol… |  | - |
| 5 | submit_rule | {"product_name": "일부결제금액이월약정(리볼빙)", "summary": "All on-page text desc… |  | - |
| 6 | submit_rule | {"product_name": "일부결제금액이월약정(리볼빙)", "summary": "All on-page text desc… |  | - |
| 7 | submit_rule | {"product_name": "일부결제금액이월약정(리볼빙)", "summary": "All on-page text desc… |  | - |
| 8 | inspect_page | {} |  | - |
| 9 | submit_rule | {"product_name": "일부결제금액이월약정(리볼빙)", "summary": "All on-page text desc… |  | - |
| 10 | submit_rule | {"product_name": "일부결제금액이월약정(리볼빙)", "summary": "All on-page text desc… |  | - |
| 11 | submit_rule | {"product_name": "일부결제금액이월약정(리볼빙)", "summary": "All on-page text desc… |  | - |
| 13 | submit_rule | {"product_name": "일부결제금액이월약정(리볼빙)", "summary": "All on-page text desc… |  | - |

## 11. 증거 카드와 조사 공백

- 상태: 완료, 카드 24건, 검증 탈락 0건
- 카드는 원문 인용과 출처(`dom-N`)가 코드로 재확인된 사실 단위이며, 법률 판단이 아닙니다.

| 카드 | 종류 | 인용 | 조건 | 예외 | 출처 | 가시성 |
|---|---|---|---|---|---|---|
| c1 | eligibility | 리볼빙 약정 고객이에요 |  |  | dom-1 | unresolved |
| c2 | condition | 약정 결제비율 10~100 % |  |  | dom-9 | default_visible |
| c3 | rate_claim | 금리 5.4~19.9% |  |  | dom-10 | default_visible |
| c4 | condition | 약정기간 3~60 개월 |  |  | dom-11 | default_visible |
| c5 | warning | 이월한 금액뿐 아니라, 매달 카드값의 일부도 계속 이월되므로 상환해야 할 원금이 계속 늘어날 수 있습니다. |  |  | dom-65 | revealed |
| c6 | condition | 미결제된 나머지 잔액은 자동으로 이월되어 연체 처리되지 않음 (이월된 금액은 다음달에 리볼빙 이자금액과 함께 청구) |  |  | dom-69 | revealed |
| c7 | warning | 최소결제금액 중 미납된 금액만 연체 처리되어 입금될 때까지 추가인출 됨 (미납된 연체금액은 입금될 때까지 연체 이자금액 발생) |  |  | dom-73 | revealed |
| c8 | fee_claim | 중도상환 수수료는 없습니다. |  |  | dom-91 | default_visible |
| c9 | rate_claim | 결제성 일부결제금액이월약정 평균 금리: 17.28% |  |  | dom-95 | default_visible |
| c10 | rate_claim | 연체금리는 “약정금리+최대 3%, 법정 최고금리(연 20%)이내"에서 적용됩니다. |  |  | dom-100 | default_visible |
| c11 | benefit_claim | 예를 들어, 70%를 약정 결제 비율로 정하면, 매달 리볼빙 이용 금액의 70%만 결제하면 돼요. |  |  | dom-118 | hidden |
| c12 | condition | 일반 리볼빙: 1년~5년(1년 단위) |  |  | dom-121 | image_only |
| c13 | condition | 선택형 리볼빙: 3개월~36개월(1개월 단위) |  |  | dom-122 | default_visible |
| c14 | condition | 리볼빙 이용 금액 X 최소 결제 비율과 50,000원 중 큰 금액이에요. |  |  | dom-124 | revealed |
| c15 | condition | 리볼빙은 본인 한도 내 일시불 거래에 대해서만 적용 가능해요. |  |  | dom-125 | image_only |
| c16 | condition | 리볼빙은 본인한도 내에서 이용한 결제금액 중 미리 약정한 약정(최소)결제비율 이상 결제하면, 나머지 금액은 다음달로 이월되는… |  |  | dom-132 | hidden |
| c17 | condition | 리볼빙 신규 약정은 고객님의 모든 카드에 적용되며, 카드/브랜드 단위로는 신청할 수 없습니다. |  |  | dom-135 | hidden |
| c18 | warning | 리볼빙을 해지하면 일부결제금액이월약정 잔액은 전액 일시청구 됩니다. |  |  | dom-161 | hidden |
| c19 | condition | 약정결제비율은 최소결제비율~100단위까지 1%단위로 지정할 수 있으며 청구금액을 결정합니다. |  |  | dom-171 | hidden |
| c20 | condition | 최소결제비율은 신용도에 따라 10% 이상으로 차등 적용되어 임의로 변경할 수 없으며 최소결제금액을 결정합니다. |  |  | dom-172 | hidden |
| c21 | condition | ③청구금액 = (① 약정 적용 금액 x 약정결제비율) + ② 약정 미적용 금액 |  |  | dom-186 | hidden |
| c22 | condition | ④최소결제금액 = (① 약정 적용 금액 x 최소결제비율) + ② 약정 미적용 금액 |  |  | dom-187 | hidden |
| c23 | condition | 단, (① 약정 적용 금액 x 최소결제비율)이 5만원 미만인 경우, 5만원으로 합니다. (’14년 12월 30일 이전 약정 … |  |  | dom-188 | hidden |
| c24 | fee_claim | 약정 적용 금액 중 단기카드대출 (현금서비스) 금액은 최초결제일에 결제될 때까지 단기카드대출 (현금서비스) 이자가 부과됩니다. |  |  | dom-196 | hidden |

| 공백 | 종류 | 상태 | 관련 카드 |
|---|---|---|---|
| gap-4 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-5 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-6 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-7 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-8 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-9 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-20 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-22 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-23 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-24 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-25 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-26 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-27 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-28 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-29 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-45 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-46 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-47 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-48 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-49 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-50 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-51 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-52 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-53 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-54 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-55 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-56 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-57 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-58 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-59 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-60 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-61 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-62 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-63 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-64 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-65 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-66 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-67 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-68 | hidden_text | open | c1, c11, c16, c17, c18, c19, c20, c21, c22, c23, c24 |
| gap-69 | unexpanded_control | open |  |
| - | claim_without_visible_condition | open | c3, c9, c10, c11 |

## 12. 참고 사례 (판정에 사용하지 않음)

- 아래 사례는 비슷한 표시 유형을 찾아 참고로만 연결한 것입니다. 이 검토의 적합·부적합 판정은 사례와 무관하게 루브릭과 페이지 인용으로만 정해졌습니다.
- 상태: 해당 사례 없음 (에이전트가 같은 패턴의 사례를 연결하지 않음), 후보 12건, 연결 agent(검색 8회, 읽기 3회, 중단 사유 finished), 사례 출처 db
- 연결은 agent가 제안하고, 코드가 페이지 인용과 사례 인용을 원문에서 다시 찾아 확인한 것만 남겼습니다.

(해당 항목 없음)

---

이 문서는 자동 검토 결과입니다(ai-generated). 게시 여부의 최종 판단은 컴플라이언스 담당자가 합니다.
