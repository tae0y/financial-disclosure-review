"""Entry point of persona_explanation: a two-paragraph plain overview beside the page — a summary
of the page, then advice on the explanation-duty items this reader should check elsewhere."""

import re
from collections.abc import Mapping, Sequence
from html import escape
from pathlib import Path
from typing import Any

from ...core.context import Context
from ...knowledge.rubrics import item_scope
from ...llm.client import ask, call_ask
from ..ad_disclosure_check.rubric import (
    OVERVIEW_REQUIRED,
    deferred_explanation_items,
    load_disclosure_items,
)
from ..plain_language.contract import (
    FORBIDDEN_ABSOLUTE_PHRASES,
    counter_ones,
    has_phrase,
    number_set,
)
from .profiles import resolve_profile
from .prompts import PERSONA_TASK
from .schema import OverviewDraft

MAX_PARAGRAPHS = 2
MIN_ADVICE_CODES = 2
MAX_ADVICE_CODES = 5
# The roles of the two paragraphs, in order; only the summary is judged against the ad disclosures.
ROLES = ("summary", "advice")
MAX_CHARS = 1200
ENUM_MARKER = re.compile(r"(?<!\S)\(?\d{1,2}[)）.](?=\s)")
VERDICT_RE = re.compile(r"적합|부적합|위반|합법|불법|문제없")
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
# Controls a published overview needs around it. They are listed so the report can show them;
# this node neither implements nor judges them.
CONTROLS = {
    "ui": ["AI 생성 고지", "원문 보기 전환", "오류 신고"],
    "governance": ["사람 승인", "변경 관리", "프로필 검토"],
    "note": "화면·운영 통제 목록으로 문서화만 하며, 이 노드는 이 항목들을 판정하지 않음",
}


def overview_html(paragraphs: Sequence[str]) -> str:
    """The overview alone; the page it summarises is shown beside it, not inside it. The first
    paragraph is the summary, the second the advice."""
    if not paragraphs:
        return ""
    body = "".join(
        f'<p data-role="{role}">{escape(p)}</p>' for role, p in zip(ROLES, paragraphs, strict=False)
    )
    return f'<section data-role="overview">{body}</section>'


def advice_problems(answer: Mapping[str, Any], allowed: Sequence[str]) -> list[str]:
    """The advice paragraph must exist and name 2–5 explanation-duty items the product has."""
    if not allowed:
        return []
    problems = []
    if not (answer.get("advice") or "").strip():
        problems.append("권고 문단(advice)이 비어 있음")
    codes = list(dict.fromkeys(answer.get("advice_codes") or []))
    unknown = [c for c in codes if c not in allowed]
    if unknown:
        problems.append(f"설명의무 항목에 없는 advice_codes: {', '.join(unknown)}")
    known = [c for c in codes if c in allowed]
    if not MIN_ADVICE_CODES <= len(known) <= MAX_ADVICE_CODES:
        problems.append(
            f"권고 항목 {len(known)}개(advice_codes는 {MIN_ADVICE_CODES}~{MAX_ADVICE_CODES}개)"
        )
    return problems


def _draft_paragraphs(answer: Mapping[str, Any]) -> list[str]:
    return [
        text
        for text in ((answer.get("summary") or "").strip(), (answer.get("advice") or "").strip())
        if text
    ]


def overview_problems(paragraphs: Sequence[str], source_text: str) -> list[str]:
    """Code checks of a drafted overview against the page text; empty when it may be shown."""
    kept = [p.strip() for p in paragraphs if p and p.strip()]
    if not kept:
        return ["개요 문단이 없음"]
    problems = []
    if len(kept) > MAX_PARAGRAPHS:
        problems.append(f"문단 {len(kept)}개(최대 {MAX_PARAGRAPHS}개)")
    chars = sum(len(p) for p in kept)
    if chars > MAX_CHARS:
        problems.append(f"개요 {chars}자(최대 {MAX_CHARS}자)")
    # "1) …", "(2) …", "3. …" number a list; they state no fact, so they are not checked.
    generated = ENUM_MARKER.sub(" ", " ".join(kept))
    extra = sorted(number_set(generated) - number_set(source_text) - counter_ones(generated))
    if extra:
        problems.append(f"원문에 없는 수치: {', '.join(extra)}")
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
    return problems


def _fallback(status: str, reason: str, profile: dict) -> dict:
    return {
        "status": status,
        "reason": reason,
        "profile": profile,
        "overview": [],
        "advice_codes": [],
        "problems": [],
        "html": "",
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
    """독자 맞춤 쉬운말 개요 생성. PersonaExplanation의 모든 필드를 돌려준다.

    {status, reason, profile, overview, advice_codes, problems, html, controls}. `overview`는
    [요약 문단, 권고 문단]이다. 모델 호출은 한 번이며, 코드
    검사에 걸린 답은 한 번 다시 묻는다. 두 번째 답도 걸리면 개요를 싣지 않고(원문 대체) 문제를
    `problems`에 남겨 검증이 재생성을 요청하게 한다. `profile`이 주어지면(choose_profile의 결과)
    다시 고르지 않고 그대로 쓴다: 재시도도 같은 독자로 쓴다.
    """
    if profile is None:
        wanted_profile = profile_id if profile_id is not None else ctx.persona_profile
        profile = resolve_profile(wanted_profile, profiles_path)
    if not sources:
        return _fallback("판정 불가", "요약할 원문 출처(sources)가 없음", profile)
    if profile["status"] != "적용":
        return _fallback("원문 대체", f"페르소나 프로필 무효: {profile['reason']}", profile)
    if not cards:
        return _fallback("원문 대체", "증거 카드가 없어 개요를 만들지 않음", profile)

    source_text = " ".join(s.get("text", "") for s in sources)
    cited_sources = {c.get("source_id") for c in cards}
    disclosure_items = [
        {"code": i["code"], "criterion": i["criterion"]}
        for i in load_disclosure_items(ctx.db_path)
        if i["code"] in OVERVIEW_REQUIRED and not item_scope(i, classification)
    ]
    explanation_items = [
        {"code": i["code"], "question": i["question"]}
        for i in deferred_explanation_items(ctx.db_path, classification.get("product_type"))
    ]
    allowed = [i["code"] for i in explanation_items]

    def check(answer: Mapping[str, Any]) -> list[str]:
        paragraphs = _draft_paragraphs(answer)
        problems = (
            [] if (answer.get("summary") or "").strip() else ["요약 문단(summary)이 비어 있음"]
        )
        return (
            problems + overview_problems(paragraphs, source_text) + advice_problems(answer, allowed)
        )

    own_feedback = [
        {
            "code": f.get("code", ""),
            "reason": f.get("reason", ""),
            "requested_change": f.get("requested_change", ""),
        }
        for f in feedback
        if f.get("module") == "persona_explanation"
    ]
    extra: dict[str, Any] = {"previous_feedback": own_feedback} if own_feedback else {}

    answer = call_ask(
        ask,
        ctx.model,
        OverviewDraft,
        PERSONA_TASK,
        check,
        "medium",
        # A second answer that still fails is kept as is; the checks below hold it back.
        lambda a, _problems: a,
        product_type=classification.get("product_type"),
        profile=profile["attributes"],
        cards=[{k: c.get(k) for k in CARD_FIELDS} for c in cards],
        sources=[
            {"source_id": s["source_id"], "text": s["text"]}
            for s in sources
            if s["source_id"] in cited_sources
        ],
        disclosure_items=disclosure_items,
        explanation_items=explanation_items,
        **extra,
    )

    paragraphs = _draft_paragraphs(answer)
    advice_codes = [c for c in dict.fromkeys(answer.get("advice_codes") or []) if c in allowed]
    problems = check(answer)
    if problems:
        return {
            **_fallback("원문 대체", "개요가 코드 검사를 통과하지 못해 싣지 않음", profile),
            "overview": paragraphs,
            "advice_codes": advice_codes,
            "problems": problems,
        }
    return {
        "status": "완료",
        "reason": "",
        "profile": profile,
        "overview": paragraphs,
        "advice_codes": advice_codes,
        "problems": [],
        "html": overview_html(paragraphs),
        "controls": CONTROLS,
    }
