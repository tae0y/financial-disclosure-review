"""The reviewer-facing report: page, display, explanation duty, then the draft and its duty result.

Kept short on purpose. Items read as their rubric question and legal basis, not their code;
explanation-duty twins (설명NN/FNN) read as one topic; only open items (부적합·판정 불가) are
listed and passes are a count. Cost, limits and agent records stay in the Report's other fields.
"""

import re
from collections.abc import Mapping
from html.parser import HTMLParser
from typing import Any

from ...core.duty_codes import duty_topic

PASS = "적합"
# Worst first: a topic whose twins disagree shows the worse verdict.
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


def _topics(rows: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """One row per duty topic, keyed by its 설명 code, carrying the worst verdict of the pair."""
    by_topic: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        topic = duty_topic(str(row.get("code", "")))
        kept = by_topic.get(topic)
        if kept is None or _rank(row) < _rank(kept):
            by_topic[topic] = {**row, "code": topic}
    return list(by_topic.values())


def _duty_section(
    rows: list[Mapping[str, Any]], labels: Mapping[str, Mapping[str, str]]
) -> list[str]:
    if not rows:
        return ["(검토하지 않음)", ""]
    topics = _topics(rows)
    open_rows = sorted((row for row in topics if row.get("verdict") != PASS), key=_rank)
    lines = [f"적합 {len(topics) - len(open_rows)}건, 확인 필요 {len(open_rows)}건입니다.", ""]
    if open_rows:
        lines += _table(
            [
                [
                    *_labelled(row["code"], labels),
                    _cell(row.get("verdict")),
                    _reason(row.get("reason")),
                ]
                for row in open_rows
            ],
            ["질문", "근거", "판정", "사유"],
        )
    return lines


class _Draft(HTMLParser):
    """The assembled draft as ("source", text) and ("unit", {role: text}) in page order."""

    def __init__(self) -> None:
        super().__init__()
        self.items: list[tuple[str, Any]] = []
        self._unit: dict[str, str] | None = None
        self._role = ""
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "section":
            self._unit = {}
        elif tag == "p":
            self._role = dict(attrs).get("data-role") or "source"
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._role:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "p" and self._role:
            text = " ".join("".join(self._text).split())
            if self._unit is not None:
                self._unit[self._role] = text
            elif text:
                self.items.append(("source", text))
            self._role = ""
        elif tag == "section" and self._unit is not None:
            self.items.append(("unit", self._unit))
            self._unit = None


def _draft_lines(plain: Mapping[str, Any]) -> list[str]:
    """The explained lines of the draft in page order, as 원문 → 쉬운말. Lines kept as they were
    read the same as the page, so they are left out."""
    if plain.get("html"):
        parser = _Draft()
        parser.feed(str(plain["html"]))
        units = [value for kind, value in parser.items if kind == "unit"]
    elif "units" in plain:  # No assembled page: the accepted units alone.
        units = [
            {"exact-fact": u.get("exact_fact"), **u}
            for u in plain.get("units") or []
            if u.get("status") == "accepted"
        ]
    else:  # A checkpoint from before the persona explanation keeps only its accepted blocks.
        return [f"- {_cell(b.get('text'))}" for b in plain.get("accepted_blocks") or []]
    return [
        f"- **원문** {_cell(unit.get('exact-fact'), 60)}"
        f" → **쉬운말** {_cell(unit.get('explanation'))}"
        + (f" (비유: {_cell(unit['analogy'])})" if unit.get("analogy") else "")
        for unit in units
    ]


def render_markdown(
    page: Mapping[str, Any],
    classification: Mapping[str, Any],
    display: Mapping[str, Any],
    plain: Mapping[str, Any],
    duty: Mapping[str, Any],
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
    if not (display_rows or duty.get("original") or plain):
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
    lines += ["## 2. 설명의무 (원문)", ""]
    lines += _duty_section(duty.get("original") or [], labels)

    lines += ["## 3. 쉬운말 초안", ""]
    reader = ((plain.get("profile") or {}).get("attributes") or {}).get("reader")
    if reader:
        lines += [f"독자: {_cell(reader, 100)}", ""]
    units = plain.get("units") or []
    reverted = sum(1 for u in units if u.get("status") == "reverted") or len(
        plain.get("contract_errors") or []
    )
    if reverted:
        lines += [
            f"원문 유지 {reverted}건: 설명이 원문 사실을 지키지 못해 원문 문장으로 되돌렸습니다.",
            "",
        ]
    lines += [*(_draft_lines(plain) or ["(초안 없음)"]), ""]
    lines += ["## 4. 쉬운말 초안의 설명의무", ""]
    lines += _duty_section(duty.get("plain") or [], labels)
    changed = [row for row in duty.get("fidelity") or [] if not row.get("informational")]
    if changed:
        lines += ["원문과 뜻이 달라진 곳:", ""]
        lines += [f"- {_cell(row.get('kind'))}: {_reason(row.get('reason'))}" for row in changed]
        lines.append("")
    return "\n".join([*lines, FOOTER, ""])
