---
ai-generated: true
human-review: false
created: 2026-09-27
---

# report

`end_report` assembles the one document a compliance reviewer reads. It is the end of the graph
and the only place the three modules' answers appear together.

## It adds no judgment

Every verdict in the report was decided by a module. What the report decides is only what the
reviewer has to do about them, and the mapping is mechanical:

| Input | `status` | `decision` |
|---|---|---|
| `classification.product_type` is `범위 밖` | 검토 대상 아님 | — |
| `classification.product_type` is `판정 불가` or missing | 판정 불가 | — |
| verification passed, no 부적합, no 판정 불가 | 검토 완료 | 담당자 확인 후 쉬운말 게시 가능 |
| verification passed, but items are 부적합 | 사람 검토 필요 | 쉬운말 자동 게시 불가 — 원문 유지 |
| verification failed after the retries | 사람 검토 필요 | 쉬운말 자동 게시 불가 — 원문 유지 |

A `판정 불가` item is a task, never a pass. `findings` collects every row a person must look at:
`부적합` and `판정 불가` from both checks, every fidelity difference, and every plain-language
block that fell back to its original wording.

## 위반 or 권고 미충족

A `부적합` is not always a breach of law, and the report says which kind it is (`severity`,
`basis` on each finding). The rubric's `binding` field and the page type decide it, in code
(`domain/report/build.py:severity`):

| Finding | Reading | Why |
|---|---|---|
| Advertising rule (A–C groups, `binding` 법령) on a public product page | 위반(법령) | A public page is an advertisement under 금소법 제22조; the rule binds it directly. |
| Display rule (E group, `binding` 협회 자율규제) | 위반(협회 자율규제) | The association's advertising rules bind card-company ads directly. |
| Explanation-duty item on a 상품광고/업무광고 page | 권고 미충족(설명의무 준용) | 제19조 arises when a contract is solicited; on an ad page its items are applied by analogy. |
| Any item whose binding is 금융위 가이드라인, 참고 기준 or 자체 설계 | 권고 미충족 | Guidance never makes a breach. |
| Binding unknown (DB missing) | 위반(구속력 미상) | The stricter reading is kept. |

The publish decision does not change with the reading: any `부적합` still keeps the plain-language
draft unpublished. The reading changes what the reviewer is told, not what the tool lets through.

## Sections of the markdown

Frontmatter first (`ai-generated: true`, `human-review: false`), so a generated report can never
be mistaken for a reviewed one. Then: 담당자 조치 목록, 검토 요약, 확인이 필요한 항목, 표시방법
상세, 설명의무 상세(원문·쉬운말·의미 차이 한 줄에), 쉬운말 변환 결과와 용어 풀이, 자동 검증 결과,
비용과 소요시간, 한계와 가정.

Two of those sections exist to stop the report from overclaiming. 자동 검증 결과 repeats that the
verification only checked citation validity and cross-module contradictions, and 한계와 가정
carries the display node's own stated assumptions (px→pt, the contrast threshold) plus the
unmeasurable-image limits, on every run.

## Why the retry policy is passed in

`build_report` takes `stop` — the reason the run ended where it did — rather than importing
`graph/retry.py`. The import direction in `docs/design.md` is `domain → graph`, so the graph layer
owns the loop policy and hands the report its account of it. That keeps the report usable from a
context with no graph at all, which is how `tests/domain/report/test_report_build.py` drives it.

## Cost

`report.cost` is the run meter's summary (`core/usage.py`): calls, tokens per step, derived USD and
KRW, elapsed seconds, and the caps that were in force, with a line per step. The CLI prints the
same line, so a run's cost is visible without opening the report.

Rebuilding only the report from a checkpoint (`rerun --from-node end_report`) makes no model call.
Until 2026-09-28 that printed the rebuild's own zero in place of what the review cost; `end_report`
now passes the cost already on the thread's report, and a rebuild that made no call carries it
forward and says so (`carried_forward`). A run that did call the model always reports its own
cost.
