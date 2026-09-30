"""Entry point of persona_explanation: one paragraph of reader-tailored advice beside the page —
which explanation-duty items the ad does not cover this reader should check before signing."""

import re
from collections.abc import Mapping, Sequence
from html import escape
from pathlib import Path
from typing import Any

from ...core.context import Context
from ...llm.client import ask, call_ask
from ..ad_disclosure_check.rubric import deferred_explanation_items
from ..plain_language.contract import (
    FORBIDDEN_ABSOLUTE_PHRASES,
    counter_ones,
    has_phrase,
    number_set,
)
from .profiles import resolve_profile
from .prompts import PERSONA_TASK
from .schema import AdviceDraft

MIN_ADVICE_CODES = 2
MAX_ADVICE_CODES = 5
MAX_CHARS = 700
ENUM_MARKER = re.compile(r"(?<!\S)\(?\d{1,2}[)）.](?=\s)")
VERDICT_RE = re.compile(r"적합|부적합|위반|합법|불법|문제없")
# A rubric code written into the reader's text ("설명16") means nothing to the reader.
CODE_RE = re.compile(r"설명\s?\d{2}|[A-GF]\d{2}\b")
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
# Controls a published advice needs around it. They are listed so the report can show them;
# this node neither implements nor judges them.
CONTROLS = {
    "ui": ["AI 생성 고지", "원문 보기 전환", "오류 신고"],
    "governance": ["사람 승인", "변경 관리", "프로필 검토"],
    "note": "화면·운영 통제 목록으로 문서화만 하며, 이 노드는 이 항목들을 판정하지 않음",
}


def advice_html(advice: str) -> str:
    """The advice alone; the page it refers to is shown beside it, not inside it."""
    return f'<section data-role="advice"><p>{escape(advice)}</p></section>' if advice else ""


def advice_problems(
    answer: Mapping[str, Any], allowed: Sequence[str], source_text: str
) -> list[str]:
    """Code checks of a drafted advice against the checklist and the page; empty when it may be
    shown."""
    advice = (answer.get("advice") or "").strip()
    if not advice:
        return ["권고 문단(advice)이 비어 있음"]
    problems = []
    codes = list(dict.fromkeys(answer.get("advice_codes") or []))
    unknown = [c for c in codes if c not in allowed]
    if unknown:
        problems.append(f"설명의무 확인 목록에 없는 advice_codes: {', '.join(unknown)}")
    known = [c for c in codes if c in allowed]
    if not MIN_ADVICE_CODES <= len(known) <= MAX_ADVICE_CODES:
        problems.append(
            f"권고 항목 {len(known)}개(advice_codes는 {MIN_ADVICE_CODES}~{MAX_ADVICE_CODES}개)"
        )
    if len(advice) > MAX_CHARS:
        problems.append(f"권고 문단 {len(advice)}자(최대 {MAX_CHARS}자)")
    if CODE_RE.search(advice):
        problems.append("본문에 항목 코드가 들어 있음(독자에게는 항목 이름으로 쓸 것)")
    # "1) …", "(2) …", "3. …" number a list; they state no fact, so they are not checked.
    stated = ENUM_MARKER.sub(" ", CODE_RE.sub(" ", advice))
    extra = sorted(number_set(stated) - number_set(source_text) - counter_ones(stated))
    if extra:
        problems.append(f"원문에 없는 수치: {', '.join(extra)}")
    added = [
        p
        for p in FORBIDDEN_ABSOLUTE_PHRASES
        if has_phrase(stated, p) and not has_phrase(source_text, p)
    ]
    if added:
        problems.append(f"원문에 없는 단정·최상급 표현: {', '.join(added)}")
    verdicts = sorted(set(VERDICT_RE.findall(stated)))
    if verdicts:
        problems.append(f"판정 표현 사용: {', '.join(verdicts)}")
    return problems


def _fallback(status: str, reason: str, profile: dict) -> dict:
    return {
        "status": status,
        "reason": reason,
        "profile": profile,
        "advice": "",
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
    """독자 맞춤 확인 권고 생성. PersonaExplanation의 모든 필드를 돌려준다.

    {status, reason, profile, advice, advice_codes, problems, html, controls}. 이 광고 페이지에
    없지만 계약 전에 설명받아야 하는 설명의무 항목 중 이 독자에게 중요한 2~5개를 골라, 상품설명서나
    상담에서 확인해 보라고 권하는 한 문단이다. 모델 호출은 한 번이며, 코드 검사에 걸린 답은 한 번
    다시 묻는다. 두 번째 답도 걸리면 싣지 않고 문제를 `problems`에 남겨 검증이 재생성을 요청하게
    한다. `profile`이 주어지면(choose_profile의 결과) 그대로 쓴다: 재시도도 같은 독자로 쓴다.
    """
    if profile is None:
        wanted_profile = profile_id if profile_id is not None else ctx.persona_profile
        profile = resolve_profile(wanted_profile, profiles_path)
    if not sources:
        return _fallback("판정 불가", "페이지 원문(sources)이 없음", profile)
    if profile["status"] != "적용":
        return _fallback("원문 대체", f"페르소나 프로필 무효: {profile['reason']}", profile)
    explanation_items = [
        {"code": i["code"], "question": i["question"]}
        for i in deferred_explanation_items(ctx.db_path, classification.get("product_type"))
    ]
    if not explanation_items:
        return _fallback("원문 대체", "이 상품유형에 확인할 설명의무 항목이 없음", profile)

    allowed = [i["code"] for i in explanation_items]
    source_text = " ".join(s.get("text", "") for s in sources)
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
        AdviceDraft,
        PERSONA_TASK,
        lambda a: advice_problems(a, allowed, source_text),
        "medium",
        # A second answer that still fails is kept as is; the checks below hold it back.
        lambda a, _problems: a,
        product_type=classification.get("product_type"),
        profile=profile["attributes"],
        cards=[{k: c.get(k) for k in CARD_FIELDS} for c in cards],
        # Every page line, not only the ones cards cite: the advice must not recommend checking
        # what the page already explains.
        sources=[{"source_id": s["source_id"], "text": s["text"]} for s in sources],
        explanation_items=explanation_items,
        **extra,
    )

    advice = (answer.get("advice") or "").strip()
    advice_codes = [c for c in dict.fromkeys(answer.get("advice_codes") or []) if c in allowed]
    problems = advice_problems(answer, allowed, source_text)
    if problems:
        return {
            **_fallback("원문 대체", "확인 권고가 코드 검사를 통과하지 못해 싣지 않음", profile),
            "advice": advice,
            "advice_codes": advice_codes,
            "problems": problems,
        }
    return {
        "status": "완료",
        "reason": "",
        "profile": profile,
        "advice": advice,
        "advice_codes": advice_codes,
        "problems": [],
        "html": advice_html(advice),
        "controls": CONTROLS,
    }
