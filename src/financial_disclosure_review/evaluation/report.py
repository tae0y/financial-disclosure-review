"""Rendering an evaluation run as the markdown a reader can check the numbers in."""

from typing import Any


def _table(header: list[str], rows: list[list[Any]]) -> list[str]:
    if not rows:
        return ["(케이스 없음)", ""]
    return [
        "| " + " | ".join(header) + " |",
        "|" + "|".join(["---"] * len(header)) + "|",
        *["| " + " | ".join(str(cell).replace("|", "\\|") for cell in row) + " |" for row in rows],
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
        if name.startswith("display-flip"):
            summary_rows.append(
                [
                    name,
                    f"{metrics['detected']}/{metrics['injected']}",
                    f"결함 탐지 {_pct(metrics['detection_rate'])},"
                    f" 대조군 오지목 {metrics['blamed_controls']}/{metrics['controls']}",
                    f"기준 판정 {metrics['base_verdicts']}",
                ]
            )
        elif name == "stability":
            summary_rows.append(
                [
                    name,
                    f"{metrics['duty_stable']}/{metrics['duty_items']}",
                    f"{metrics['repeats']}회 반복 동일 판정 {_pct(metrics['duty_stability'])}"
                    f" · 분류 {metrics['classification_stable']}/{metrics['classification_cases']}",
                    f"적합이 오간 항목 {metrics['duty_pass_flips'] or '없음'}"
                    f" · 흔들림 유형 {metrics.get('duty_unstable_kinds') or '없음'}",
                ]
            )
            for arm, base in metrics.get("baseline", {}).items():
                summary_rows.append(
                    [
                        f"stability/{arm}",
                        f"{base['duty_stable']}/{base['duty_items']}",
                        f"{metrics['repeats']}회 반복 동일 판정 {_pct(base['duty_stability'])}",
                        f"적합이 오간 항목 {base['duty_pass_flips'] or '없음'}"
                        f" · 흔들림 유형 {base.get('duty_unstable_kinds') or '없음'}",
                    ]
                )
        elif name.startswith("classification"):
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
                    f" 미탐 {metrics['missed'] or '없음'}"
                    + (f", 판정 실패 {metrics['failed']}" if metrics.get("failed") else ""),
                ]
            )
        else:
            summary_rows.append(
                [
                    name,
                    f"{metrics['caught']}/{metrics['defective']}",
                    f"재현율 {_pct(metrics['recall'])}, 오탐률 {_pct(metrics['false_alarm_rate'])}",
                    f"미탐: {metrics['missed'] or '없음'}",
                ]
            )
    lines += _table(["스위트", "적중", "지표", "비고"], summary_rows)

    classification_arms = {
        entry["result"].get("arm", "pipeline"): entry["metrics"]
        for entry in run["suites"]
        if entry["result"]["suite"].startswith("classification")
    }
    if len(classification_arms) > 1:
        lines += [
            "## 분류: 3단계 판정 대비 키워드 빈도 기준선",
            "",
            "같은 6개 페이지를 상품 낱말 빈도만으로 분류한 기준선(`keyword`)과 비교합니다."
            " 기준선은 모델을 부르지 않습니다.",
            "",
        ]
        lines += _table(
            ["지표", *classification_arms],
            [
                [
                    "정답 일치",
                    *[f"{m['correct']}/{m['cases']}" for m in classification_arms.values()],
                ],
                ["정확도", *[_pct(m["accuracy"]) for m in classification_arms.values()]],
                ["오분류", *[str(m["wrong"] or "없음") for m in classification_arms.values()]],
            ],
        )

    display_arms = {
        entry["result"]["arm"]: entry["metrics"]
        for entry in run["suites"]
        if entry["result"]["suite"].startswith("display-flip")
    }
    if len(display_arms) > 1:
        lines += [
            "## 표시방법: 라벨링 + 코드 측정 대비 코드 규칙만",
            "",
            "같은 렌더링 측정값과 같은 변형에 대해, 어떤 문구가 의무표시인지 모델이 라벨을 붙인 뒤"
            " 코드가 재는 본 구성(`pipeline`)과, 문구 구분 없이 기준 미달 블록이 하나라도 있으면"
            " 위반으로 보는 코드 규칙(`rules`)을 비교합니다.",
            "",
        ]
        lines += _table(
            ["지표", *display_arms],
            [
                [
                    "주입한 위반 탐지(해당 블록 지목)",
                    *[f"{m['detected']}/{m['injected']}" for m in display_arms.values()],
                ],
                [
                    "대조군 블록을 위반으로 지목",
                    *[f"{m['blamed_controls']}/{m['controls']}" for m in display_arms.values()],
                ],
                ["기준 페이지 판정", *[str(m["base_verdicts"]) for m in display_arms.values()]],
            ],
        )

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
            "(`ablation`)과 본 파이프라인(`pipeline`)을 비교합니다. 두 구성은 같은 삭제 변형을"
            " 판정합니다. 삭제 대상은 두 구성이 모두 적합으로 본 항목에서 고릅니다.",
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
                    *[
                        "판정 실패"
                        if "neutral-delete" in m.get("failed", [])
                        else str(len(m["false_flips"]))
                        for m in arms.values()
                    ],
                ],
                [
                    "답을 내지 못한 변형",
                    *[str(m.get("failed") or "없음") for m in arms.values()],
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
        if result["suite"].startswith("display-flip"):
            lines += _table(
                ["기준 페이지", "관찰 항목", "기준 판정", "기준 근거 블록", "전체 판정"],
                [
                    [
                        base["page"],
                        base["watch"],
                        base["verdict"],
                        ", ".join(base["block_ids"]) or "-",
                        base["all"],
                    ]
                    for base in result["bases"]
                ],
            )
            lines += _table(
                ["케이스", "유형", "루브릭", "대상 블록", "변형 전", "변형 후", "지목", "결과"],
                [
                    [
                        row["case"],
                        row["kind"],
                        row["rubric"] or "-",
                        row["block"] or "-",
                        row["base_verdict"],
                        row["after_verdict"] or "-",
                        {True: "O", False: "X", None: "-"}[row.get("cited")],
                        "탐지"
                        if row.get("detected")
                        else "미탐"
                        if row.get("detected") is False
                        else "오지목"
                        if row.get("blamed_control")
                        else "정상"
                        if row.get("blamed_control") is False
                        else row.get("note") or "-",
                    ]
                    for row in result["rows"]
                ],
            )
        elif result["suite"] == "stability":
            lines += [
                f"- 반복 횟수: {result['repeats']}회 (1회차는 다른 스위트가 쓰는 녹음, 2회차부터"
                " 새로 녹음)",
                f"- 설명의무 기준 페이지: `{result['base_html']}`",
                "",
            ]
            lines += _table(
                ["분류 케이스", "회차별 판정", "동일"],
                [
                    [
                        row["case"],
                        " / ".join(map(str, row["answers"])),
                        "O" if row["stable"] else "X",
                    ]
                    for row in result["classification"]
                ],
            )
            for arm, duty in [
                ("pipeline", result["duty"]),
                *(result.get("baseline") or {}).items(),
            ]:
                lines += [f"설명의무 반복 판정 — `{arm}`", ""]
                lines += _table(
                    ["설명의무 항목", "회차별 판정", "동일"],
                    [
                        [
                            row["code"],
                            " / ".join(map(str, row["verdicts"])),
                            "O" if row["stable"] else "X",
                        ]
                        for row in duty
                        if not row["stable"]
                    ]
                    or [["(모두 동일)", "-", "O"]],
                )
        elif result["suite"].startswith("classification"):
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
                f"- 이 구성의 적합 판정 {base.get('passed', '-')}건(인용 확인"
                f" {base['passed_with_quote']}건), 모든 구성이 적합으로 본 항목"
                f" {base.get('passed_by_every_arm', '-')}건 중 {metrics['injected']}건을 삭제"
                " 대상으로 사용(앞 대상과 같은 문장을 지우게 되는 항목은 건너뜀)",
                "",
            ]
            lines += _table(
                [
                    "케이스",
                    "유형",
                    "항목",
                    "삭제 전",
                    "삭제 후",
                    "탐지",
                    "삭제된 문장",
                    "삭제 후 근거",
                ],
                [
                    [
                        row["case"],
                        row["kind"],
                        row["code"] or "-",
                        row["base_verdict"],
                        row["after_verdict"] or "-",
                        {True: "O", False: "X", None: "-"}[row.get("detected")],
                        row["removed_quote"],
                        (
                            ("본문에 있음: " if row.get("after_quote_on_page") else "본문에 없음: ")
                            + row["after_quote"][:60]
                        )
                        if row.get("after_quote")
                        else "-",
                    ]
                    for row in result["rows"]
                ],
            )
            if metrics.get("missed_with_evidence_on_page"):
                lines += [
                    f"- 미탐 중 {metrics['missed_with_evidence_on_page']}는 삭제 뒤에도 본문에"
                    " 실제로 있는 다른 문장을 근거로 적합을 냈습니다. 같은 사실이 다른 곳에 남아"
                    " 있으면 '삭제했으므로 부적합'이라는 정답이 성립하지 않으므로, 이 사례는 정답을"
                    " 다시 봐야 합니다.",
                    "",
                ]
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
