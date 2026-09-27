---
ai-generated: true
human-review: false
created: 2026-09-27
---

# 노트북에서 src 패키지로의 전환 기록

`notebooks/review.ipynb` 한 파일에 있던 검토 파이프라인을 `src/financial_disclosure_review/`
패키지로 옮긴 작업의 기록입니다. 설계 판단의 근거는 `docs/design.md`의 `Package layout` 절과
`localdocs/adr/adr-001-notebook-to-src.md`(로컬 전용)에 있고, 이 문서는 "무엇이 어디로 갔고
무엇이 달라졌는가"를 남깁니다.

## 배경

노트북은 탐색 단계에 맞는 도구였습니다. 셀 하나를 살아 있는 체크포인트에 다시 실행할 수 있었고,
파일 전체를 위에서 아래로 돌리는 것이 그대로 검증이었습니다. 2026-09-27 시점에 정의가 7개 섹션
약 2,900줄로 늘면서 세 가지 비용이 분명해졌습니다.

- 모든 정의가 한 이름공간에 있어 모듈 경계가 없었습니다. 표시방법 헬퍼가 상품페이지 세션을
  직접 만지는 것을 막을 방법도, 어떤 헬퍼가 어느 모듈 소유인지 적어 둘 자리도 없었습니다.
- 검증이 assert 셀 하나였습니다. 노트북 전체를 돌릴 때만 실행되고, 비용 기준으로 골라 실행할
  수 없고, 무료 검사만 CI에 걸 수도 없었습니다.
- `ralph/PROMPT_*.md`가 작업 단위를 셀 ID로 지목하고 있어 셀을 나눌 때마다 깨졌습니다.

## 무엇이 어디로 갔는가

State 키 하나에 폴더 하나이고, 그 폴더들은 모두 `domain/` 아래에 모여 있습니다(2026-09-27
영태 님 결정). 노트북 섹션과의 대응은 다음과 같습니다.

| 노트북 | 옮긴 자리 |
|---|---|
| 2. 데이터 모델 (State, Context, 툴 스키마) | `core/state.py`, `core/context.py`, `domain/product_page/tools.py` |
| 3. 헬퍼 (문자열, 색상, HTML, 스냅숏, 루브릭) | `core/text.py`, `core/color.py`, `core/threads.py`, `domain/product_page/html.py`, `domain/product_page/session.py`, `knowledge/rubrics.py` |
| 4. 비즈니스 로직 (세션, 툴, 규칙, 분류, 표시방법) | `domain/product_page/`, `domain/classification/`, `domain/display_check/` |
| 4. 비즈니스 로직 (쉬운말 생성, 설명의무 판정, 답변 검증) | `domain/plain_language/`, `domain/explanation_duty_check/`, `domain/verification/` |
| 5~6. 노드와 그래프 | `graph/nodes.py`, `graph/routes.py`, `graph/build.py` |
| 7. 실행 (DB 구축, 실행 셀, 재실행 셀) | `knowledge/build.py`, `__main__.py` |
| 각 확인 셀, fixture | `tests/` |
| `!uv sync`, mermaid 렌더, EXPERIMENT 스파이크 2개 | 버렸습니다 |

`domain/` 아래 폴더는 `product_page`, `classification`, `display_check`, `plain_language`,
`explanation_duty_check`, `verification`, `report` 일곱 개입니다. `tests/`도 같은 모양으로
`tests/domain/<이름>/`을 씁니다.

import 방향은 `core → llm → knowledge → 도메인 → graph → __main__` 한 방향입니다. 도메인은
서로를 import하지 않고, 데이터는 State에서만 만납니다. `langgraph`와 `State`는 `graph/`와
`__main__.py`에만 등장합니다. 각 도메인은 `__init__.py`에서 진입 함수 하나만 내보내고, 그
함수는 State 전체가 아니라 필요한 값만 받습니다.

전환 시점에 `report`와 `graph/retry.py`는 빈 dict를 돌려주는 스텁이었고, 노드는 그때부터 그
스텁을 호출했습니다. 그래프는 전환 내내 END까지 실행됐습니다. 두 스텁은 2026-09-27에 실제
구현으로 채웠습니다(검토 보고서와 2회 재시도·에스컬레이션 정책). 지금 남은 스텁은 없습니다 —
`docs/report.md`, `docs/operations.md` 참조.

## 옮기기 외에 달라진 것

로직은 그대로 옮겼습니다. 동작이 같은 선에서 세 가지를 분리했습니다.

| 분리 | 이유 |
|---|---|
| `discover`의 모델 턴 → `llm/client.py`의 `ToolChat` | 결정 5. `langchain` 메시지 객체가 도메인에 남지 않도록 턴 전체를 호출 장치로 옮겼습니다. |
| 비전 호출의 `OpenAI(...).responses.create` → `llm/client.py`의 `ask_images` | 같은 근거입니다. 프롬프트 조립과 응답 검증은 `display_check/judge.py`에 남습니다. |
| 색상 헬퍼 → `core/color.py` | `capture_visual_samples`가 `contrast_ratio`를 쓰게 되면서 `product_page`와 `display_check` 두 도메인이 공유하게 되었습니다. |
| `html_lines`, `BLOCK_TAGS` → `core/text.py` | `plain_blocks`가 `html_lines`를 쓰게 되면서 `plain_language`와 `display_check`가 공유합니다. 규칙 6. `html_text_runs`는 여전히 `display_check`만 쓰므로 그대로 남았습니다. |
| `VIOLATION_KEYS` → `core/display_codes.py` | `verify`가 표시방법 측정값과 판정의 모순을 다시 확인하면서 `display_check`와 `verification`이 공유합니다. 규칙 6이자 규칙 3(도메인 간 import 금지)입니다. |
| 2회 재시도 루프 → `llm/client.py`의 `call_ask` | 규칙 4(재시도는 `llm/`의 일). 노트북은 `call_model`이 전역 `ask`만 호출해 가짜 ask를 넣을 수 없어 `generate_plain`에 루프를 다시 썼지만, `call_ask`는 호출 함수를 인자로 받으므로 그 이유가 없어졌습니다. `generate_plain`의 되돌리기 분기는 `salvage`로 그대로 옮겼고 예외 메시지도 같습니다. |
| `judge_explanation`의 원문 판정 블록 → `judge_original_side` | 노트북에서 이미 함수였던 `judge_plain_side`와 대칭이 되도록 같은 모듈의 함수로 꺼냈습니다. 인자는 클로저가 잡던 값 그대로입니다. |

그 밖에 코드 내용이 아니라 형식만 바뀐 것이 둘 있습니다.

- 100자를 넘는 줄을 다시 감았습니다. 문자열 이어붙이기를 건드린 곳은 합쳐진 문자열이 같은지
  확인한 뒤 바꿨습니다. 프롬프트 파일(`*/prompts.py`, `product_page/discover.py`)은 E501
  검사에서 제외했습니다. 줄을 다시 감으면 모델이 읽는 문자열 자체가 바뀝니다.
- pyright가 이 코드를 처음 검사하면서 오류 40건이 나왔고, 좁은 범위의 타입 표기로 해결했습니다
  (도메인 진입 함수 인자를 `Mapping[str, Any]`로, tuple 폭 명시, `RunnableConfig` 표기 등).
  남은 경고 약 1,070건은 노트북에서 온 `dict` 무인자 표기에서 나오며, 각 모듈을 다시 쓸 때
  조이면 됩니다.

## 검증 결과

무료 검사는 `uv run pytest` 168건이 약 4초에 통과하고, `ruff check`와 `pyright`도 깨끗합니다
(pyright 오류 0건). 브라우저 테스트는 마커 없이 기본 실행에 포함됩니다. 로컬 HTML 픽스처를
`set_content`로 열기 때문에 네트워크에 나가지 않습니다.

유료·네트워크 검사는 `use_llm`, `use_network` 마커로 기본 실행에서 빠집니다.

```bash
uv run pytest                                # 무료 검사
uv run pytest -m "use_llm or use_network"    # 실제 모델 호출과 외부 사이트
```

전환 동등성은 2026-09-27에 샘플 URL 2건을 실제 그래프로 돌려 확인했습니다. 롯데카드
Las Vegas와 신한카드 Hi-Point Plan 모두 END까지 도달했고, 두 건 다 `신용카드`/`상품광고`로
판정되어 전환 전 기록(S-13)과 일치했습니다. 비교 대상은 `product_page.product`,
`classification`, `display_check`의 키 구조입니다. LLM 판정 값은 실행마다 달라질 수 있으므로
비교에서 제외했습니다. 롯데 건에서는 E07 판정이 검증에 한 번 걸린 뒤 재시도로 통과해,
"숨김 판정은 사용자 조작으로 드러난 블록만 근거로 삼는다"는 가드가 실제로 작동함을 확인했습니다.

## 잃은 것과 남은 일

노트북의 편의는 사라졌습니다. 체크포인트를 즉석에서 들여다볼 커널이 없고, 그래프를 인라인으로
그려 보는 mermaid 렌더도 없습니다. 한 노드만 다시 돌리는 일은 CLI가 맡습니다.

```bash
uv run python -m financial_disclosure_review rerun --thread review-260927-101500 \
    --from-node judge_display_method
```

남은 일은 두 가지입니다.

- `notebooks/`가 아직 남아 있습니다. 2026-09-27 두 번째 묶음으로 `generate_plain_lang`,
  `judge_explanation_duty`, `verify_answer`와 각 확인 셀까지 옮겼으므로, 노트북에 src로
  가지 않은 코드는 이제 없습니다(`!uv sync`, mermaid 렌더, EXPERIMENT 스파이크 2개는 계획대로
  버렸습니다). 삭제는 영태 님 확인을 받은 뒤에 합니다. 전환 직전 상태는 커밋 `3fa6cc0`에
  남아 있습니다.
- `ralph/PROMPT_*.md`가 여전히 셀 ID를 참조합니다. 보관할지, src 기준으로 갱신할지, 삭제할지
  정해야 합니다.

## 두 번째 묶음에서 새로 만든 검증 픽스처

`generate_plain`과 `judge_explanation`은 루브릭 DB를 읽습니다. 노트북 확인 셀은 실제
`data/reference.sqlite`를 읽었지만, 테스트는 저장소 밖 원본에 의존하지 않아야 하므로
`tests/fixtures/rubric/`의 작은 루브릭을 늘렸습니다.

| 파일 | 늘린 항목 | 왜 |
|---|---|---|
| `card_guardrail_rubric.yaml` | `F01`, `F03`, `F19` | 설명의무 F군의 세 경로: 범위 안, `applies_to` 불일치, 신청·가입·발급 화면 전용 조건 |
| `plain_service_rubric.yaml` | 설명의무 `설명01`·`설명02`·`설명03`·`설명05`·`설명10`·`설명19`, 쉬운말서비스 `쉬운말01`·`쉬운말02`·`쉬운말08`·`쉬운말11`·`쉬운말13` | 설명의무는 위 세 경로에 "모델이 조건을 판단해야 하는 항목"을 더한 네 경로, 쉬운말서비스는 `plain_items_report`의 네 분기(`쉬운말01` 특례, 용어 코드, 범위 밖, 오류 표지 대조)와 `plain_scope` 제외 |

`설명01`의 `applies_to`에 `신용카드`를 넣었습니다(원래 픽스처는 `리볼빙`만). 확인 시나리오가
신용카드 페이지를 쓰기 때문이고, 실제 루브릭의 `설명01`도 신용카드를 포함합니다.
