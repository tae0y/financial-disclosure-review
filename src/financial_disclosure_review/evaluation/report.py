"""Rendering an evaluation run as the markdown a reader can check the numbers in."""

from typing import Any


def _table(header: list[str], rows: list[list[Any]]) -> list[str]:
    if not rows:
        return ["(케이스 없음)", ""]
    return [
        "| " + " | ".join(header) + " |",
        "|" + "|".join(["---"] * len(header)) + "|",
        *[
            "| " + " | ".join(str(cell).replace("|", "\\|") for cell in row) + " |"
            for row in rows
        ],
        "",
    ]


def _pct(value: float | None) -> str:
    return "-" if value is None else f"{value * 100:.1f}%"


def render(run: dict) -> str:
    lines = [
        "---",
        "ai-generated: true",
        "human-review: false",
        "---",
        "",
        "# 검증 결과 — 금융상품 판매화면 검토 에이전트",
        "",
        f"- 실행 시각: {run['generated_at']}",
        f"- 모델: {run['model']}",
        f"- 실행 모드: {run['mode']} (`replay`는 녹음된 응답 재생으로 비용 0)",
        f"- 카세트: {run['cassette']}",
        f"- 모델 호출 {run['cost']['calls']}회, 입력 {run['cost']['input_tokens']:,} tokens,"
        f" 출력 {run['cost']['output_tokens']:,} tokens,"
        f" ${run['cost']['usd']} (약 {run['cost']['krw']}원)",
        f"- 소요시간 {run['cost']['elapsed_seconds']}초",
        "",
        "## 요약",
        "",
    ]
    summary_rows = []
    for entry in run["suites"]:
        name, metrics = entry["result"]["suite"], entry["metrics"]
        if name == "classification":
            summary_rows.append(
                [
                    name,
                    f"{metrics['correct']}/{metrics['cases']}",
                    f"정확도 {_pct(metrics['accuracy'])}",
                    f"오분류: {metrics['wrong'] or '없음'}",
                ]
            )
        elif name.startswith("duty-flip"):
            summary_rows.append(
                [
                    name,
                    f"{metrics['detected']}/{metrics['injected']}",
                    f"결함 탐지 {_pct(metrics['detection_rate'])},"
                    f" 인용 유효 {_pct(metrics['quote_groundedness']['rate'])}",
                    f"오탐(대조군) {len(metrics['false_flips'])}건,"
                    f" 미탐 {metrics['missed'] or '없음'}",
                ]
            )
        else:
            summary_rows.append(
                [
                    name,
                    f"{metrics['caught']}/{metrics['defective']}",
                    f"재현율 {_pct(metrics['recall'])},"
                    f" 오탐률 {_pct(metrics['false_alarm_rate'])}",
                    f"미탐: {metrics['missed'] or '없음'}",
                ]
            )
    lines += _table(["스위트", "적중", "지표", "비고"], summary_rows)

    arms = {
        entry["result"]["arm"]: entry["metrics"]
        for entry in run["suites"]
        if entry["result"]["suite"].startswith("duty-flip")
    }
    if len(arms) > 1:
        lines += [
            "## 파이프라인 대비 축소 비교(ablation)",
            "",
            "같은 루브릭 항목·같은 입력에 대해 인용 검증·조건 판단·재시도를 제거한 단일 호출"
            "(`ablation`)과 본 파이프라인(`pipeline`)을 비교합니다.",
            "",
        ]
        lines += _table(
            ["지표", *arms],
            [
                ["결함 탐지율", *[_pct(m["detection_rate"]) for m in arms.values()]],
                [
                    "인용 유효율",
                    *[_pct(m["quote_groundedness"]["rate"]) for m in arms.values()],
                ],
                [
                    "대조군 오탐 건수",
                    *[str(len(m["false_flips"])) for m in arms.values()],
                ],
                [
                    "판정 불가로 보류",
                    *[str(m["softened_to_unjudged"]) for m in arms.values()],
                ],
                [
                    "기준선 판정 분포",
                    *[str(m["base_verdicts"]) for m in arms.values()],
                ],
            ],
        )

    for entry in run["suites"]:
        result, metrics = entry["result"], entry["metrics"]
        lines += [f"## 상세 — {result['suite']}", ""]
        if result["suite"] == "classification":
            lines += _table(
                ["케이스", "정답 유형", "판정 유형", "정답 화면", "판정 화면", "일치"],
                [
                    [
                        row["case"],
                        row["expected_product_type"],
                        row["actual_product_type"],
                        row["expected_page_type"],
                        row["actual_page_type"],
                        "O" if row["correct"] else "X",
                    ]
                    for row in result["rows"]
                ],
            )
        elif result["suite"].startswith("duty-flip"):
            base = result["base"]
            lines += [
                f"- 기준 페이지: `{base['html']}` (본문 {base['visible_chars']:,}자,"
                f" 적용 항목 {base['items_in_scope']}개)",
                f"- 기준 판정 분포: {base['verdicts']}",
                f"- 인용이 확인된 적합 판정 {base['passed_with_quote']}건 중"
                f" {metrics['injected']}건을 삭제 대상으로 사용",
                "",
            ]
            lines += _table(
                ["케이스", "유형", "항목", "삭제 전", "삭제 후", "탐지", "삭제된 문장"],
                [
                    [
                        row["case"],
                        row["kind"],
                        row["code"] or "-",
                        row["base_verdict"],
                        row["after_verdict"] or "-",
                        {True: "O", False: "X", None: "-"}[row.get("detected")],
                        row["removed_quote"],
                    ]
                    for row in result["rows"]
                ],
            )
        else:
            lines += _table(
                ["케이스", "주입 결함", "적발", "정답 일치", "적발 내용"],
                [
                    [
                        row["case"],
                        row["defect"] or "(무결함 대조군)",
                        "O" if row["flagged"] else "X",
                        "O" if row["correct"] else "X",
                        "; ".join(row["problems"])[:110] or "-",
                    ]
                    for row in result["rows"]
                ],
            )
        lines += [f"- 지표: `{metrics}`", ""]

    lines += [
        "## 이 평가가 말하지 않는 것",
        "",
        *[f"- {limit}" for limit in run["limits"]],
        "",
    ]
    return "\n".join(lines)
