"""Fact-ledger check of the persona explanation: code decides presence, the model only meaning."""

from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel

from ...core.text import locate_quote
from ...llm.client import call_ask
from ..plain_language.contract import counter_ones, number_set, strip_ws

LEDGER_TASK = """사실 원장(items)의 각 값이 독자 맞춤 설명문(text)에서 뜻으로 보존됐는지 판단합니다.
items의 각 항목은 fact_id, kind(number/period/limit/target/condition/exception/penalty), 원문 표기
그대로의 value, 원문에서 그 값 주변 문맥(original_context)으로 구성됩니다. 이 값들은 설명문에 글자
그대로는 없다고 코드가 이미 확인한 것입니다. 각 항목마다 다음 중 하나로 답합니다.
- 보존: 설명문이 같은 값·조건·예외·불이익을 다른 표기로 분명히 말함(예: "30만원"을 "300,000원"으로).
- 약화: 설명문에 관련 내용은 있으나 값·범위·조건이 흐려지거나 불이익이 덜 위험하게 읽힘.
- 누락: 설명문에서 이 값의 뜻을 찾을 수 없음.
보존이나 약화이면 quote에 그 판단의 근거가 되는 설명문 문장을 그대로 인용합니다(요약·수정 금지).
누락이면 quote는 빈 문자열입니다. reason에는 결론과 한두 문장의 짧은 근거만 씁니다.
준법 여부나 적합·부적합은 판단하지 않습니다."""
ORIGINAL_CONTEXT_CHARS = 60
UNMAPPED_SOURCE = "unmapped"


class LedgerSemantic(BaseModel):
    fact_id: str
    verdict: Literal["보존", "누락", "약화"]
    quote: str
    reason: str


class LedgerSemantics(BaseModel):
    items: list[LedgerSemantic]


def _contains(text: str, value: str) -> bool:
    needle = strip_ws(value)
    return bool(needle) and needle in strip_ws(text)


def _context(text: str, value: str) -> str:
    span = locate_quote(text, value)
    if span is None:
        return ""
    start, end = span
    return text[max(0, start - ORIGINAL_CONTEXT_CHARS) : end + ORIGINAL_CONTEXT_CHARS]


def _related_units(fact: Mapping[str, Any], units: Sequence[Mapping[str, Any]]) -> list[str]:
    if "unit_ids" in fact:
        return list(fact["unit_ids"])
    return [u["unit_id"] for u in units if fact.get("card_id") in (u.get("card_ids") or [])]


def _informational(unit_ids: Sequence[str], by_id: Mapping[str, Mapping[str, Any]]) -> bool:
    """True when every related unit went back to the original text (or there is none)."""
    return all(by_id[u].get("status") == "reverted" for u in unit_ids if u in by_id)


def _source_ids(
    own: Sequence[str], unit_ids: Sequence[str], by_id: Mapping[str, Mapping[str, Any]]
) -> list[str]:
    """Never empty: the fact's own source, else its units' sources, else an explicit marker."""
    ids = [s for s in own if s]
    if not ids:
        ids = list(
            dict.fromkeys(s for u in unit_ids if u in by_id for s in by_id[u].get("source_ids", []))
        )
    return ids or [UNMAPPED_SOURCE]


def judge_ledger_semantics(
    pending: Sequence[Mapping[str, Any]],
    original_text: str,
    explanation_text: str,
    model: str,
    ask,
) -> dict[str, dict]:
    """One model call over every fact whose value is not literally in the explanation."""
    wanted = [f["fact_id"] for f in pending]

    def check(answer: dict) -> list[str]:
        seen = [j["fact_id"] for j in answer["items"]]
        if sorted(seen) != sorted(wanted):
            return [f"fact_ids {sorted(seen)} != {sorted(wanted)}"]
        problems = []
        for j in answer["items"]:
            if not j["reason"].strip():
                problems.append(f"{j['fact_id']}: 근거 없음")
            if j["verdict"] != "누락" and not (
                j["quote"] and locate_quote(explanation_text, j["quote"])
            ):
                problems.append(f"{j['fact_id']}: quote가 설명문에 없음")
        return problems

    def salvage(answer: dict, problems: list[str]) -> dict:
        keyed = {p.split(":", 1)[0].strip() for p in problems}
        bad = set(wanted) if not keyed <= set(wanted) else keyed
        note = "; ".join(problems)[:150]
        kept = {j["fact_id"]: j for j in answer["items"] if j["fact_id"] not in bad}
        return {
            "items": [
                kept.get(f)
                or {
                    "fact_id": f,
                    "verdict": "판정 불가",
                    "quote": "",
                    "reason": f"검증 실패로 판정 불가 처리: {note}",
                }
                for f in wanted
            ]
        }

    answer = call_ask(
        ask,
        model,
        LedgerSemantics,
        LEDGER_TASK,
        check,
        "low",
        salvage,
        items=[
            {
                "fact_id": f["fact_id"],
                "kind": f["kind"],
                "value": f["value"],
                "original_context": _context(original_text, f["value"]),
            }
            for f in pending
        ],
        text=explanation_text,
    )
    return {j["fact_id"]: j for j in answer["items"]}


def _added_numbers(
    units: Sequence[Mapping[str, Any]],
    original_text: str,
    explanation_text: str,
    by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict]:
    extra = sorted(
        number_set(explanation_text) - number_set(original_text) - counter_ones(explanation_text)
    )
    rows = []
    for number in extra:
        unit_ids = [
            u["unit_id"]
            for u in units
            if u.get("status") == "accepted"
            and number in number_set(f"{u.get('explanation', '')} {u.get('analogy', '')}")
        ]
        rows.append(
            {
                "code": "NUM",
                "kind": "추가",
                "source_ids": _source_ids([], unit_ids, by_id),
                "unit_ids": unit_ids,
                "quote": number,
                "reason": f"설명문에 원문에 없는 수치 {number}가 있음",
                "decided_by": "code",
                "informational": _informational(unit_ids, by_id) if unit_ids else False,
            }
        )
    return rows


def check_ledger(
    fact_ledger: Sequence[Mapping[str, Any]],
    units: Sequence[Mapping[str, Any]],
    original_text: str,
    explanation_text: str,
    model: str,
    ask,
) -> dict:
    """{"ledger": 사실 원장 행별 대조, "fidelity": 누락·약화·추가·판정 불가 행}을 돌려준다."""
    by_id = {u["unit_id"]: u for u in units}
    rows = []
    for fact in fact_ledger:
        present = _contains(explanation_text, fact["value"])
        rows.append(
            {
                "fact_id": fact["fact_id"],
                "card_id": fact.get("card_id", ""),
                "kind": fact["kind"],
                "value": fact["value"],
                "source_ids": _source_ids(
                    [fact.get("source_id", "")], _related_units(fact, units), by_id
                ),
                "unit_ids": _related_units(fact, units),
                "in_original": _contains(original_text, fact["value"]),
                "in_explanation": present,
                "decided_by": "code" if present else "model",
                "verdict": "보존" if present else "",
                "quote": fact["value"] if present else "",
                "reason": "설명문에 원문 값이 그대로 있음" if present else "",
            }
        )

    pending = [r for r in rows if not r["in_explanation"]]
    if pending:
        judged = judge_ledger_semantics(pending, original_text, explanation_text, model, ask)
        for row in pending:
            j = judged[row["fact_id"]]
            row.update(verdict=j["verdict"], quote=j["quote"], reason=j["reason"])

    fidelity = [
        {
            "code": r["fact_id"],
            "kind": r["verdict"],
            "source_ids": r["source_ids"],
            "unit_ids": r["unit_ids"],
            "quote": r["quote"],
            "reason": r["reason"],
            "decided_by": r["decided_by"],
            "informational": _informational(r["unit_ids"], by_id),
        }
        for r in rows
        if r["verdict"] != "보존"
    ]
    fidelity += _added_numbers(units, original_text, explanation_text, by_id)
    return {"ledger": rows, "fidelity": fidelity}
