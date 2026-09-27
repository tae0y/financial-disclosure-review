"""The four downstream nodes wired together: judge_display_method (faked upstream result) ->
generate_plain_lang -> judge_explanation_duty -> verify_answer -> route_after_verify."""

from types import SimpleNamespace
from typing import cast

import pytest
from langgraph.runtime import Runtime

from financial_disclosure_review.core.context import Context
from financial_disclosure_review.core.state import State
from financial_disclosure_review.domain.explanation_duty_check.schema import (
    ExplanationJudgments,
    FidelityDiffs,
    PlainJudgments,
)
from financial_disclosure_review.domain.plain_language.contract import strip_ws
from financial_disclosure_review.domain.plain_language.schema import PlainDraftAnswer
from financial_disclosure_review.graph import nodes
from financial_disclosure_review.graph.nodes import (
    generate_plain_lang,
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


@pytest.fixture(scope="module")
def runtime(tmp_path_factory) -> Runtime[Context]:
    path = tmp_path_factory.mktemp("reference") / "reference.sqlite"
    build_rubric_db(FIXTURE_DIR / "rubric", path)
    return cast(Runtime[Context], SimpleNamespace(context=Context(model="fake", db_path=str(path))))


def routed(result: dict) -> str:
    return route_after_verify(cast(State, result))


def upstream_display_check(status: str = "완료") -> dict:
    """judge_display_method는 이 확인의 대상이 아니므로(다른 노드), 공통 계약을 따르는 가짜 상류
    결과를 직접 만든다. status='완료'/items=[]는 '적용 항목 없이 정상 종료'를 뜻한다."""
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


def plain_ask(invent_for: str | None = None):
    """generate_plain에 주입할 가짜 ask. quote를 그대로 text로 돌려주는 충실한 변환이 기본이고,
    invent_for를 포함한 블록 하나에만 원문에 없는 숫자를 끼워 넣어 contract_errors -> 원문 대체
    경로를 재현한다."""

    def fake(model, schema, task, effort="low", **data):
        assert schema is PlainDraftAnswer, schema
        items = []
        for block in data["blocks"]:
            text = block["quote"]
            if invent_for and invent_for in text:
                text = text.replace("1만원", "12만원")  # 원문에 없는 숫자를 새로 만들어 넣음
            items.append({"id": block["id"], "text": text, "terms": []})
        return {"items": items}

    return fake


def explanation_ask(condition_status: str = "불성립"):
    """judge_explanation에 주입할 가짜 ask. applies_condition이 없는 항목은 데이터 자체(text)에서
    뽑은 실제 인용으로 적합 처리한다. applies_condition이 있는 항목은 condition_status에 따라
    '불성립'(정상 경로: 조건이 성립하지 않아 제외, 판정 불가로 세지 않음)이거나 '불명확'(판정 불가
    경로: verify_answer가 반드시 실패로 잡아야 함)으로 남긴다. 원문/쉬운말 호출 양쪽에 같은 규칙을
    적용하므로 fidelity 후보는 생기지 않는다."""

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
        raise AssertionError(f"unexpected schema in the chain test: {schema}")

    return fake


def run_chain(
    monkeypatch,
    runtime,
    plain_fake,
    *,
    classification=None,
    display_status: str | None = "완료",
    explanation_fake=None,
) -> dict:
    from financial_disclosure_review.domain.explanation_duty_check import judge_explanation
    from financial_disclosure_review.domain.plain_language import generate_plain

    explanation_fake = explanation_fake or explanation_ask("불성립")
    monkeypatch.setattr(
        nodes,
        "generate_plain",
        lambda page, cls, feedback, ctx: generate_plain(page, cls, feedback, ctx, ask=plain_fake),
    )
    monkeypatch.setattr(
        nodes,
        "judge_explanation",
        lambda page, plain, cls, ctx, previous_original, previous_items: judge_explanation(
            page, plain, cls, ctx, previous_original, previous_items, ask=explanation_fake
        ),
    )
    state = state_with(
        product_page=PAGE,
        classification=CLASSIFICATION if classification is None else classification,
        display_check=upstream_display_check(display_status) if display_status else {},
    )
    state.update(generate_plain_lang(state, runtime))  # type: ignore[typeddict-item]
    state.update(judge_explanation_duty(state, runtime))  # type: ignore[typeddict-item]
    state.update(verify_answer(state, runtime))  # type: ignore[typeddict-item]
    return dict(state)


def test_the_happy_path_fills_every_key_and_passes(monkeypatch, runtime):
    result = run_chain(monkeypatch, runtime, plain_ask())

    assert set(result["plain_language"]) == {
        "items",
        "draft",
        "html",
        "term_refs",
        "accepted_blocks",
        "contract_errors",
    }
    assert result["plain_language"]["accepted_blocks"]
    assert result["plain_language"]["contract_errors"] == []
    assert set(result["explanation_duty_check"]) == {"items", "original", "plain", "fidelity"}
    assert result["explanation_duty_check"]["original"]
    excluded = [row for row in result["explanation_duty_check"]["items"] if not row["applied"]]
    assert excluded, "조건이 성립하지 않는 항목이 하나도 없으면 이 시나리오가 의미가 없음"
    assert result["verification"]["passed"] is True, result["verification"]
    assert result["verification"]["failed_modules"] == []
    assert routed(result) == "end_report"


def test_an_invented_number_is_replaced_by_the_original_and_still_fails_verification(
    monkeypatch, runtime
):
    result = run_chain(monkeypatch, runtime, plain_ask(invent_for="연회비"))

    assert result["plain_language"]["contract_errors"], (
        "invented number는 contract_errors에 남아야 함"
    )
    rejected = result["plain_language"]["contract_errors"][0]["source_id"]
    html = result["plain_language"]["html"]
    assert f'data-source-id="{rejected}"' in html
    assert "12만원" not in html, "지어낸 수치가 최종 html에 남으면 안 됨"
    assert "1만원" in html, "대체된 블록은 원문 그대로 보여야 함"
    assert result["verification"]["passed"] is False
    assert "plain_language" in result["verification"]["failed_modules"]
    assert routed(result) == "retry_dispatch", "조치 가능한 피드백이 있으면 재생성으로 돌아감"


def test_an_unclear_condition_is_never_counted_as_a_pass(monkeypatch, runtime):
    result = run_chain(
        monkeypatch, runtime, plain_ask(), explanation_fake=explanation_ask("불명확")
    )

    assert any(
        row["verdict"] == "판정 불가" for row in result["explanation_duty_check"]["original"]
    )
    assert result["verification"]["passed"] is False
    assert "explanation_duty_check" in result["verification"]["failed_modules"]
    assert routed(result) == "end_report"


def test_a_missing_upstream_result_fails_all_three_modules(monkeypatch, runtime):
    result = run_chain(monkeypatch, runtime, plain_ask(), classification={}, display_status=None)

    assert result["plain_language"]["contract_errors"]
    assert result["explanation_duty_check"]["original"] == []
    assert result["verification"]["passed"] is False
    assert result["verification"]["failed_modules"] == [
        "display_check",
        "explanation_duty_check",
        "plain_language",
    ]
    assert routed(result) == "retry_dispatch"
