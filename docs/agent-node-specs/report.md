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
| the run budget ran out after collection | 판정 불가 | names the interrupted node |

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

The markdown is short on purpose (replaced 2026-09-30): it is what a requester is sent.
`domain/report/markdown.py` renders it; the other Report fields keep the detail.

Frontmatter first (`ai-generated: true`, `human-review: false`), so a generated report can never
be mistaken for a reviewed one. Then the page (product, verdict and publish decision, URL, types)
with header notes only where they explain the verdict: why a review stopped, an incomplete
collection, a failed verification, hidden text no control could reveal. Then four sections:

1. 표시방법 — every item, as its rubric question and legal basis (not its code), verdict, reason.
2. 설명의무 (원문) — explanation-duty twins (설명NN/FNN) read as one topic with the worse verdict;
   passes are a count, and only 부적합·판정 불가 topics are listed with question, basis and reason.
3. 쉬운말 초안 — the reader, how many units fell back to the original, and each explained line of
   the assembled draft in page order as 원문 → 쉬운말 (lines kept as they were are left out).
4. 쉬운말 초안의 설명의무 — the same table for the draft, then the meaning changes that are not
   merely informational.

The question is the asking sentence of the rubric `criterion`; the basis names each cited
document once (`rubric_sources.doc` through `knowledge.rubrics.DOC_NAMES`) with its first article
and a count of the rest. Both come from `rubric_labels(db_path)`; with no DB the code stands in.

Cost, limits and assumptions, the action list, findings, agent runs, evidence cards and reference
links are not in the markdown. They stay in `report.cost`, `report.limits`, `report.actions`,
`report.findings` and `report.summary` (the API returns them), and the markdown's last line says
so. Unreachable hidden text is both a header note and a `limits` entry.

A `BudgetError` raised after collection no longer ends the thread without a report:
`graph.build.invoke_to_report` (used by the CLI and the API worker) builds the report from the
last checkpoint, with `summary.interrupted_at` naming the node that did not finish, and writes it
back as `end_report`. `summary.agent_runs` records, for the page agent, the case-linking agent
and the reader selection, whether the model loop ran (`agent`) or how the step was settled
without it (`reuse`, `skipped`, `default`, ...), with turns, tool calls and stop reason (audit
2026-09-29, R2, R5).

Collection comes first in the status: a page with no collected html reads `수집 실패` or `조사
불충분`, never a classification problem, and an open evidence gap keeps a clean run from reading
`검토 완료`. A checkpoint written before the persona explanation (`plain_language`) renders its
accepted blocks as the draft.

`report.limits` exists to stop the report from overclaiming: it repeats that the verification
only checked citation validity and cross-module contradictions, and carries the display node's
own stated assumptions (px→pt, the contrast threshold) plus the unmeasurable-image limits.

## Why the retry policy is passed in

`build_report` takes `stop` — the reason the run ended where it did — rather than importing
`graph/retry.py`. The import direction in [../README.md](../README.md#architecture) is `domain → graph`, so the graph layer
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

## One finding per explanation-duty topic

The F group of `card_guardrail_rubric` and the 설명의무 group of `plain_service_rubric` state
the same duties on two code axes (`core/duty_codes.DUTY_TWINS`: F01–F19 ↔ 설명01–19, F21 ↔ 설명27,
F22 ↔ 설명28; F20 has no twin). Both stay judged so each citation survives, but `_findings`
merges a code and its twin into one row (`설명07/F07`) when they have the same verdict on the
same side, so the action list names each duty once. Twins with different verdicts stay separate.
`summary.duty_topics_violated_original` counts distinct topics; `duty_violations_original` still
counts rows. The §5 table keeps every row, ordered so twins sit together (audit P1-7).

