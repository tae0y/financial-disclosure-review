"""The reviewer-facing report: page, display, ad disclosures, then the overview and its check.

Kept short on purpose. Items read as their rubric question and legal basis, not their code; only
open items (부적합·판정 불가) are listed and passes are a count. Explanation-duty items are listed
for the product documents, unjudged. Cost, limits and agent records stay in the Report's other
fields.
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
FOOTER = (
    "비용, 한계와 가정, 수집 기록은 API 응답의 report 필드(cost, limits, summary)에"
    " 있습니다. 게시 여부의 최종 판단은 컴플라이언스 담당자가 합니다."
)


def _rank(row: Mapping[str, Any]) -> int:
    return _RANK.get(str(row.get("verdict")), 1)


def _cell(text: Any, limit: int = 0) -> str:
    text = " ".join(str(text or "").split()).replace("|", "\\|")
    return text if not limit or len(text) <= limit else text[: limit - 1] + "…"


def _reason(text: Any, limit: int = 120) -> str:
    return _cell(_HELD_PREFIX.sub("", _CONDITION_PREFIX.sub("", str(text or ""))), limit)


def _table(rows: list[list[str]], header: list[str]) -> list[str]:
    return [
        "| " + " | ".join(header) + " |",
        "|" + "|".join(["---"] * len(header)) + "|",
        *["| " + " | ".join(row) + " |" for row in rows],
        "",
    ]


def _labelled(code: str, labels: Mapping[str, Mapping[str, str]]) -> list[str]:
    """Question and basis cells; without a label the code stands in for the question."""
    label = labels.get(code) or {}
    return [_cell(label.get("question") or code), _cell(label.get("basis") or "-")]


def _disclosure_section(
    rows: list[Mapping[str, Any]], labels: Mapping[str, Mapping[str, str]]
) -> list[str]:
    if not rows:
        return ["(검토하지 않음)", ""]
    open_rows = sorted((row for row in rows if row.get("verdict") != PASS), key=_rank)
    lines = [f"적합 {len(rows) - len(open_rows)}건, 확인 필요 {len(open_rows)}건입니다.", ""]
    if open_rows:
        lines += _table(
            [
                [
                    *_labelled(str(row.get("code", "")), labels),
                    _cell(row.get("verdict")),
                    _reason(row.get("reason")),
                ]
                for row in open_rows
            ],
            ["질문", "근거", "판정", "사유"],
        )
    return lines


def _overview_lines(overview: Mapping[str, Any]) -> list[str]:
    """The overview paragraphs as shown, or why none is shown."""
    paragraphs = overview.get("overview") or []
    if overview.get("html") and paragraphs:
        return [line for p in paragraphs for line in (_cell(p), "")]
    problems = overview.get("problems") or []
    if problems:
        return [f"(싣지 않음: {_cell('; '.join(problems), 200)})", ""]
    reason = _cell(overview.get("reason"), 120)
    return [f"(개요 없음: {reason})" if reason else "(개요 없음)", ""]


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
        *[f"- {_cell(note, 240)}" for note in notes if note],
        "",
    ]
    display_rows = display.get("items") or []
    if not (display_rows or disclosure.get("original") or overview):
        # Out of scope, or stopped before any check: the header says why.
        return "\n".join([*lines, FOOTER, ""])
    lines += ["## 1. 표시방법", ""]
    lines += (
        _table(
            [
                [
                    *_labelled(str(row.get("code", "")), labels),
                    _cell(row.get("verdict")),
                    "" if row.get("verdict") == PASS else _reason(row.get("reason")),
                ]
                for row in display_rows
            ],
            ["질문", "근거", "판정", "사유"],
        )
        if display_rows
        else ["(검토하지 않음)", ""]
    )
    lines += ["## 2. 광고 의무표시 (원문)", ""]
    lines += _disclosure_section(disclosure.get("original") or [], labels)

    lines += ["## 3. 쉬운말 개요", ""]
    reader = ((overview.get("profile") or {}).get("attributes") or {}).get("reader")
    if reader:
        lines += [f"독자: {_cell(reader, 100)}", ""]
    lines += _overview_lines(overview)
    lines += ["## 4. 쉬운말 개요의 광고 의무표시", ""]
    lines += _disclosure_section(disclosure.get("overview") or [], labels)
    changed = [row for row in disclosure.get("fidelity") or [] if not row.get("informational")]
    if changed:
        lines += ["원문과 달라진 곳:", ""]
        lines += [
            f"- {_cell(row.get('kind'))} ({_cell(row.get('code'))}): {_reason(row.get('reason'))}"
            for row in changed
        ]
        lines.append("")
    deferred = disclosure.get("deferred") or []
    if deferred:
        lines += [
            "## 5. 상품설명서에서 확인할 설명의무 항목",
            "",
            "설명의무는 청약 단계 상품설명서·설명화면의 의무라서 이 광고 페이지로는 판정하지"
            f" 않았습니다. 다음 {len(deferred)}개 항목을 상품설명서에서 확인해 주세요.",
            "",
            *[f"- {_cell(row.get('question') or row.get('code'))}" for row in deferred],
            "",
        ]
    return "\n".join([*lines, FOOTER, ""])
