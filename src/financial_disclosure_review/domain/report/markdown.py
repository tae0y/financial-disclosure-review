"""The reviewer-facing report: what to check, the overview, and what to confirm elsewhere.

Kept short on purpose (compacted 2026-09-30). Passes are counts; only open items (부적합·판정
불가) are listed, in one table, as their rubric question with a short legal basis.
Explanation-duty items are one line of topics for the product document, unjudged. Cost, limits
and agent records stay in the Report's other fields.
"""

import re
from collections.abc import Mapping
from typing import Any

PASS = "적합"
_RANK = {"부적합": 0, "판정 불가": 1, PASS: 2}
# The judge opens a reason with how the item's applies_condition resolved, or states a condition
# that held (`…이 존재(성립). `); a reader needs only the finding after it.
_CONDITION_PREFIX = re.compile(r"^applies_condition[^.]*\.\s*")
_HELD_PREFIX = re.compile(r"^[^.]*\(성립\)\.\s*")
# "…이 설명되어 있는가?" reads as a topic once the asking tail and the asides are gone.
_QUESTION_TAIL = re.compile(r"\s*(?:이|가)?\s*(?:설명되어|표시되어|제공되어) 있는가\?$|\?$")
_ASIDE = re.compile(r"\s*\([^)]*\)")
FOOTER = (
    "비용·한계·수집 기록은 API 응답의 report 필드에 있습니다. 게시 여부의 최종 판단은"
    " 컴플라이언스 담당자가 합니다."
)


def _rank(row: Mapping[str, Any]) -> int:
    return _RANK.get(str(row.get("verdict")), 1)


def _cell(text: Any, limit: int = 0) -> str:
    text = " ".join(str(text or "").split()).replace("|", "\\|")
    return text if not limit or len(text) <= limit else text[: limit - 1] + "…"


def _reason(text: Any, limit: int = 80) -> str:
    return _cell(_HELD_PREFIX.sub("", _CONDITION_PREFIX.sub("", str(text or ""))), limit)


def _table(rows: list[list[str]], header: list[str]) -> list[str]:
    return [
        "| " + " | ".join(header) + " |",
        "|" + "|".join(["---"] * len(header)) + "|",
        *["| " + " | ".join(row) + " |" for row in rows],
        "",
    ]


def _basis(text: str) -> str:
    """The first cited document of a basis line, with how many others it names."""
    parts = [p for p in (text or "").split("; ") if p]
    if not parts:
        return "-"
    return parts[0] + (f" 외 {len(parts) - 1}" if len(parts) > 1 else "")


def _labelled(code: str, labels: Mapping[str, Mapping[str, str]]) -> list[str]:
    """Question and short basis cells; without a label the code stands in for the question."""
    label = labels.get(code) or {}
    return [_cell(label.get("question") or code), _cell(_basis(label.get("basis") or ""))]


def _topic(question: str) -> str:
    return _ASIDE.sub("", _QUESTION_TAIL.sub("", question or "")).strip()


def _passed(rows: list[Mapping[str, Any]]) -> str:
    return f"{sum(1 for r in rows if r.get('verdict') == PASS)}/{len(rows)}"


def reader_line(profile: Mapping[str, Any]) -> str:
    """Who the overview is for, as an age band and familiarity only — never the dataset
    persona's name or story, which is synthetic and not the requester's business."""
    attributes = profile.get("attributes") or {}
    parts = []
    age = re.match(r"\s*(\d+)세", str(attributes.get("reader") or ""))
    if age:
        parts.append(f"{int(age.group(1)) // 10 * 10}대")
    if attributes.get("financial_familiarity"):
        parts.append(f"금융 익숙도 {attributes['financial_familiarity']}")
    return " · ".join(parts)


def _open_table(
    display: Mapping[str, Any], disclosure: Mapping[str, Any], labels: Mapping[str, Any]
) -> list[str]:
    rows = [("표시방법", r) for r in display.get("items") or []]
    rows += [("의무표시", r) for r in disclosure.get("original") or []]
    open_rows = sorted(
        ((area, r) for area, r in rows if r.get("verdict") != PASS), key=lambda x: _rank(x[1])
    )
    if not open_rows:
        return ["확인할 항목이 없습니다.", ""]
    return _table(
        [
            [
                area,
                *_labelled(str(r.get("code", "")), labels),
                _cell(r.get("verdict")),
                _reason(r.get("reason")),
            ]
            for area, r in open_rows
        ],
        ["구분", "질문", "근거", "판정", "사유"],
    )


def _overview_lines(
    overview: Mapping[str, Any], disclosure: Mapping[str, Any], labels: Mapping[str, Any]
) -> list[str]:
    """The overview as shown, or why none is shown, then what in it needs checking."""
    lines = []
    reader = reader_line(overview.get("profile") or {})
    if reader:
        lines += [f"독자: {reader}", ""]
    paragraphs = overview.get("overview") or []
    if overview.get("html") and paragraphs:
        lines += [line for p in paragraphs for line in (_cell(p), "")]
    elif overview.get("problems"):
        lines += [f"(싣지 않음: {_cell('; '.join(overview['problems']), 200)})", ""]
    else:
        reason = _cell(overview.get("reason"), 120)
        lines += [f"(개요 없음: {reason})" if reason else "(개요 없음)", ""]
    issues = [
        f"- {_cell((labels.get(str(r.get('code', ''))) or {}).get('question') or r.get('code'))}"
        f" — {r.get('verdict')}: {_reason(r.get('reason'))}"
        for r in sorted(disclosure.get("overview") or [], key=_rank)
        if r.get("verdict") != PASS
    ]
    issues += [
        f"- {_cell(r.get('kind'))} ({_cell(r.get('code'))}): {_reason(r.get('reason'))}"
        for r in disclosure.get("fidelity") or []
        if not r.get("informational")
    ]
    if issues:
        lines += ["개요 확인 사항:", "", *issues, ""]
    return lines


def render_markdown(
    page: Mapping[str, Any],
    classification: Mapping[str, Any],
    display: Mapping[str, Any],
    overview: Mapping[str, Any],
    disclosure: Mapping[str, Any],
    status: str,
    decision: str,
    notes: list[str],
    labels: Mapping[str, Mapping[str, str]] | None = None,
) -> str:
    """`notes` are header lines that explain the verdict (why a review stopped, open gaps)."""
    labels = labels or {}
    product = page.get("product") or {}
    lines = [
        "---",
        "ai-generated: true",
        "human-review: false",
        "---",
        "",
        f"# 검토 결과 — {product.get('product_name') or '(상품명 확인 불가)'}",
        "",
        f"- 판정: **{status}** ({decision})",
        f"- 화면: {page.get('url', '')}",
        # 범위 밖·판정 불가로 끝난 검토는 화면유형이 정해지지 않은 채로 남습니다. `None`이 그대로
        # 찍히면 값이 빠진 것인지 오류인지 구분되지 않으므로 말로 적습니다.
        f"- 유형: {classification.get('product_type') or '(확인 불가)'}"
        f" / {classification.get('page_type') or '(해당 없음)'}",
        *[f"- {_cell(note, 200)}" for note in notes if note],
        "",
    ]
    display_rows = display.get("items") or []
    original = disclosure.get("original") or []
    if not (display_rows or original or overview):
        # Out of scope, or stopped before any check: the header says why.
        return "\n".join([*lines, FOOTER, ""])
    lines += [
        "## 확인할 항목",
        "",
        f"적합: 표시방법 {_passed(display_rows)} · 광고 의무표시 {_passed(original)}"
        f" · 쉬운말 개요 {_passed(disclosure.get('overview') or [])}",
        "",
    ]
    lines += _open_table(display, disclosure, labels)
    lines += ["## 쉬운말 개요", ""]
    lines += _overview_lines(overview, disclosure, labels)
    deferred = disclosure.get("deferred") or []
    if deferred:
        topics = " · ".join(
            _cell(_topic(str(r.get("question") or r.get("code")))) for r in deferred
        )
        lines += [
            f"## 상품설명서에서 확인할 설명의무 ({len(deferred)}개)",
            "",
            "광고 페이지로는 판정하지 않았습니다(청약 단계의 의무). " + topics,
            "",
        ]
    return "\n".join([*lines, FOOTER, ""])
