"""Assembling the final review report: the one artifact a compliance reviewer reads.

The report adds no judgment. It states what each module decided, the evidence it cited, what
could not be decided, and what the reviewer has to do next. Anything a module left as
`판정 불가` becomes a task for a person here — never a pass.
"""

from collections.abc import Mapping
from typing import Any

from ...core.usage import current

STATUS_PASSED = "검토 완료"
STATUS_REVIEW = "사람 검토 필요"
STATUS_OUT_OF_SCOPE = "검토 대상 아님"
STATUS_UNJUDGED = "판정 불가"

PUBLISH_BLOCKED = "쉬운말 자동 게시 불가 — 원문 유지"
PUBLISH_ALLOWED = "담당자 확인 후 쉬운말 게시 가능"


def _table(rows: list[list[str]], header: list[str]) -> list[str]:
    if not rows:
        return ["(해당 항목 없음)", ""]
    escaped = [[str(cell).replace("|", "\\|").replace("\n", " ") for cell in row] for row in rows]
    return [
        "| " + " | ".join(header) + " |",
        "|" + "|".join(["---"] * len(header)) + "|",
        *["| " + " | ".join(row) + " |" for row in escaped],
        "",
    ]


def _codes(codes: list[str], limit: int = 12) -> str:
    """항목 코드 목록. 너무 길면 앞쪽만 보여 주고 나머지는 건수로 적습니다."""
    shown = [c for c in codes[:limit] if c]
    rest = len(codes) - len(shown)
    return ", ".join(shown) + (f" 외 {rest}건" if rest > 0 else "")


def _unjudged(rows: Any) -> int:
    return sum(1 for row in rows or [] if row.get("verdict") == "판정 불가")


def _clip(text: str, limit: int = 120) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _findings(
    display: Mapping[str, Any], duty: Mapping[str, Any], plain: Mapping[str, Any]
) -> list[dict]:
    """Every row a reviewer has to look at: a violation, or something the run could not decide."""
    found: list[dict] = []
    for row in display.get("items") or []:
        if row.get("verdict") in ("부적합", "판정 불가"):
            found.append(
                {
                    "module": "display_check",
                    "code": row.get("code", ""),
                    "verdict": row.get("verdict"),
                    "target": "판매 화면 표시방법",
                    "reason": row.get("reason", ""),
                    "quotes": row.get("quotes") or [],
                }
            )
    for side, label in (("original", "원문"), ("plain", "쉬운말")):
        for row in duty.get(side) or []:
            if row.get("verdict") in ("부적합", "판정 불가"):
                found.append(
                    {
                        "module": "explanation_duty_check",
                        "code": row.get("code", ""),
                        "verdict": row.get("verdict"),
                        "target": label,
                        "reason": row.get("reason", ""),
                        "quotes": [row.get("quote", "")] if row.get("quote") else [],
                    }
                )
    for row in duty.get("fidelity") or []:
        found.append(
            {
                "module": "explanation_duty_check",
                "code": row.get("code", ""),
                "verdict": f"의미 차이({row.get('kind', '')})",
                "target": f"쉬운말 블록 {row.get('source_id', '')}",
                "reason": row.get("reason", ""),
                "quotes": [],
            }
        )
    for row in plain.get("contract_errors") or []:
        found.append(
            {
                "module": "plain_language",
                "code": row.get("marker", "") or "계약위반",
                "verdict": "원문 대체",
                "target": f"쉬운말 블록 {row.get('source_id', '')}",
                "reason": row.get("reason", ""),
                "quotes": [],
            }
        )
    return found


def _status(
    classification: Mapping[str, Any],
    display: Mapping[str, Any],
    verification: Mapping[str, Any],
    findings: list[dict],
    stop: Mapping[str, Any],
) -> tuple[str, str, list[str]]:
    product_type = classification.get("product_type")
    if product_type == "범위 밖":
        return (
            STATUS_OUT_OF_SCOPE,
            "검토를 진행하지 않았습니다.",
            [f"분류 근거 확인: {_clip(str(classification.get('reason', '')), 200)}"],
        )
    if product_type == "판정 불가" or not product_type:
        return (
            STATUS_UNJUDGED,
            "상품 유형을 확정하지 못해 이후 검토를 진행하지 않았습니다.",
            [
                "사람이 상품 유형을 확정한 뒤 재실행",
                f"분류 사유: {_clip(str(classification.get('reason', '')), 200)}",
            ],
        )

    actions: list[str] = []
    unjudged = [f for f in findings if f["verdict"] == "판정 불가"]
    violations = [f for f in findings if f["verdict"] == "부적합"]
    if (display.get("judgments") or {}).get("status") != "완료":
        actions.append(
            "표시방법 검토가 완료되지 않았습니다: "
            + _clip(str((display.get("judgments") or {}).get("reason", "")), 160)
        )
    # 항목을 한 줄씩 나열하면 조치 목록이 수십 줄이 됩니다. 담당자가 화면 단위로 일하므로
    # 대상(표시방법·원문·쉬운말)별로 묶고 코드만 보여 줍니다.
    for target in sorted({row["target"] for row in violations}):
        codes = sorted({row["code"] for row in violations if row["target"] == target})
        actions.append(f"{target} 위반 {len(codes)}건 확인·수정: {_codes(codes)}")
    diffs = [f for f in findings if str(f["verdict"]).startswith("의미 차이")]
    if diffs:
        actions.append(
            f"쉬운말이 원문과 어긋난 블록 {len(diffs)}건 확인: "
            f"{_codes(sorted({f['code'] for f in diffs}))}"
        )
    replaced = [f for f in findings if f["verdict"] == "원문 대체"]
    if replaced:
        actions.append(f"쉬운말 계약 검사에서 원문으로 되돌린 블록 {len(replaced)}건 확인")
    if unjudged:
        by_target = sorted({row["target"] for row in unjudged})
        actions.append(
            f"판정 불가 {len(unjudged)}건 사람 확인 필요"
            f" ({', '.join(by_target)}): {_codes(sorted({f['code'] for f in unjudged}))}"
        )

    if verification.get("passed") and not violations and not unjudged:
        return STATUS_PASSED, PUBLISH_ALLOWED, actions or ["담당자 최종 확인"]
    if verification.get("passed"):
        return (
            STATUS_REVIEW,
            PUBLISH_ALLOWED if not violations else PUBLISH_BLOCKED,
            actions,
        )
    actions.insert(
        0,
        f"자동 검증 미통과({stop.get('reason', '사유 미기재')}) — 컴플라이언스 담당자 에스컬레이션"
        + (f": {stop['detail']}" if stop.get("detail") else ""),
    )
    return STATUS_REVIEW, PUBLISH_BLOCKED, actions


def build_report(
    page: Mapping[str, Any],
    classification: Mapping[str, Any],
    display: Mapping[str, Any],
    plain: Mapping[str, Any],
    duty: Mapping[str, Any],
    verification: Mapping[str, Any],
    stop: Mapping[str, Any] | None = None,
) -> dict:
    """The Report fields. `markdown` is the reviewer-facing document; the rest is the same
    content as data, so a caller can render it another way. `stop` is the retry policy's account
    of why the run ended where it did; the graph layer owns that policy and passes it in."""
    stop = stop or {}
    findings = _findings(display, duty, plain)
    status, decision, actions = _status(classification, display, verification, findings, stop)
    cost = current().summary()
    product = page.get("product") or {}
    duty_items = duty.get("items") or []
    applied = [row for row in duty_items if row.get("applied")]
    summary = {
        "url": page.get("url"),
        "product_name": product.get("product_name"),
        "product_type": classification.get("product_type"),
        "page_type": classification.get("page_type"),
        "display_items": len(display.get("items") or []),
        "display_violations": sum(
            1 for row in display.get("items") or [] if row.get("verdict") == "부적합"
        ),
        "display_unjudged": sum(
            1 for row in display.get("items") or [] if row.get("verdict") == "판정 불가"
        ),
        "duty_items_applied": len(applied),
        "duty_items_total": len(duty_items),
        "duty_violations_original": sum(
            1 for row in duty.get("original") or [] if row.get("verdict") == "부적합"
        ),
        "duty_violations_plain": sum(
            1 for row in duty.get("plain") or [] if row.get("verdict") == "부적합"
        ),
        "fidelity_diffs": len(duty.get("fidelity") or []),
        "plain_blocks": len(plain.get("accepted_blocks") or []),
        "plain_rejected": len(plain.get("contract_errors") or []),
        "verification_passed": verification.get("passed"),
        "verification_loops": verification.get("loop_count"),
        "findings": len(findings),
    }
    limits = _limits(display, plain, duty)
    return {
        "status": status,
        "decision": decision,
        "actions": actions,
        "summary": summary,
        "findings": findings,
        "limits": limits,
        "cost": cost,
        "markdown": _markdown(
            page, classification, display, plain, duty, verification, stop, status, decision,
            actions, summary, findings, limits, cost,
        ),
    }


def _limits(
    display: Mapping[str, Any], plain: Mapping[str, Any], duty: Mapping[str, Any]
) -> list[str]:
    judgments = display.get("judgments") or {}
    limits = [
        "이 검토는 공개된 광고성 화면을 대상으로 하며, 청약 단계 설명화면은 범위에 없습니다."
        " 설명의무 기준은 준용해 품질 기준으로 적용했습니다.",
        "자동 검증은 인용 근거의 존재와 모듈 간 모순만 확인합니다. 통과가 법률 준수를 보증하지"
        " 않습니다.",
    ]
    for key in ("images", "backgrounds"):
        text = (judgments.get("limits") or {}).get(key)
        if text:
            limits.append(_clip(str(text), 300))
    for key in ("font_size", "contrast"):
        text = (judgments.get("assumptions") or {}).get(key)
        if text:
            limits.append("가정: " + _clip(str(text), 300))
    if plain.get("contract_errors"):
        limits.append(
            f"쉬운말 {len(plain['contract_errors'])}개 블록은 계약 검사를 통과하지 못해 원문"
            " 문장으로 되돌렸습니다."
        )
    unresolved = [row for row in duty.get("original") or [] if row.get("verdict") == "판정 불가"]
    if unresolved:
        limits.append(
            f"설명의무 원문 판정 불가 {len(unresolved)}건은 조건 성립 여부가 불명확합니다."
        )
    return limits


def _markdown(
    page: Mapping[str, Any],
    classification: Mapping[str, Any],
    display: Mapping[str, Any],
    plain: Mapping[str, Any],
    duty: Mapping[str, Any],
    verification: Mapping[str, Any],
    stop: Mapping[str, Any],
    status: str,
    decision: str,
    actions: list[str],
    summary: Mapping[str, Any],
    findings: list[dict],
    limits: list[str],
    cost: Mapping[str, Any],
) -> str:
    product = page.get("product") or {}
    lines: list[str] = [
        "---",
        "ai-generated: true",
        "human-review: false",
        "---",
        "",
        "# 금융상품 판매화면 검토 결과",
        "",
        f"- 판정: **{status}**",
        f"- 조치 방침: {decision}",
        f"- 대상 화면: {page.get('url', '')}",
        f"- 상품명: {product.get('product_name', '(확인 불가)')}",
        # 범위 밖·판정 불가로 끝난 검토는 화면유형이 정해지지 않은 채로 남습니다. 담당자가 읽는
        # 문서에 `None`이 그대로 찍히면 값이 빠진 것인지 오류인지 구분되지 않으므로 말로 적습니다.
        f"- 상품유형/화면유형: {classification.get('product_type') or '(확인 불가)'}"
        f" / {classification.get('page_type') or '(해당 없음)'}",
        f"- 분류 근거: {_clip(str(classification.get('reason', '')), 300)}",
        "",
        "## 1. 담당자 조치 목록",
        "",
    ]
    lines += [f"{n}. {action}" for n, action in enumerate(actions, 1)] or ["조치 사항 없음"]
    lines += [
        "",
        "## 2. 검토 요약",
        "",
        *_table(
            [
                [
                    "표시방법",
                    str(summary["display_items"]),
                    str(summary["display_violations"]),
                    str(summary["display_unjudged"]),
                ],
                [
                    "설명의무(원문)",
                    f"{summary['duty_items_applied']}/{summary['duty_items_total']}",
                    str(summary["duty_violations_original"]),
                    str(_unjudged(duty.get("original"))),
                ],
                [
                    "설명의무(쉬운말)",
                    f"{summary['duty_items_applied']}/{summary['duty_items_total']}",
                    str(summary["duty_violations_plain"]),
                    str(_unjudged(duty.get("plain"))),
                ],
                [
                    "쉬운말 변환",
                    str(summary["plain_blocks"] + summary["plain_rejected"]),
                    str(summary["plain_rejected"]),
                    str(summary["fidelity_diffs"]),
                ],
            ],
            ["검토 영역", "검토 항목", "위반·반려", "판정 불가·차이"],
        ),
        "## 3. 확인이 필요한 항목",
        "",
        *_table(
            [
                [
                    row["code"],
                    row["target"],
                    str(row["verdict"]),
                    _clip(row["reason"], 160),
                    _clip(" / ".join(row["quotes"]), 80),
                ]
                for row in findings
            ],
            ["항목", "대상", "판정", "사유", "인용"],
        ),
        "## 4. 표시방법 검토 상세",
        "",
        *_table(
            [
                [
                    row.get("code", ""),
                    str(row.get("verdict", "")),
                    ", ".join(row.get("block_ids") or []),
                    _clip(row.get("reason", ""), 200),
                ]
                for row in display.get("items") or []
            ],
            ["항목", "판정", "근거 블록", "사유"],
        ),
        "## 5. 설명의무 검토 상세 (원문 대비 쉬운말)",
        "",
    ]
    plain_by_code = {row.get("code"): row for row in duty.get("plain") or []}
    fidelity_by_code = {row.get("code"): row for row in duty.get("fidelity") or []}
    lines += _table(
        [
            [
                row.get("code", ""),
                str(row.get("condition_status", "")),
                str(row.get("verdict", "")),
                str((plain_by_code.get(row.get("code")) or {}).get("verdict", "-")),
                str((fidelity_by_code.get(row.get("code")) or {}).get("kind", "-")),
                _clip(row.get("quote", ""), 80),
            ]
            for row in duty.get("original") or []
        ],
        ["항목", "조건", "원문 판정", "쉬운말 판정", "의미 차이", "원문 인용"],
    )
    lines += ["## 6. 쉬운말 변환 결과", ""]
    lines += _table(
        [
            [
                row.get("source_id", ""),
                _clip(row.get("source_quote", ""), 90),
                _clip(row.get("text", ""), 90),
            ]
            for row in plain.get("accepted_blocks") or []
        ],
        ["블록", "원문", "쉬운말"],
    )
    term_refs = plain.get("term_refs") or []
    if term_refs:
        lines += ["### 용어 풀이", ""]
        lines += _table(
            [
                [row.get("term", ""), row.get("source_id", ""), _clip(row.get("gloss", ""), 120)]
                for row in term_refs
            ],
            ["용어", "블록", "풀이"],
        )
    lines += [
        "## 7. 자동 검증 결과",
        "",
        f"- 통과: {verification.get('passed')}",
        f"- 실패 모듈: {verification.get('failed_modules') or '없음'}",
        f"- 검증 루프: {verification.get('loop_count')}회"
        f" (최대 {stop.get('max_loops', '-')}회)",
        f"- 중단 사유: {stop.get('reason') or '없음(통과)'}"
        + (f" — {stop['detail']}" if stop.get("detail") else ""),
        f"- 재시도 이력: {verification.get('retry_history') or '없음'}",
        "",
    ]
    lines += [f"- {_clip(reason, 240)}" for reason in (verification.get("reasons") or [])]
    lines += [
        "",
        "## 8. 비용과 소요시간",
        "",
        "아래 수치는 **이 문서를 만든 실행**에서 발생한 것입니다. 체크포인트에서 보고서만 다시"
        " 만들면 모델 호출이 0회로 찍히며, 그때는 원래 검토의 비용이 아닙니다.",
        "",
        f"- 모델 호출 {cost.get('calls')}회, 입력 {cost.get('input_tokens'):,} tokens,"
        f" 출력 {cost.get('output_tokens'):,} tokens",
        f"- 비용 ${cost.get('usd')} (약 {cost.get('krw')}원, {cost.get('usd_krw')}원/$ 가정)",
        f"- 소요시간 {cost.get('elapsed_seconds')}초",
        f"- 상한: {cost.get('caps')}",
        *(
            ["- 이 실행은 모델을 부르지 않았습니다(체크포인트에서 보고서만 재생성)."]
            if not cost.get("calls")
            else []
        ),
        "",
        "## 9. 한계와 가정",
        "",
    ]
    lines += [f"- {limit}" for limit in limits]
    lines += [
        "",
        "---",
        "",
        "이 문서는 자동 검토 결과입니다(ai-generated). 게시 여부의 최종 판단은 컴플라이언스"
        " 담당자가 합니다.",
        "",
    ]
    return "\n".join(lines)
