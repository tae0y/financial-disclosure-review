---
ai-generated: true
human-review: false
---

# 금융상품 판매화면 검토 결과

- 판정: **판정 불가**
- 조치 방침: 상품 유형을 확정하지 못해 이후 검토를 진행하지 않았습니다.
- 대상 화면: https://www.hyundaicard.com/cpf/ll/CPFLL0101_01.hc
- 상품명: 장기카드대출(카드론)
- 상품유형/화면유형: 판정 불가 / (해당 없음)
- 분류 근거: 판정 근거 부족: single_product_quote가 페이지의 보이는 텍스트에 없음
- 페이지 수집: 조사 불충분 (submitted_with_gaps)
- 에이전트 실행: 페이지 탐색 agent 13턴(submitted_with_gaps) · 사례 연결 실행 안 됨 · 독자 선택 실행 안 됨

## 1. 담당자 조치 목록

1. 페이지 수집 조사 불충분(submitted_with_gaps): 열린 조사 공백 4건을 사람이 화면에서 확인
2. 사람이 상품 유형을 확정한 뒤 재실행
3. 분류 사유: 판정 근거 부족: single_product_quote가 페이지의 보이는 텍스트에 없음

## 2. 검토 요약

| 검토 영역 | 검토 항목 | 위반·반려 | 판정 불가·차이 |
|---|---|---|---|
| 표시방법 | 0 | 0 | 0 |
| 설명의무(원문) | 0/0 | 0 | 0 |
| 설명의무(독자 맞춤 설명) | 0/0 | 0 | 0 |
| 독자 맞춤 설명 | 0 | 0 | 0 |

## 3. 확인이 필요한 항목

(해당 항목 없음)

## 4. 표시방법 검토 상세

(해당 항목 없음)

## 5. 설명의무 검토 상세 (원문 대비 독자 맞춤 설명)

(해당 항목 없음)

- F01–F19·F21·F22는 같은 의무를 담은 설명 코드(설명01–19·27·28)와 한 주제입니다. 표에는 둘 다 남기고, 조치 목록에서는 같은 판정이면 한 번만 셉니다.

## 6. 독자 맞춤 설명 결과

(해당 항목 없음)

## 7. 자동 검증 결과

- 통과: None
- 실패 모듈: 없음
- 검증 루프: None회 (최대 2회)
- 중단 사유: 조치 가능한 피드백 없음 — 실패 사유에 구체적인 수정 요청이 없어 재시도하지 않았습니다.
- 재시도 이력: 없음


## 8. 비용과 소요시간

아래 수치는 **이 문서를 만든 실행**에서 발생한 것입니다.

- 모델 호출 15회, 입력 325,473 tokens, 출력 7,517 tokens
- 비용 $0.096402 (약 135.0원, 1400.0원/$ 가정)
- 소요시간 170.7초
- 상한: {'max_calls': 60, 'max_usd': 0.15}
- 단계별: discover 13회 $0.0709, ClassifyAnswer 2회 $0.0255

## 9. 한계와 가정

- 이 검토는 공개된 광고성 화면을 대상으로 하며, 청약 단계 설명화면은 범위에 없습니다. 설명의무 기준은 준용해 품질 기준으로 적용했습니다.
- 자동 검증은 인용 근거의 존재와 모듈 간 모순만 확인합니다. 통과가 법률 준수를 보증하지 않습니다.

## 10. 페이지 수집 agent 기록

- 상태: 조사 불충분, 중단 사유: submitted_with_gaps
- 조사 범위(전 → 후): {'hidden_text_blocks': 4, 'visible_text_blocks': 139, 'candidate_controls': 4, 'open_gaps': 8} → {'hidden_text_blocks': 0, 'visible_text_blocks': 0, 'candidate_controls': 0, 'open_gaps': 4}
- `조사 불충분`은 누락의 증거가 아닙니다. 보이지 않은 조건은 위반이 아니라 조사 공백으로 남깁니다.

| 공백 | 종류 | 상태 | 내용 | 닫은 행동 |
|---|---|---|---|---|
| gap-1 | unexpanded_control | open | 금융 상세보기 팝업 열기 not yet expanded |  |
| gap-2 | unexpanded_control | open | 일부결제금액이월약정(리볼빙) 자세히 보기 not yet expanded |  |
| gap-3 | unexpanded_control | open | 알기 쉽게 확인하는 신용카드 관련 피싱사기 예방법 not yet expanded |  |
| gap-4 | unexpanded_control | open | 금융 계산기 not yet expanded |  |
| gap-5 | hidden_text | closed | hidden text: '단기카드대출로 카드대금을 낼 수 있어요' | interact expand #btnRevolvinginfo (gap gap-1) |
| gap-6 | hidden_text | closed | hidden text: '일부결제금액이월약정' | interact expand #btnRevolvinginfo (gap gap-1) |
| gap-7 | hidden_text | closed | hidden text: '최근 검색어가 없습니다.' | interact expand #btnRevolvinginfo (gap gap-1) |
| gap-8 | hidden_text | closed | hidden text: '로그인 접속종료 예정 팝업 열기' | interact expand #btnRevolvinginfo (gap gap-1) |

| 턴 | 도구 | 인자 | 대상 공백 | 결과 |
|---|---|---|---|---|
| 1 | inspect_page | {} |  | - |
| 2 | interact | {"action": "expand", "selector": "#btnRevolvinginfo", "gap_id": "gap-… | gap-1 | 새 증거 |
| 3 | inspect_page | {} |  | - |
| 4 | submit_rule | {"product_name": "장기카드대출(카드론)", "summary": "Selectors that capture al… |  | - |
| 5 | probe_selector | {"selectors": ["#llCmsContent", "div.layer_wrap.w996", "ul.bul_list",… |  | - |
| 6 | submit_rule | {"product_name": "장기카드대출(카드론)", "summary": "Selectors that capture al… |  | - |
| 7 | submit_rule | {"product_name": "장기카드대출(카드론)", "summary": "Selectors that capture al… |  | - |
| 8 | submit_rule | {"product_name": "장기카드대출(카드론)", "summary": "Selectors that capture al… |  | - |
| 9 | interact | {"action": "expand", "selector": "a.p2_b.fc_m_link", "gap_id": "gap-2… | gap-2 | 거부: apply/login/submit/download wording; navigation l… |
| 10 | inspect_page | {} |  | - |
| 12 | submit_rule | {"product_name": "장기카드대출(카드론)", "summary": "Selectors capturing all t… |  | - |
| 13 | submit_rule | {"product_name": "장기카드대출(카드론)", "summary": "Selectors capturing all t… |  | - |

---

이 문서는 자동 검토 결과입니다(ai-generated). 게시 여부의 최종 판단은 컴플라이언스 담당자가 합니다.
