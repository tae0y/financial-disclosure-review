"""Assembles the review report; adds no judgment, and any `판정 불가` becomes a reviewer task."""

from collections.abc import Mapping
from typing import Any

from ...core.usage import current
from .markdown import render_markdown

STATUS_PASSED = "검토 완료"
STATUS_REVIEW = "사람 검토 필요"
STATUS_OUT_OF_SCOPE = "검토 대상 아님"
STATUS_UNJUDGED = "판정 불가"
STATUS_COLLECTION_FAILED = "수집 실패"
STATUS_INSUFFICIENT = "조사 불충분"
# product_page.status values written by the page-evidence agent.
PAGE_COMPLETE = "완료"

PUBLISH_BLOCKED = "쉬운말 확인 권고 자동 게시 불가 — 원문만 게시"
PUBLISH_ALLOWED = "담당자 확인 후 쉬운말 확인 권고 게시 가능"
EXPLANATION = "쉬운말 확인 권고"

SEVERITY_VIOLATION = "위반"
SEVERITY_SHORTFALL = "권고 미충족"
# Rubric `binding` levels that bind a page directly when the rule is about that kind of page.
DIRECT_BINDINGS = ("법령", "협회 자율규제")


def severity(binding: str | None) -> tuple[str, str]:
    """How 부적합 reads: a direct binding is 위반, a guideline-level one 권고 미충족."""
    if binding and binding not in DIRECT_BINDINGS:
        return SEVERITY_SHORTFALL, binding
    return SEVERITY_VIOLATION, binding or "구속력 미상"


def _codes(codes: list[str], limit: int = 12) -> str:
    """항목 코드 목록. 너무 길면 앞쪽만 보여 주고 나머지는 건수로 적습니다."""
    shown = [c for c in codes[:limit] if c]
    rest = len(codes) - len(shown)
    return ", ".join(shown) + (f" 외 {rest}건" if rest > 0 else "")


def _clip(text: str, limit: int = 120) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _withheld(advice: Mapping[str, Any]) -> list[str]:
    """The code-check problems that kept the advice off the page; empty when it is shown."""
    return list(advice.get("problems") or [])


def _findings(
    display: Mapping[str, Any],
    disclosure: Mapping[str, Any],
    advice: Mapping[str, Any],
    bindings: Mapping[str, str] | None = None,
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
    for row in disclosure.get("original") or []:
        if row.get("verdict") in ("부적합", "판정 불가"):
            found.append(
                {
                    "module": "ad_disclosure_check",
                    "code": row.get("code", ""),
                    "verdict": row.get("verdict"),
                    "target": "원문",
                    "reason": row.get("reason", ""),
                    "quotes": [row.get("quote", "")] if row.get("quote") else [],
                }
            )
    for row in found:
        if row["verdict"] == "부적합":
            row["severity"], row["basis"] = severity(bindings.get(row["code"]))
    problems = _withheld(advice)
    if problems:
        found.append(
            {
                "module": "persona_explanation",
                "code": "원문 대체",
                "verdict": "원문 대체",
                "target": EXPLANATION,
                "reason": "; ".join(problems),
                "quotes": [],
            }
        )
    return found


def _loop(ran: str, trace: Any, stop_reason: Any) -> dict:
    steps = [t for t in trace or [] if isinstance(t, Mapping) and t.get("turn")]
    return {
        "ran": ran,
        "turns": max((int(t["turn"]) for t in steps), default=0),
        "tool_calls": sum(1 for t in steps if t.get("tool")),
        "stop_reason": str(stop_reason or ""),
    }


def agent_runs(page: Mapping[str, Any], selection: Mapping[str, Any]) -> dict:
    """Which of the two agent loops ran in this review, with turns, tool calls and stop.

    `ran` is `agent` when the model loop ran; otherwise how the step was settled without one:
    discovery `reuse` (a saved site rule) or `none`; reader_selection `default`, `uuid`,
    `attributes`, `fallback` or `not_run`.
    """
    trace = page.get("agent_trace") or []
    if trace:
        discovery = "agent"
    else:
        discovery = "reuse" if page.get("stop_reason") == "rule_reused" else "none"
    pick_trace = selection.get("trace") or []
    if any(t.get("turn") for t in pick_trace):
        reader = "agent"
    else:
        reader = str(selection.get("decided_by") or "not_run")
    return {
        "discovery": _loop(discovery, trace, page.get("stop_reason")),
        "reader_selection": _loop(reader, pick_trace, selection.get("stop_reason")),
    }


RUN_LABELS = {
    "discovery": ("페이지 탐색", {"reuse": "저장 규칙 재사용", "none": "실행 안 됨"}),
    "reader_selection": (
        "독자 선택",
        {
            "default": "상품유형 기본 조건",
            "uuid": "지정 uuid",
            "attributes": "지정 속성",
            "fallback": "대체",
            "not_run": "실행 안 됨",
        },
    ),
}


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
    collection = _collection_action(page)
    if stop.get("interrupted_at"):
        # A run cut short by its budget judged only part of the page: no verdict is earned,
        # whatever the finished steps found.
        return (
            STATUS_UNJUDGED,
            f"{stop['interrupted_at']} 단계에서 실행이 중단되어"
            f"({stop.get('reason') or '사유 미기재'}) 자동 판정을 내리지 않았습니다.",
            [
                f"검토 중단({stop.get('reason') or '사유 미기재'}): {stop.get('detail') or '-'}",
                *([collection] if collection else []),
                "한도를 조정해 재실행하거나 사람이 페이지 전체를 직접 검토",
            ],
        )
    status, decision, actions = _judged_status(
        classification, display, verification, findings, stop
    )
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
    # 대상(표시방법·원문·쉬운말 개요)별로 묶고 코드만 보여 줍니다.
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
    if any(f["verdict"] == "원문 대체" for f in findings):
        actions.append(f"{EXPLANATION}가 코드 검사를 통과하지 못해 싣지 않음: 사유 확인")
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
    advice: Mapping[str, Any],
    disclosure: Mapping[str, Any],
    verification: Mapping[str, Any],
    stop: Mapping[str, Any] | None = None,
    bindings: Mapping[str, str] | None = None,
    previous_cost: Mapping[str, Any] | None = None,
    *,
    cards: Mapping[str, Any] | None = None,
    labels: Mapping[str, Mapping[str, str]] | None = None,
) -> dict:
    """The Report fields; `stop` is why the run ended, `previous_cost` carries cost on rebuild.

    `labels` maps rubric codes to their question and legal basis for the markdown."""
    stop = stop or {}
    findings = _findings(display, disclosure, advice, bindings)
    status, decision, actions = _status(classification, display, verification, findings, stop, page)
    deferred = disclosure.get("deferred") or []
    if deferred and status in (STATUS_PASSED, STATUS_REVIEW):
        actions.append(
            f"설명의무 {len(deferred)}개 항목은 광고 페이지로 판정하지 않음 — 상품설명서에서"
            f" 확인: {_codes([row.get('code', '') for row in deferred])}"
        )
    cost = current().summary()
    if not cost.get("calls") and previous_cost and previous_cost.get("calls"):
        cost = {**previous_cost, "carried_forward": True}
    product = page.get("product") or {}
    disclosure_items = disclosure.get("items") or []
    applied = [row for row in disclosure_items if row.get("applied")]
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
        "disclosure_items_applied": len(applied),
        "disclosure_items_total": len(disclosure_items),
        "disclosure_violations_original": sum(
            1 for row in disclosure.get("original") or [] if row.get("verdict") == "부적합"
        ),
        "deferred_explanation_items": len(deferred),
        "advice_items": len(advice.get("advice_codes") or []) if advice.get("html") else 0,
        "advice_withheld": bool(_withheld(advice)),
        "verification_passed": verification.get("passed"),
        "verification_loops": verification.get("loop_count"),
        "findings": len(findings),
        "violations": sum(1 for row in findings if row.get("severity") == SEVERITY_VIOLATION),
        "shortfalls": sum(1 for row in findings if row.get("severity") == SEVERITY_SHORTFALL),
    }
    cards = cards or {}
    summary["evidence_cards"] = len(cards.get("cards") or [])
    summary["interrupted_at"] = stop.get("interrupted_at") or ""
    summary["agent_runs"] = agent_runs(page, advice.get("selection") or {})
    limits = _limits(display, advice, disclosure)
    limits += _card_limits(cards, disclosure)
    unreachable = _unreachable_limit(page)
    if unreachable:
        limits.append(unreachable)
    return {
        "status": status,
        "decision": decision,
        "actions": actions,
        "summary": summary,
        "findings": findings,
        "limits": limits,
        "cost": cost,
        "markdown": render_markdown(
            page,
            classification,
            display,
            advice,
            disclosure,
            status,
            decision,
            _notes(status, actions, page, verification, stop, unreachable),
            labels,
        ),
    }


def _card_limits(cards: Mapping[str, Any], disclosure: Mapping[str, Any]) -> list[str]:
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
            for row in disclosure.get("original") or []
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


def _limits(
    display: Mapping[str, Any], advice: Mapping[str, Any], disclosure: Mapping[str, Any]
) -> list[str]:
    judgments = display.get("judgments") or {}
    limits = [
        "이 검토는 공개된 광고 페이지를 광고 의무표시 기준으로 판정합니다. 설명의무는 청약 단계"
        " 상품설명서·설명화면의 의무라서 판정하지 않고 확인할 항목 목록으로만 제공합니다.",
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
    if _withheld(advice):
        limits.append(f"{EXPLANATION}는 코드 검사를 통과하지 못해 싣지 않았습니다.")
    profile = advice.get("profile") or {}
    if profile:
        limits.append(
            f"{EXPLANATION}는 독자 프로필 {profile.get('id', '-')} v{profile.get('version', '-')}"
            f"({profile.get('review_status', '-')}, {profile.get('status', '-')}) 기준으로 계약 전"
            " 확인할 사항을 권하는 보조 안내이며, 그 사항의 내용이나 독자의 자격·혜택·상환액을"
            " 판단하지 않습니다."
        )
    unresolved = [
        row for row in disclosure.get("original") or [] if row.get("verdict") == "판정 불가"
    ]
    if unresolved:
        limits.append(
            f"광고 의무표시 원문 판정 불가 {len(unresolved)}건은 조건 성립 여부가 불명확합니다."
        )
    return limits


def _unreachable_limit(page: Mapping[str, Any]) -> str:
    """Hidden text no control could reveal is a limitation, not a lower status (decision A4)."""
    unreachable = [
        g
        for g in (page.get("coverage") or {}).get("gaps") or []
        if g.get("kind") == "hidden_text" and g.get("status") == "unresolved"
    ]
    if not unreachable:
        return ""
    return (
        f"열 수 있는 컨트롤을 모두 시도해도 보이지 않은 숨김 글 {len(unreachable)}건은"
        " 상태 판단에서 제외했습니다. 이 글에 조건·예외가 있다면 이 검토는 확인하지 못했습니다."
    )


def _notes(
    status: str,
    actions: list[str],
    page: Mapping[str, Any],
    verification: Mapping[str, Any],
    stop: Mapping[str, Any],
    unreachable: str,
) -> list[str]:
    """Header lines for the markdown: why a review did not reach a verdict, or what qualifies it.

    A judged page lists its items in the tables, so only the lines that are not per-item go up
    top: an incomplete collection, a failed verification, and unreachable hidden text."""
    if status not in (STATUS_PASSED, STATUS_REVIEW):
        return [f"사유: {action}" for action in actions]
    notes = []
    collection = _collection_action(page)
    if collection:
        notes.append(f"수집: {collection}")
    if verification and not verification.get("passed"):
        notes.append(
            f"자동 검증: 미통과({stop.get('reason') or '사유 미기재'})"
            + (f" — {stop['detail']}" if stop.get("detail") else "")
        )
    if unreachable:
        notes.append(f"한계: {unreachable}")
    return notes
