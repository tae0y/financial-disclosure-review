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
| verification passed, no 부적합, no 판정 불가 | 검토 완료 | 담당자 확인 후 쉬운말 개요 게시 가능 |
| verification passed, but items are 부적합 | 사람 검토 필요 | 쉬운말 개요 자동 게시 불가 — 원문만 게시 |
| verification failed after the retries | 사람 검토 필요 | 쉬운말 개요 자동 게시 불가 — 원문만 게시 |
| the run budget ran out after collection | 판정 불가 | names the interrupted node |

A `판정 불가` item is a task, never a pass. `findings` collects every row a person must look at:
`부적합` and `판정 불가` from both checks, every fidelity difference, and an overview held back
by its code checks.

## 위반 or 권고 미충족

A `부적합` is not always a breach of law, and the report says which kind it is (`severity`,
`basis` on each finding). The rubric's `binding` field decides it, in code
(`domain/report/build.py:severity`):

| Finding | Reading | Why |
|---|---|---|
| Advertising rule (A–C groups, `binding` 법령) on a public product page | 위반(법령) | A public page is an advertisement under 금소법 제22조; the rule binds it directly. |
| Display rule (E group, `binding` 협회 자율규제) | 위반(협회 자율규제) | The association's advertising rules bind card-company ads directly. |
| Any item whose binding is 금융위 가이드라인, 참고 기준 or 자체 설계 | 권고 미충족 | Guidance never makes a breach. |
| Binding unknown (DB missing) | 위반(구속력 미상) | The stricter reading is kept. |

Explanation-duty items (금소법 제19조) are not judged at all: they bind the contract-stage product
document, not an ad, and are listed in `ad_disclosure_check.deferred` for the reviewer
([ADR-006](../architecture-decisions/adr-006-ad-disclosure-instead-of-explanation-duty.md)). The
report adds one action naming their codes and a markdown section with their questions.

The publish decision does not change with the reading: any `부적합` still keeps the plain-language
overview unpublished. The reading changes what the reviewer is told, not what the tool lets through.

## Sections of the markdown

The markdown is short on purpose (replaced, then compacted, 2026-09-30): it is what a requester
is sent.
`domain/report/markdown.py` renders it; the other Report fields keep the detail.

Frontmatter first (`ai-generated: true`, `human-review: false`), so a generated report can never
be mistaken for a reviewed one. Then the page (product, verdict and publish decision, URL, types)
with header notes only where they explain the verdict: why a review stopped, an incomplete
collection, a failed verification, hidden text no control could reveal. Then three sections:

1. 확인할 항목 — one line of pass counts (표시방법, 광고 의무표시, 쉬운말 개요), then a single table
   of every open item (부적합 first, then 판정 불가) from the display check and the page-side
   disclosure check: area, rubric question, short basis, verdict, reason (80 characters).
2. 쉬운말 개요 — the reader as an age band and financial familiarity only (never the dataset
   persona's name or story), the paragraphs as shown or why none is shown, then "개요 확인 사항":
   the overview's open items and the differences that are not merely informational.
3. 상품설명서에서 확인할 설명의무 (n개) — one paragraph of topics (the question without its asking
   tail and asides); omitted when there are none.

The question is the asking sentence of the rubric `criterion`; the short basis is its first cited
document and article with a count of the others (`rubric_labels`, `knowledge.rubrics.DOC_NAMES`). Both come from `rubric_labels(db_path)`; with no DB the code stands in.

Cost, limits and assumptions, the action list, findings, agent runs and evidence cards are not in
the markdown. They stay in `report.cost`, `report.limits`, `report.actions`,
`report.findings` and `report.summary` (the API returns them), and the markdown's last line says
so. Unreachable hidden text is both a header note and a `limits` entry.

A `BudgetError` raised after collection no longer ends the thread without a report:
`graph.build.invoke_to_report` (used by the CLI and the API worker) builds the report from the
last checkpoint, with `summary.interrupted_at` naming the node that did not finish, and writes it
back as `end_report`. `summary.agent_runs` records, for the page agent (`discovery`) and the
reader selection (`reader_selection`), whether the model loop ran (`agent`) or how the step was
settled without it (`reuse`, `none`, `default`, ...), with turns, tool calls and stop reason
(audit 2026-09-29, R2, R5).

Collection comes first in the status: a page with no collected html reads `수집 실패` or `조사
불충분`, never a classification problem, and an open evidence gap keeps a clean run from reading
`검토 완료`. A checkpoint written before 2026-09-30 (explanation units, `explanation_duty_check`)
still produces a report, without an overview or disclosure rows.

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
