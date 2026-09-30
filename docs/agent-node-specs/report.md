---
ai-generated: true
human-review: false
created: 2026-09-27
updated: 2026-09-30
---

# Report (`end_report`)

This page describes how `end_report` assembles the one document a compliance reviewer reads.

It is the last node and the only place every module's answers appear together. It adds no judgment: every verdict comes from a module, and the report only decides what the reviewer has to do about them.

## Status and publish decision

The mapping is mechanical.

| Input | `status` | `decision` |
|---|---|---|
| `product_type` is `범위 밖` | 검토 대상 아님 | — |
| `product_type` is `판정 불가` or missing | 판정 불가 | — |
| verification passed, no `부적합`, no `판정 불가` | 검토 완료 | 담당자 확인 후 쉬운말 확인 권고 게시 가능 |
| verification passed, but items are `부적합` | 사람 검토 필요 | 쉬운말 확인 권고 자동 게시 불가 — 원문만 게시 |
| verification failed after the retries | 사람 검토 필요 | 쉬운말 확인 권고 자동 게시 불가 — 원문만 게시 |
| the run budget ran out after collection | 판정 불가 | names the interrupted node |

Collection comes first: a page with no collected HTML reads `수집 실패` or `조사 불충분`, and an open evidence gap keeps a clean run from reading `검토 완료`. A `판정 불가` item is a reviewer task, never a pass.

## 위반 or 권고 미충족

A `부적합` is not always a breach of law. The rubric's `binding` field decides the reading, in code:

| Finding | Reading | Why |
|---|---|---|
| Ad rule (A–C groups, binding 법령) | 위반(법령) | A public product page is an advertisement under 금소법 제22조. |
| Display rule (E group, binding 협회 자율규제) | 위반(협회 자율규제) | The association's ad rules bind card-company ads directly. |
| Binding 금융위 가이드라인, 참고 기준 or 자체 설계 | 권고 미충족 | Guidance never makes a breach. |
| Binding unknown (DB missing) | 위반(구속력 미상) | The stricter reading is kept. |

The reading changes what the reviewer is told, not the publish decision: any `부적합` keeps the advice unpublished.

## The markdown

The markdown is short because it is what a requester receives. It opens with frontmatter (`ai-generated: true`, `human-review: false`) so it can never be mistaken for a reviewed document, then the product, verdict, publish decision, URL and types, with header notes only where they explain the verdict. Three sections follow:

1. **확인할 항목** — pass counts, then one table of every open display and disclosure item, `부적합` before `판정 불가`, with the rubric question, a short legal basis and a reason.
1. **쉬운말 확인 권고** — the reader as an age band and financial familiarity only, then the advice or why none is shown.
1. **상품설명서에서 확인할 설명의무** — the deferred 설명의무 topics, with the items the advice recommends starred (★).

Cost, limits, the action list, findings, agent runs and evidence cards stay in the structured fields (`report.cost`, `report.limits`, `report.actions`, `report.findings`, `report.summary`), which the API returns.

`report.limits` keeps the report from overclaiming: it states that verification checked only citation validity and cross-module consistency, and carries the display check's assumptions (px→pt, contrast threshold) and the unmeasurable-image limits.

`summary.agent_runs` records, for the page agent and the reader selection, whether the model loop ran or how the step was settled without it, with turns, tool calls and stop reason.

## Budget interruption and reruns

When the call or cost cap is hit after collection, `invoke_to_report` builds the report from the last checkpoint, with `summary.interrupted_at` naming the node that did not finish. The CLI and the API worker both use it, so every collected run ends in a report.

`report.cost` is the run meter's summary: calls, tokens per step, USD and KRW, elapsed time, and the caps in force. Rebuilding only the report (`rerun --from-node end_report`) makes no model call and carries the original cost forward (`carried_forward`).

`build_report` receives the stop reason from the graph instead of importing the retry policy, so the report can be built and tested without a graph ([layers](../architecture.md#layers)).

Tests: `tests/domain/report/`.
