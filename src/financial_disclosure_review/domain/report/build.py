"""Assembles the review report; adds no judgment, and any `판정 불가` becomes a reviewer task."""

from collections.abc import Mapping
from typing import Any

from ...core.usage import current

STATUS_PASSED = "검토 완료"
STATUS_REVIEW = "사람 검토 필요"
STATUS_OUT_OF_SCOPE = "검토 대상 아님"
STATUS_UNJUDGED = "판정 불가"
STATUS_COLLECTION_FAILED = "수집 실패"
STATUS_INSUFFICIENT = "조사 불충분"
# product_page.status values written by the page-evidence agent.
PAGE_COMPLETE = "완료"

PUBLISH_BLOCKED = "독자 맞춤 설명 자동 게시 불가 — 원문 유지"
PUBLISH_ALLOWED = "담당자 확인 후 독자 맞춤 설명 게시 가능"
EXPLANATION = "독자 맞춤 설명"

SEVERITY_VIOLATION = "위반"
SEVERITY_SHORTFALL = "권고 미충족"
AD_PAGE_TYPES = ("상품광고", "업무광고")
# Rubric `binding` levels that bind a page directly when the rule is about that kind of page.
DIRECT_BINDINGS = ("법령", "협회 자율규제")


def severity(module: str, binding: str | None, page_type: str | None) -> tuple[str, str]:
    """How 부적합 reads: direct bindings are 위반; explanation duty by 준용 is 권고 미충족."""
    if binding and binding not in DIRECT_BINDINGS:
        return SEVERITY_SHORTFALL, binding
    if module == "explanation_duty_check" and page_type in AD_PAGE_TYPES:
        return SEVERITY_SHORTFALL, "설명의무 준용"
    return SEVERITY_VIOLATION, binding or "구속력 미상"


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


def _step_costs(by_step: Mapping[str, Any]) -> str:
    """Where the calls went, most expensive first, e.g. `ExplanationJudgments 4회 $0.0612`."""
    return ", ".join(
        f"{step} {entry.get('calls', 0)}회 ${float(entry.get('usd', 0)):.4f}"
        for step, entry in sorted(by_step.items(), key=lambda kv: -float(kv[1].get("usd", 0)))
    )


def _clip(text: str, limit: int = 120) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _accepted(plain: Mapping[str, Any]) -> list[dict]:
    """Accepted explanation units, or a legacy checkpoint's accepted plain-language blocks."""
    if "units" in plain:
        return [u for u in plain.get("units") or [] if u.get("status") == "accepted"]
    return list(plain.get("accepted_blocks") or [])


def _reverted(plain: Mapping[str, Any]) -> list[dict]:
    """Units that fell back to the original line (legacy: plain-language contract errors)."""
    if "units" in plain:
        return [
            {
                "source_id": ",".join(u.get("source_ids") or []),
                "reason": "; ".join(u.get("problems") or []),
            }
            for u in plain.get("units") or []
            if u.get("status") == "reverted"
        ]
    return list(plain.get("contract_errors") or [])


def _findings(
    display: Mapping[str, Any],
    duty: Mapping[str, Any],
    plain: Mapping[str, Any],
    bindings: Mapping[str, str] | None = None,
    page_type: str | None = None,
) -> list[dict]:
    """Every row a reviewer must check; a 부적합 row also carries its `severity` and `basis`."""
    bindings = bindings or {}
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
    for side, label in (("original", "원문"), ("plain", EXPLANATION)):
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
    for row in found:
        if row["verdict"] == "부적합":
            row["severity"], row["basis"] = severity(
                row["module"], bindings.get(row["code"]), page_type
            )
    for row in duty.get("fidelity") or []:
        where = ",".join(row.get("source_ids") or []) or row.get("source_id", "")
        found.append(
            {
                "module": "explanation_duty_check",
                "code": row.get("code", ""),
                "verdict": f"의미 차이({row.get('kind', '')})"
                + (" [정보]" if row.get("informational") else ""),
                "target": f"{EXPLANATION} {where}".strip(),
                "reason": row.get("reason", ""),
                "quotes": [row["quote"]] if row.get("quote") else [],
            }
        )
    for row in _reverted(plain):
        found.append(
            {
                "module": "persona_explanation",
                "code": row.get("marker", "") or "원문 대체",
                "verdict": "원문 대체",
                "target": f"{EXPLANATION} {row.get('source_id', '')}",
                "reason": row.get("reason", ""),
                "quotes": [],
            }
        )
    return found


def _collection_action(page: Mapping[str, Any]) -> str:
    """One reviewer line naming why collection stopped; empty when the agent finished cleanly."""
    status = page.get("status")
    if not status or status == PAGE_COMPLETE:
        return ""
    gaps = [
        g
        for g in (page.get("coverage") or {}).get("gaps") or []
        if g.get("status") in ("open", "unresolved")
    ]
    detail = f" — {_clip(str(page['error']), 160)}" if page.get("error") else ""
    return (
        f"페이지 수집 {status}({page.get('stop_reason') or '사유 미기재'}){detail}:"
        f" 열린 조사 공백 {len(gaps)}건을 사람이 화면에서 확인"
    )


def _status(
    classification: Mapping[str, Any],
    display: Mapping[str, Any],
    verification: Mapping[str, Any],
    findings: list[dict],
    stop: Mapping[str, Any],
    page: Mapping[str, Any] | None = None,
) -> tuple[str, str, list[str]]:
    page = page or {}
    # Collection comes first: with no collected html nothing downstream ran, and a missing
    # classification must not read as a classification problem.
    if page.get("status") and not page.get("html"):
        failed = page.get("status") == STATUS_COLLECTION_FAILED
        return (
            STATUS_COLLECTION_FAILED if failed else STATUS_INSUFFICIENT,
            "페이지를 수집하지 못해 검토를 진행하지 않았습니다."
            if failed
            else "수집 agent가 검토할 본문을 확정하지 못해 검토를 진행하지 않았습니다.",
            [
                _collection_action(page),
                "사람이 페이지를 직접 확인하거나 원인을 해소한 뒤 재실행",
            ],
        )
    status, decision, actions = _judged_status(
        classification, display, verification, findings, stop
    )
    collection = _collection_action(page)
    if collection:
        actions = [collection, *actions]
        # An open evidence gap means the page was not fully seen; a clean pass is not earned.
        if status == STATUS_PASSED:
            status = STATUS_REVIEW
    return status, decision, actions


def _judged_status(
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
    levels = sorted(
        {(row["target"], row.get("severity", SEVERITY_VIOLATION)) for row in violations}
    )
    for target, level in levels:
        rows = [
            row
            for row in violations
            if row["target"] == target and row.get("severity", SEVERITY_VIOLATION) == level
        ]
        codes = sorted({row["code"] for row in rows})
        bases = sorted({row["basis"] for row in rows if row.get("basis")})
        basis = f"({', '.join(bases)})" if bases else ""
        actions.append(f"{target} {level}{basis} {len(codes)}건 확인·수정: {_codes(codes)}")
    diffs = [f for f in findings if str(f["verdict"]).startswith("의미 차이")]
    if diffs:
        actions.append(
            f"{EXPLANATION}이 원문과 어긋난 항목 {len(diffs)}건 확인: "
            f"{_codes(sorted({f['code'] for f in diffs}))}"
        )
    replaced = [f for f in findings if f["verdict"] == "원문 대체"]
    if replaced:
        actions.append(f"{EXPLANATION} 검사에서 원문으로 되돌린 단위 {len(replaced)}건 확인")
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
    bindings: Mapping[str, str] | None = None,
    previous_cost: Mapping[str, Any] | None = None,
    *,
    cards: Mapping[str, Any] | None = None,
    references: Mapping[str, Any] | None = None,
) -> dict:
    """The Report fields; `stop` is why the run ended, `previous_cost` carries cost on rebuild."""
    stop = stop or {}
    findings = _findings(display, duty, plain, bindings, classification.get("page_type"))
    status, decision, actions = _status(classification, display, verification, findings, stop, page)
    cost = current().summary()
    if not cost.get("calls") and previous_cost and previous_cost.get("calls"):
        cost = {**previous_cost, "carried_forward": True}
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
        "plain_blocks": len(_accepted(plain)),
        "plain_rejected": len(_reverted(plain)),
        "verification_passed": verification.get("passed"),
        "verification_loops": verification.get("loop_count"),
        "findings": len(findings),
        "violations": sum(1 for row in findings if row.get("severity") == SEVERITY_VIOLATION),
        "shortfalls": sum(1 for row in findings if row.get("severity") == SEVERITY_SHORTFALL),
    }
    cards, references = cards or {}, references or {}
    summary["evidence_cards"] = len(cards.get("cards") or [])
    summary["reference_links"] = len(references.get("links") or [])
    limits = _limits(display, plain, duty)
    limits += _card_limits(cards, duty)
    return {
        "status": status,
        "decision": decision,
        "actions": actions,
        "summary": summary,
        "findings": findings,
        "limits": limits,
        "cost": cost,
        "markdown": _markdown(
            page,
            classification,
            display,
            plain,
            duty,
            verification,
            stop,
            status,
            decision,
            actions,
            summary,
            findings,
            limits,
            cost,
            cards,
            references,
        ),
    }


def _collection_section(page: Mapping[str, Any]) -> list[str]:
    """What the page agent did, why it stopped, and which evidence gaps stayed open."""
    coverage = page.get("coverage") or {}
    trace = page.get("agent_trace") or []
    unreachable = [
        g
        for g in coverage.get("gaps") or []
        if g.get("kind") == "hidden_text" and g.get("status") == "unresolved"
    ]
    lines = [
        "## 10. 페이지 수집 agent 기록",
        "",
        f"- 상태: {page.get('status') or '(기록 없음)'},"
        f" 중단 사유: {page.get('stop_reason') or '-'}",
        *([f"- 오류: {_clip(str(page['error']), 300)}"] if page.get("error") else []),
        f"- 조사 범위(전 → 후): {coverage.get('before') or '-'} → {coverage.get('after') or '-'}",
        "- `조사 불충분`은 누락의 증거가 아닙니다. 보이지 않은 조건은 위반이 아니라 조사 공백으로"
        " 남깁니다.",
        *(
            [
                "- 한계: 열 수 있는 컨트롤을 모두 시도해도 보이지 않은"
                f" 숨김 글 {len(unreachable)}건은 상태 판단에서 제외했습니다."
                " 이 글에 조건·예외가 있다면 이 검토는 확인하지 못했습니다."
            ]
            if unreachable
            else []
        ),
        "",
    ]
    lines += _table(
        [
            [
                gap.get("id", ""),
                gap.get("kind", ""),
                gap.get("status", ""),
                _clip(str(gap.get("detail", "")), 100),
                _clip(str(gap.get("closed_by") or ""), 60),
            ]
            for gap in coverage.get("gaps") or []
        ],
        ["공백", "종류", "상태", "내용", "닫은 행동"],
    )
    lines += _table(
        [
            [
                str(step.get("turn", "")),
                step.get("tool", ""),
                _clip(str(step.get("args") or ""), 70),
                _clip(str((step.get("rationale") or {}).get("gap_id") or ""), 20),
                ("거부: " + _clip(str(step.get("blocked_reason", "")), 50))
                if step.get("blocked")
                else ("새 증거" if step.get("new_evidence") else "-"),
            ]
            for step in trace
        ],
        ["턴", "도구", "인자", "대상 공백", "결과"],
    )
    return lines


def _card_limits(cards: Mapping[str, Any], duty: Mapping[str, Any]) -> list[str]:
    """Limits the evidence cards reveal: open gaps, and passes that rest only on unseen text."""
    limits = []
    gaps = [
        g for g in cards.get("coverage_gaps") or [] if g.get("status") in ("open", "unresolved")
    ]
    if gaps:
        kinds = sorted({str(g.get("kind")) for g in gaps})
        limits.append(
            f"조사 공백 {len(gaps)}건({', '.join(kinds)})은 누락의 증거가 아니라 확인하지 못한"
            " 범위입니다."
        )
    sources = cards.get("sources") or []
    unseen = [s["text"] for s in sources if s.get("visibility") in ("hidden", "unresolved")]
    seen = [s["text"] for s in sources if s.get("visibility") not in ("hidden", "unresolved")]
    shaky = sorted(
        {
            row.get("code", "")
            for row in duty.get("original") or []
            if row.get("verdict") == "적합"
            and row.get("quote")
            and any(_squash(row["quote"]) in _squash(text) for text in unseen)
            and not any(_squash(row["quote"]) in _squash(text) for text in seen)
        }
    )
    if shaky:
        limits.append(
            f"원문 적합 {len(shaky)}건({_codes(shaky)})의 인용은 화면에 보이지 않았거나 가시성을"
            " 확인하지 못한 문장에만 있습니다. 사람이 화면에서 노출 여부를 확인해야 합니다."
        )
    return limits


def _squash(text: str) -> str:
    return "".join((text or "").split())


def _cards_section(cards: Mapping[str, Any]) -> list[str]:
    if not cards:
        return []
    reason = f" ({_clip(str(cards['reason']), 120)})" if cards.get("reason") else ""
    lines = [
        "## 11. 증거 카드와 조사 공백",
        "",
        f"- 상태: {cards.get('status', '-')}{reason}, 카드 {len(cards.get('cards') or [])}건,"
        f" 검증 탈락 {len(cards.get('rejected') or [])}건",
        "- 카드는 원문 인용과 출처(`dom-N`)가 코드로 재확인된 사실 단위이며, 법률 판단이 아닙니다.",
        "",
    ]
    lines += _table(
        [
            [
                card.get("id", ""),
                card.get("kind", ""),
                _clip(card.get("quote", ""), 70),
                _clip(", ".join(card.get("qualifiers") or []), 40),
                _clip(", ".join(card.get("exceptions") or []), 40),
                card.get("source_id", ""),
                card.get("visibility", ""),
            ]
            for card in cards.get("cards") or []
        ],
        ["카드", "종류", "인용", "조건", "예외", "출처", "가시성"],
    )
    lines += _table(
        [
            [
                str(gap.get("id") or "-"),
                str(gap.get("kind", "")),
                str(gap.get("status", "")),
                ", ".join(gap.get("card_ids") or []),
            ]
            for gap in cards.get("coverage_gaps") or []
        ],
        ["공백", "종류", "상태", "관련 카드"],
    )
    return lines


def _references_section(references: Mapping[str, Any]) -> list[str]:
    if not references:
        return []
    method = references.get("method") or {}
    reason = f" ({_clip(str(references['reason']), 120)})" if references.get("reason") else ""
    lines = [
        "## 12. 참고 사례 (판정에 사용하지 않음)",
        "",
        "- 아래 사례는 비슷한 표시 유형을 찾아 참고로만 연결한 것입니다. 이 검토의 적합·부적합"
        " 판정은 사례와 무관하게 루브릭과 페이지 인용으로만 정해졌습니다.",
        f"- 상태: {references.get('status', '-')}{reason},"
        f" 후보 {len(references.get('candidates') or [])}건,"
        f" 임계값 {method.get('threshold', '-')}, 사례 출처 {method.get('cases_from', '-')}",
        "",
    ]
    lines += _table(
        [
            [
                link.get("case_id", ""),
                ", ".join(link.get("card_ids") or []),
                _clip(link.get("page_quote", ""), 60),
                _clip(link.get("case_quote") or link.get("case_quote_note", ""), 60),
                _clip("; ".join(link.get("material_difference") or []), 80),
                (link.get("page_only_detectability") or "")
                + (f" — {link['page_only_note']}" if link.get("page_only_note") else ""),
                link.get("official_url", ""),
            ]
            for link in references.get("links") or []
        ],
        [
            "사례",
            "카드",
            "페이지 인용",
            "사례 인용",
            "중요한 차이",
            "페이지 단독 판단",
            "공식 출처",
        ],
    )
    return lines


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
    if _reverted(plain):
        limits.append(
            f"{EXPLANATION} {len(_reverted(plain))}개 단위는 검사를 통과하지 못해 원문 문장으로"
            " 되돌렸습니다."
        )
    profile = plain.get("profile") or {}
    if profile:
        limits.append(
            f"{EXPLANATION}은 독자 프로필 {profile.get('id', '-')} v{profile.get('version', '-')}"
            f"({profile.get('review_status', '-')}, {profile.get('status', '-')}) 기준의 보조"
            " 설명이며, 원문을 대신하거나 독자의 자격·혜택·상환액을 판단하지 않습니다."
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
    cards: Mapping[str, Any] | None = None,
    references: Mapping[str, Any] | None = None,
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
        f"- 페이지 수집: {page.get('status') or '(기록 없음)'} ({page.get('stop_reason') or '-'})",
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
                    f"설명의무({EXPLANATION})",
                    f"{summary['duty_items_applied']}/{summary['duty_items_total']}",
                    str(summary["duty_violations_plain"]),
                    str(_unjudged(duty.get("plain"))),
                ],
                [
                    EXPLANATION,
                    str(summary["plain_blocks"] + summary["plain_rejected"]),
                    str(summary["plain_rejected"]),
                    str(summary["fidelity_diffs"]),
                ],
            ],
            ["검토 영역", "검토 항목", "위반·반려", "판정 불가·차이"],
        ),
        *(
            [
                f"부적합 {summary['violations'] + summary['shortfalls']}건 중 위반"
                f" {summary['violations']}건, 권고 미충족 {summary['shortfalls']}건입니다. 광고"
                " 규정과 협회 표시 규정은 공개 상품 페이지(광고)에 직접 적용되어 위반으로 읽고,"
                " 설명의무 항목은 계약 권유 단계의 의무를 광고 화면에 준용한 것이어서 권고"
                " 미충족으로 읽습니다.",
                "",
            ]
            if summary["violations"] + summary["shortfalls"]
            else []
        ),
        "## 3. 확인이 필요한 항목",
        "",
        *_table(
            [
                [
                    row["code"],
                    row["target"],
                    str(row["verdict"]),
                    f"{row['severity']}({row['basis']})" if row.get("severity") else "-",
                    _clip(row["reason"], 160),
                    _clip(" / ".join(row["quotes"]), 80),
                ]
                for row in findings
            ],
            ["항목", "대상", "판정", "구분", "사유", "인용"],
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
        f"## 5. 설명의무 검토 상세 (원문 대비 {EXPLANATION})",
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
        ["항목", "조건", "원문 판정", f"{EXPLANATION} 판정", "의미 차이", "원문 인용"],
    )
    lines += [f"## 6. {EXPLANATION} 결과", ""]
    if "units" in plain:
        profile = plain.get("profile") or {}
        lines += [
            f"- 상태: {plain.get('status', '-')}"
            + (f" ({_clip(str(plain['reason']), 120)})" if plain.get("reason") else ""),
            f"- 독자 프로필: {profile.get('id', '-')} v{profile.get('version', '-')}"
            f" ({profile.get('source', '-')}, {profile.get('review_status', '-')},"
            f" {profile.get('status', '-')})",
            "- 원문 사실(exact_fact)은 설명 옆에 그대로 남습니다."
            " 위험 개념에는 비유를 쓰지 않습니다.",
            "",
        ]
        lines += _table(
            [
                [
                    unit.get("unit_id", ""),
                    ", ".join(unit.get("source_ids") or []),
                    _clip(unit.get("exact_fact", ""), 70),
                    _clip(unit.get("explanation", ""), 90),
                    _clip(unit.get("analogy", ""), 40) or "-",
                    unit.get("status", ""),
                ]
                for unit in plain.get("units") or []
            ],
            ["단위", "출처", "원 사실", "설명", "비유", "상태"],
        )
        ledger = duty.get("ledger") or []
        if ledger:
            lines += ["### 사실 원장 대조", ""]
            lines += _table(
                [
                    [
                        row.get("fact_id", ""),
                        row.get("kind", ""),
                        _clip(str(row.get("value", "")), 50),
                        str(row.get("verdict", "")),
                        str(row.get("decided_by", "")),
                    ]
                    for row in ledger
                ],
                ["사실", "종류", "값", "보존", "판단 주체"],
            )
        controls = plain.get("controls") or {}
        if controls:
            lines += [
                "### 운영 통제 (판정 대상 아님)",
                "",
                f"- 화면: {', '.join(controls.get('ui') or [])}",
                f"- 거버넌스: {', '.join(controls.get('governance') or [])}",
                "",
            ]
    else:
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
                    [
                        row.get("term", ""),
                        row.get("source_id", ""),
                        _clip(row.get("gloss", ""), 120),
                    ]
                    for row in term_refs
                ],
                ["용어", "블록", "풀이"],
            )
    lines += [
        "## 7. 자동 검증 결과",
        "",
        f"- 통과: {verification.get('passed')}",
        f"- 실패 모듈: {verification.get('failed_modules') or '없음'}",
        f"- 검증 루프: {verification.get('loop_count')}회 (최대 {stop.get('max_loops', '-')}회)",
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
        (
            "아래 수치는 **원래 검토 실행**에서 기록된 값입니다. 이 문서는 체크포인트에서 모델"
            " 호출 없이 다시 만들었고, 다시 만드는 데 든 비용은 없습니다."
            if cost.get("carried_forward")
            else "아래 수치는 **이 문서를 만든 실행**에서 발생한 것입니다."
        ),
        "",
        f"- 모델 호출 {cost.get('calls')}회, 입력 {cost.get('input_tokens'):,} tokens,"
        f" 출력 {cost.get('output_tokens'):,} tokens",
        f"- 비용 ${cost.get('usd')} (약 {cost.get('krw')}원, {cost.get('usd_krw')}원/$ 가정)",
        f"- 소요시간 {cost.get('elapsed_seconds')}초",
        f"- 상한: {cost.get('caps')}",
        *(
            [
                "- 이 문서는 모델 호출 없이 만들어졌습니다(녹음 재생 또는 체크포인트 재생성)."
                " 원래 검토의 비용은 이 문서에 기록되지 않았습니다."
            ]
            if not cost.get("calls")
            else []
        ),
        *([f"- 단계별: {_step_costs(cost['by_step'])}"] if cost.get("by_step") else []),
        "",
        "## 9. 한계와 가정",
        "",
    ]
    lines += [f"- {limit}" for limit in limits]
    lines += ["", *_collection_section(page)]
    lines += _cards_section(cards or {})
    lines += _references_section(references or {})
    lines += [
        "---",
        "",
        "이 문서는 자동 검토 결과입니다(ai-generated). 게시 여부의 최종 판단은 컴플라이언스"
        " 담당자가 합니다.",
        "",
    ]
    return "\n".join(lines)
