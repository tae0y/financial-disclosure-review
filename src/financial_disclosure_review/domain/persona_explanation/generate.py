"""Entry point of persona_explanation: one drafting call, then code keeps only traceable units."""

import re
from collections.abc import Mapping, Sequence
from html import escape
from pathlib import Path
from typing import Any

from ...core.context import Context
from ...core.text import locate_quote
from ...llm.client import ask, call_ask
from ..plain_language.contract import (
    FORBIDDEN_ABSOLUTE_PHRASES,
    counter_ones,
    has_phrase,
    number_set,
    strip_ws,
)
from .ledger import build_fact_ledger
from .profiles import resolve_profile
from .prompts import PERSONA_TASK
from .schema import PersonaUnitDrafts

RISK_CARD_KINDS = {"rate_claim", "fee_claim", "warning"}
RISK_TERMS_RE = re.compile(r"리볼빙|금리|이자|연체|위약금|수수료|이월")
VERDICT_RE = re.compile(r"적합|부적합|위반|합법|불법|문제없")
BENEFIT_KINDS = {"benefit_claim"}
CARD_FIELDS = (
    "id",
    "kind",
    "subject",
    "claim",
    "qualifiers",
    "exceptions",
    "numbers",
    "quote",
    "source_id",
)
# Controls a published explanation needs around it. They are listed so the report can show them;
# this node neither implements nor judges them.
CONTROLS = {
    "ui": ["AI 생성 고지", "원문 보기 전환", "오류 신고"],
    "governance": ["사람 승인", "변경 관리", "프로필 검토"],
    "note": "화면·운영 통제 목록으로 문서화만 하며, 이 노드는 이 항목들을 판정하지 않음",
}


MANDATORY_ATTR = ' data-mandatory="true"'


def _source_html(source: Mapping[str, Any]) -> str:
    """One original line; a mandatory disclosure (감사 P2-12) is marked and set in bold."""
    text = escape(source["text"])
    if source.get("mandatory"):
        return (
            f'<p data-source-id="{escape(source["source_id"])}"{MANDATORY_ATTR}>'
            f"<strong>{text}</strong></p>"
        )
    return f'<p data-source-id="{escape(source["source_id"])}">{text}</p>'


def _unit_html(unit: Mapping[str, Any], mandatory: bool = False) -> str:
    fact = escape(unit["exact_fact"])
    parts = [
        f'<section data-unit-id="{escape(unit["unit_id"])}"'
        f' data-source-ids="{escape(" ".join(unit["source_ids"]))}"'
        f"{MANDATORY_ATTR if mandatory else ''}>",
        f'<p data-role="exact-fact">{f"<strong>{fact}</strong>" if mandatory else fact}</p>',
        f'<p data-role="explanation">{escape(unit["explanation"])}</p>',
    ]
    if unit["analogy"]:
        parts.append(f'<p data-role="analogy">{escape(unit["analogy"])}</p>')
    return "".join(parts) + "</section>"


def assemble_html(sources: Sequence[Mapping[str, Any]], units: Sequence[Mapping[str, Any]]) -> str:
    """Every source in page order; an accepted unit replaces only its first source line.

    A source flagged `mandatory` (a 의무표시 block, labelled by display_check) stays emphasised,
    and so does a unit that stands in for any mandatory line it covers."""
    by_first = {u["replaces"]: u for u in units if u["status"] == "accepted"}
    mandatory = {s["source_id"] for s in sources if s.get("mandatory")}
    return "".join(
        _unit_html(
            by_first[s["source_id"]], bool(mandatory & set(by_first[s["source_id"]]["source_ids"]))
        )
        if s["source_id"] in by_first
        else _source_html(s)
        for s in sources
    )


def _analogy_block(cited: Sequence[Mapping[str, Any]], texts: Sequence[str], policy: str) -> str:
    """Why the unit may not carry an analogy, or "" when it may."""
    if policy == "none":
        return "프로필 비유 정책이 none"
    risky = sorted({c.get("kind", "") for c in cited} & RISK_CARD_KINDS)
    if risky:
        return f"위험 개념 카드({', '.join(risky)})"
    term = next((m.group(0) for t in texts if (m := RISK_TERMS_RE.search(t))), "")
    if term:
        return f"위험 개념 언급({term})"
    if policy == "benefit_only" and not all(c.get("kind") in BENEFIT_KINDS for c in cited):
        return "benefit_only 정책인데 혜택 카드가 아닌 카드를 설명함"
    return ""


def review_unit(
    unit_id: str,
    draft: Mapping[str, Any],
    cards_by_id: Mapping[str, Mapping[str, Any]],
    sources_by_id: Mapping[str, Mapping[str, Any]],
    order: Mapping[str, int],
    ledger: Sequence[Mapping[str, Any]],
    analogy_policy: str,
) -> dict:
    """One drafted unit after the code checks: status accepted or reverted, with its problems."""
    problems: list[str] = []
    notes: list[str] = []
    card_ids = list(dict.fromkeys(draft.get("card_ids") or []))
    source_ids = list(dict.fromkeys(draft.get("source_ids") or []))
    exact = (draft.get("exact_fact") or "").strip()
    explanation = (draft.get("explanation") or "").strip()
    analogy = (draft.get("analogy") or "").strip()

    if not card_ids:
        problems.append("card_ids가 비어 있음")
    unknown_cards = [c for c in card_ids if c not in cards_by_id]
    if unknown_cards:
        problems.append(f"알 수 없는 card_id: {', '.join(unknown_cards)}")
    cited = [cards_by_id[c] for c in card_ids if c in cards_by_id]
    cited_sources = {c.get("source_id") for c in cited}

    if not source_ids:
        problems.append("source_ids가 비어 있음")
    unknown_sources = [s for s in source_ids if s not in sources_by_id]
    if unknown_sources:
        problems.append(f"알 수 없는 source_id: {', '.join(unknown_sources)}")
    outside = [s for s in source_ids if s in sources_by_id and s not in cited_sources]
    if outside:
        problems.append(f"인용 카드의 출처가 아닌 source_id: {', '.join(outside)}")
    known = sorted((s for s in source_ids if s in sources_by_id), key=lambda s: order[s])
    replaces = known[0] if known else ""
    source_text = " ".join(sources_by_id[s]["text"] for s in known)

    if not explanation:
        problems.append("explanation이 비어 있음")
    if not exact or not locate_quote(source_text, exact):
        problems.append("exact_fact를 근거 원문에서 확인할 수 없음")

    if analogy:
        why = _analogy_block(cited, [source_text, exact, explanation, analogy], analogy_policy)
        if why:
            notes.append(f"analogy_dropped: {why}")
            analogy = ""

    generated = f"{explanation} {analogy}"
    extra = sorted(number_set(generated) - number_set(source_text) - counter_ones(generated))
    if extra:
        problems.append(f"근거 원문에 없는 수치: {', '.join(extra)}")

    # The replaced line is hidden behind the section, so the facts of every card on it must
    # survive too, not only those of the cards the unit chose to cite.
    required_cards = set(card_ids) | {
        c_id for c_id, c in cards_by_id.items() if replaces and c.get("source_id") == replaces
    }
    kept = strip_ws(exact) + "\n" + strip_ws(explanation)
    missing = [
        f["fact_id"]
        for f in ledger
        if f["card_id"] in required_cards and strip_ws(f["value"]) not in kept
    ]
    if missing:
        problems.append(f"사실 원장 값 누락: {', '.join(missing)}")

    added = [
        p
        for p in FORBIDDEN_ABSOLUTE_PHRASES
        if has_phrase(generated, p) and not has_phrase(source_text, p)
    ]
    if added:
        problems.append(f"원문에 없는 단정·최상급 표현: {', '.join(added)}")
    verdicts = sorted(set(VERDICT_RE.findall(generated)))
    if verdicts:
        problems.append(f"판정 표현 사용: {', '.join(verdicts)}")

    return {
        "unit_id": unit_id,
        "card_ids": card_ids,
        "source_ids": source_ids,
        "replaces": replaces,
        "exact_fact": exact,
        "explanation": explanation,
        "analogy": analogy,
        "persona_question_answered": (draft.get("persona_question_answered") or "").strip(),
        "status": "reverted" if problems else "accepted",
        "problems": problems + notes,
    }


def _structural_problems(
    answer: Mapping[str, Any],
    cards_by_id: Mapping[str, Any],
    sources_by_id: Mapping[str, Any],
) -> list[str]:
    """Problems worth one retry: an empty answer, empty fields, ids that do not exist."""
    items = answer.get("items") or []
    if not items:
        return ["items: 설명 단위가 없음"]
    problems = []
    for number, draft in enumerate(items, 1):
        empty = [
            key
            for key in ("card_ids", "source_ids", "exact_fact", "explanation")
            if not draft.get(key) or (isinstance(draft[key], str) and not draft[key].strip())
        ]
        if empty:
            problems.append(f"u{number}: 빈 필드 {', '.join(empty)}")
        bad_cards = [c for c in draft.get("card_ids") or [] if c not in cards_by_id]
        bad_sources = [s for s in draft.get("source_ids") or [] if s not in sources_by_id]
        if bad_cards or bad_sources:
            problems.append(f"u{number}: 없는 id {', '.join(bad_cards + bad_sources)}")
    return problems


def _fallback(
    status: str,
    reason: str,
    profile: dict,
    ledger: list[dict],
    sources: Sequence[Mapping[str, Any]],
) -> dict:
    return {
        "status": status,
        "reason": reason,
        "profile": profile,
        "fact_ledger": [{**f, "unit_ids": []} for f in ledger],
        "units": [],
        "html": assemble_html(sources, []),
        "controls": CONTROLS,
    }


def generate_persona_explanation(
    sources: Sequence[Mapping[str, Any]],
    cards: Sequence[Mapping[str, Any]],
    classification: Mapping[str, Any],
    ctx: Context,
    feedback: Sequence[Mapping[str, Any]] = (),
    ask=ask,
    profile_id: str | None = None,
    profiles_path: str | Path | None = None,
    profile: dict | None = None,
) -> dict:
    """독자 맞춤 설명 생성. PersonaExplanation의 모든 필드를 돌려준다.

    {status, reason, profile, fact_ledger, units, html, controls}. 모델 호출은 최대 한 번(구조가
    깨진 답에 한해 한 번 재질문)이며, 검증에 걸린 단위는 원문 줄로 남는다. `profile`이 주어지면
    (choose_profile의 결과) 다시 고르지 않고 그대로 쓴다: 재시도도 같은 독자로 설명한다.
    """
    if profile is None:
        wanted_profile = profile_id if profile_id is not None else ctx.persona_profile
        profile = resolve_profile(wanted_profile, profiles_path)
    ledger = build_fact_ledger(cards)
    if not sources:
        return _fallback("판정 불가", "설명할 원문 출처(sources)가 없음", profile, ledger, sources)
    if profile["status"] != "적용":
        return _fallback(
            "원문 대체", f"페르소나 프로필 무효: {profile['reason']}", profile, ledger, sources
        )
    if not cards:
        return _fallback(
            "원문 대체", "증거 카드가 없어 설명을 만들지 않음", profile, ledger, sources
        )

    cards_by_id = {c["id"]: c for c in cards}
    sources_by_id = {s["source_id"]: s for s in sources}
    order = {s["source_id"]: i for i, s in enumerate(sources)}
    cited_sources = {c.get("source_id") for c in cards}
    own_feedback = [
        {
            "source_id": f.get("source_id", ""),
            "reason": f.get("reason", ""),
            "requested_change": f.get("requested_change", ""),
        }
        for f in feedback
        if f.get("module") == "persona_explanation"
    ]
    extra = {"previous_feedback": own_feedback} if own_feedback else {}

    answer = call_ask(
        ask,
        ctx.model,
        PersonaUnitDrafts,
        PERSONA_TASK,
        lambda a: _structural_problems(a, cards_by_id, sources_by_id),
        "medium",
        # A second broken answer is kept as is: review_unit reverts every unit it cannot trace,
        # so the graph goes on with the original text instead of stopping.
        lambda a, _problems: a,
        product_type=classification.get("product_type"),
        profile=profile["attributes"],
        cards=[{k: c.get(k) for k in CARD_FIELDS} for c in cards],
        sources=[
            {"source_id": s["source_id"], "text": s["text"]}
            for s in sources
            if s["source_id"] in cited_sources
        ],
        fact_ledger=[
            {
                "fact_id": f["fact_id"],
                "card_id": f["card_id"],
                "kind": f["kind"],
                "value": f["value"],
            }
            for f in ledger
        ],
        **extra,
    )

    policy = profile["attributes"]["analogy_policy"]
    units: list[dict] = []
    explained_lines: set[str] = set()
    for number, draft in enumerate(answer.get("items") or [], 1):
        unit = review_unit(f"u{number}", draft, cards_by_id, sources_by_id, order, ledger, policy)
        if unit["status"] == "accepted" and unit["replaces"] in explained_lines:
            unit["status"] = "reverted"
            unit["problems"].insert(0, f"다른 단위가 {unit['replaces']} 줄을 이미 설명함")
        if unit["status"] == "accepted":
            explained_lines.add(unit["replaces"])
        units.append(unit)

    fact_ledger = []
    for fact in ledger:
        related = [
            u["unit_id"]
            for u in units
            if fact["card_id"] in u["card_ids"]
            or (u["replaces"] and u["replaces"] == fact["source_id"])
        ]
        fact_ledger.append({**fact, "unit_ids": related})

    accepted = [u for u in units if u["status"] == "accepted"]
    reverted = len(units) - len(accepted)
    if accepted:
        status = "완료"
        reason = f"{reverted}개 단위는 코드 검증에 걸려 원문으로 대체됨" if reverted else ""
    else:
        status = "원문 대체"
        reason = (
            "모든 설명 단위가 코드 검증에 걸려 원문으로 대체됨"
            if units
            else "모델이 설명 단위를 내지 않아 원문을 그대로 둠"
        )
    return {
        "status": status,
        "reason": reason,
        "profile": profile,
        "fact_ledger": fact_ledger,
        "units": units,
        "html": assemble_html(sources, units),
        "controls": CONTROLS,
    }
