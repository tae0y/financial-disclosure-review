"""The downstream nodes wired together: evidence cards (given) -> generate_persona_explanation ->
judge_explanation_duty -> verify_answer -> route_after_verify, with every model call faked."""

from types import SimpleNamespace
from typing import cast

import pytest
from langgraph.runtime import Runtime

from financial_disclosure_review.core.context import Context
from financial_disclosure_review.core.state import State
from financial_disclosure_review.domain.evidence_cards import page_sources
from financial_disclosure_review.domain.explanation_duty_check.ledger import LedgerSemantics
from financial_disclosure_review.domain.explanation_duty_check.schema import (
    ExplanationJudgments,
    FidelityDiffs,
    PlainJudgments,
)
from financial_disclosure_review.domain.persona_explanation.schema import PersonaUnitDrafts
from financial_disclosure_review.domain.plain_language.contract import strip_ws
from financial_disclosure_review.graph import nodes
from financial_disclosure_review.graph.nodes import (
    generate_persona_explanation,
    judge_explanation_duty,
    verify_answer,
)
from financial_disclosure_review.graph.routes import route_after_verify
from financial_disclosure_review.knowledge.build import build_rubric_db
from tests.helpers import FIXTURE_DIR, state_with

FIXTURE_HTML = """
<html><body>
<h1>초록카드 신용카드</h1>
<p>연회비는 국내전용 1만원이며 매년 부과됩니다.</p>
<p>연체 시 최고 연 20%의 연체이자율이 적용될 수 있습니다.</p>
<p>중도 해지 시 위약금은 없습니다.</p>
</body></html>
"""
CLASSIFICATION = {"product_type": "신용카드", "page_type": "상품광고", "reason": "통합 확인용"}
PAGE = {
    "url": "https://example.test/integration-card",
    "product": {"product_name": "초록카드"},
    "html": FIXTURE_HTML,
}
SOURCES = page_sources(PAGE)
FEE_LINE = "연회비는 국내전용 1만원이며 매년 부과됩니다."
LATE_LINE = "연체 시 최고 연 20%의 연체이자율이 적용될 수 있습니다."


def source_id_of(text: str) -> str:
    return next(s["source_id"] for s in SOURCES if s["text"] == text)


CARDS = [
    {
        "id": "c1",
        "kind": "fee_claim",
        "subject": "연회비",
        "claim": "국내전용 연회비 1만원",
        "qualifiers": ["매년 부과"],
        "exceptions": [],
        "numbers": ["1만원"],
        "quote": FEE_LINE,
        "source_id": source_id_of(FEE_LINE),
        "visibility": "unresolved",
    },
    {
        "id": "c2",
        "kind": "warning",
        "subject": "연체이자율",
        "claim": "연체 시 최고 연 20%",
        "qualifiers": [],
        "exceptions": [],
        "numbers": ["20%"],
        "quote": LATE_LINE,
        "source_id": source_id_of(LATE_LINE),
        "visibility": "unresolved",
    },
]
EVIDENCE = {"status": "완료", "sources": SOURCES, "cards": CARDS}


@pytest.fixture(scope="module")
def runtime(tmp_path_factory) -> Runtime[Context]:
    path = tmp_path_factory.mktemp("reference") / "reference.sqlite"
    build_rubric_db(FIXTURE_DIR / "rubric", path)
    return cast(Runtime[Context], SimpleNamespace(context=Context(model="fake", db_path=str(path))))


def routed(result: dict) -> str:
    return route_after_verify(cast(State, result))


def upstream_display_check(status: str = "완료") -> dict:
    """judge_display_method는 이 확인의 대상이 아니므로 공통 계약을 따르는 가짜 상류 결과를 쓴다."""
    return {
        "items": [],
        "judgments": {
            "status": status,
            "skipped": [],
            "blocks": [],
            "measures": {},
            "reason": "" if status == "완료" else "통합 확인용 판정 불가",
        },
    }


def persona_ask(invent: bool = False, seen: list | None = None):
    """generate_persona_explanation에 주입할 가짜 ask. 카드마다 원문 줄을 exact_fact로 옮기고
    수치를 그대로 둔 설명을 돌려준다. invent=True면 연회비 설명에 원문에 없는 금액을 넣는다."""

    def fake(model, schema, task, effort="low", **data):
        assert schema is PersonaUnitDrafts, schema
        if seen is not None:
            seen.append(data.get("previous_feedback") or [])
        fee = "카드를 쓰는 값으로 매년 1만원이 부과됩니다."
        return {
            "items": [
                {
                    "card_ids": ["c1"],
                    "source_ids": [CARDS[0]["source_id"]],
                    "exact_fact": FEE_LINE,
                    "explanation": fee.replace("1만원", "12만원") if invent else fee,
                    "analogy": "",
                    "persona_question_answered": "이 카드를 쓰면 돈이 언제, 얼마나 나가나요?",
                },
                {
                    "card_ids": ["c2"],
                    "source_ids": [CARDS[1]["source_id"]],
                    "exact_fact": LATE_LINE,
                    "explanation": "돈을 늦게 내면 최고 연 20%의 연체이자가 붙을 수 있습니다.",
                    "analogy": "",
                    "persona_question_answered": "모르고 지나치면 손해 보는 조건이 있나요?",
                },
            ]
        }

    return fake


def explanation_ask(condition_status: str = "불성립"):
    """judge_explanation에 주입할 가짜 ask. applies_condition이 없는 항목은 입력 text에서 뽑은
    실제 인용으로 적합 처리하고, 있는 항목은 condition_status('불성립' 정상 제외 또는 '불명확'
    판정 불가)로 남긴다. 원문/설명문 양쪽에 같은 규칙을 적용하므로 fidelity 후보는 생기지 않는다."""

    def fake(model, schema, task, effort="low", **data):
        if schema is ExplanationJudgments:
            quote = strip_ws(data["text"])[:12]
            return {
                "items": [
                    {
                        "code": item["code"],
                        "condition_status": condition_status,
                        "verdict": "판정 불가",
                        "quote": "",
                        "reason": "통합 확인용",
                    }
                    if item.get("applies_condition")
                    else {
                        "code": item["code"],
                        "condition_status": "해당없음",
                        "verdict": "적합",
                        "quote": quote,
                        "reason": "통합 확인용: 기준 충족",
                    }
                    for item in data["items"]
                ]
            }
        if schema is PlainJudgments:
            quote = strip_ws(data["text"])[:12]
            return {
                "items": [
                    {
                        "code": item["code"],
                        "verdict": "적합",
                        "quote": quote,
                        "reason": "통합 확인용: 기준 충족",
                    }
                    for item in data["items"]
                ]
            }
        if schema is FidelityDiffs:
            return {
                "items": [
                    {"code": item["code"], "kind": "변화없음", "reason": "통합 확인용: 차이 없음"}
                    for item in data["items"]
                ]
            }
        if schema is LedgerSemantics:
            raise AssertionError("every ledger value is in the explanation; no model call")
        raise AssertionError(f"unexpected schema in the chain test: {schema}")

    return fake


def run_chain(
    monkeypatch,
    runtime,
    persona_fake,
    *,
    classification=None,
    evidence=None,
    display_status: str | None = "완료",
    explanation_fake=None,
) -> dict:
    from financial_disclosure_review.domain.explanation_duty_check import judge_explanation
    from financial_disclosure_review.domain.persona_explanation import (
        generate_persona_explanation as generate,
    )

    explanation_fake = explanation_fake or explanation_ask("불성립")
    monkeypatch.setattr(
        nodes,
        "generate_persona",
        lambda sources, cards, cls, ctx, feedback, **kw: generate(
            sources, cards, cls, ctx, feedback, ask=persona_fake, **kw
        ),
    )
    monkeypatch.setattr(
        nodes,
        "judge_explanation",
        lambda page, plain, cls, ctx, previous_original, previous_items, *, feedback=(): (
            judge_explanation(
                page,
                plain,
                cls,
                ctx,
                previous_original,
                previous_items,
                ask=explanation_fake,
                feedback=feedback,
            )
        ),
    )
    monkeypatch.setattr(nodes, "ask", explanation_fake)
    state = state_with(
        product_page=PAGE,
        classification=CLASSIFICATION if classification is None else classification,
        evidence_cards=EVIDENCE if evidence is None else evidence,
        display_check=upstream_display_check(display_status) if display_status else {},
    )
    state.update(generate_persona_explanation(state, runtime))  # type: ignore[typeddict-item]
    state.update(judge_explanation_duty(state, runtime))  # type: ignore[typeddict-item]
    state.update(verify_answer(state, runtime))  # type: ignore[typeddict-item]
    return dict(state)


def test_the_happy_path_fills_every_key_and_passes(monkeypatch, runtime):
    result = run_chain(monkeypatch, runtime, persona_ask())

    persona = result["persona_explanation"]
    assert persona["status"] == "완료", persona["reason"]
    assert [u["status"] for u in persona["units"]] == ["accepted", "accepted"]
    assert persona["profile"]["status"] == "적용"
    duty = result["explanation_duty_check"]
    assert set(duty) == {"items", "original", "plain", "ledger", "fidelity"}
    assert duty["ledger"] and all(row["decided_by"] == "code" for row in duty["ledger"])
    assert all(row["verdict"] == "보존" for row in duty["ledger"])
    excluded = [row for row in duty["items"] if not row["applied"]]
    assert excluded, "조건이 성립하지 않는 항목이 하나도 없으면 이 시나리오가 의미가 없음"
    assert result["verification"]["passed"] is True, result["verification"]
    assert routed(result) == "end_report"


def test_an_invented_number_reverts_the_unit_and_the_original_line_stays(monkeypatch, runtime):
    """지어낸 금액이 있는 단위는 원문 줄로 되돌립니다. 되돌린 단위는 원문이 그대로 보이므로
    검증 실패가 아니며, 보고서의 확인 항목으로만 남습니다."""
    result = run_chain(monkeypatch, runtime, persona_ask(invent=True))

    persona = result["persona_explanation"]
    fee_unit = next(u for u in persona["units"] if u["card_ids"] == ["c1"])
    assert fee_unit["status"] == "reverted"
    assert "12만원" not in persona["html"], "지어낸 수치가 최종 html에 남으면 안 됨"
    assert "1만원" in persona["html"], "되돌린 줄은 원문 그대로 보여야 함"
    assert result["verification"]["passed"] is True, result["verification"]
    assert routed(result) == "end_report"


def test_an_unclear_condition_is_never_counted_as_a_pass(monkeypatch, runtime):
    result = run_chain(
        monkeypatch, runtime, persona_ask(), explanation_fake=explanation_ask("불명확")
    )

    assert any(
        row["verdict"] == "판정 불가" for row in result["explanation_duty_check"]["original"]
    )
    assert result["verification"]["passed"] is False
    assert "explanation_duty_check" in result["verification"]["failed_modules"]
    assert routed(result) == "end_report"


def test_a_missing_upstream_result_fails_every_module_and_goes_to_a_person(monkeypatch, runtime):
    result = run_chain(
        monkeypatch, runtime, persona_ask(), classification={}, evidence={}, display_status=None
    )

    assert result["persona_explanation"]["html"] == ""
    assert result["explanation_duty_check"]["original"] == []
    assert result["verification"]["passed"] is False
    assert result["verification"]["failed_modules"] == [
        "display_check",
        "explanation_duty_check",
        "persona_explanation",
    ]
    assert routed(result) == "end_report", "고칠 수 있는 피드백이 없으면 재시도하지 않음"


def test_the_retry_round_hands_the_generator_what_verification_asked_for(monkeypatch, runtime):
    """A retry that repeats the same call without the feedback would pay twice for one answer."""
    first = run_chain(monkeypatch, runtime, persona_ask())
    request = {
        "module": "persona_explanation",
        "code": "f1",
        "source_id": CARDS[0]["source_id"],
        "reason": "사실 원장 f1 누락",
        "requested_change": "원문의 수치·조건·예외·불이익을 보존하도록 이 단위를 다시 생성하세요",
        "target": "",
    }
    first["verification"] = {**first["verification"], "feedback": [request]}

    seen: list[list[dict]] = []
    run_chain(monkeypatch, runtime, persona_ask(seen=seen))  # installs the capturing fake
    generate_persona_explanation(cast(State, first), runtime)

    assert seen[-1], "재시도 회차의 설명 생성이 검증 피드백을 받지 못함"
    assert {entry["source_id"] for entry in seen[-1]} == {CARDS[0]["source_id"]}


def test_a_persona_failure_is_routed_back_to_the_generator(monkeypatch, runtime):
    """이름을 바꾼 뒤 재시도 라우팅이 조용히 end_report로 빠지지 않는지 확인합니다."""
    from financial_disclosure_review.graph.retry import plan_retry
    from financial_disclosure_review.graph.routes import route_after_retry

    verification = {
        "passed": False,
        "loop_count": 1,
        "failed_modules": ["persona_explanation"],
        "feedback": [{"module": "persona_explanation", "requested_change": "다시 생성"}],
    }
    state = state_with(verification=verification)
    assert routed(dict(state)) == "retry_dispatch"
    state["verification"] = {**verification, **plan_retry(verification)}  # type: ignore[typeddict-item]
    assert route_after_retry(state) == "generate_persona_explanation"
