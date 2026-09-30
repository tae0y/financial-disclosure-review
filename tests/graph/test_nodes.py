"""The nodes return a State slice for their own key, and never raise on empty input."""

from types import SimpleNamespace
from typing import cast

from langgraph.runtime import Runtime

from financial_disclosure_review.core.context import Context
from financial_disclosure_review.core.state import empty_state
from financial_disclosure_review.graph import nodes
from financial_disclosure_review.graph.nodes import (
    classify_type,
    end_report,
    generate_persona_explanation,
    judge_ad_disclosure,
    judge_display_method,
    retry_dispatch,
    verify_answer,
)
from tests.helpers import make_fake_ask, page_of, state_with

RUNTIME = cast(Runtime[Context], SimpleNamespace(context=Context(model="fake")))


def test_classify_type_writes_the_classification(monkeypatch, revolving):
    from financial_disclosure_review.domain.classification import classify_page

    fake = make_fake_ask(revolving)
    monkeypatch.setattr(
        nodes, "classify_page", lambda page, model: classify_page(page, model, ask=fake)
    )
    update = classify_type(state_with(product_page=page_of(revolving)), RUNTIME)
    assert update["classification"]["product_type"] == "리볼빙"
    assert update["classification"]["page_type"] == "업무광고"
    assert fake.calls == ["ClassifyAnswer"]


def test_classify_type_reports_an_empty_page_as_unjudgeable():
    update = classify_type(empty_state(), RUNTIME)
    assert update["classification"]["product_type"] == "판정 불가"


def test_judge_display_method_needs_a_classification():
    state = state_with(product_page={"html": "<p>x</p>", "snapshots": [{}]})
    update = judge_display_method(state, RUNTIME)
    assert update["display_check"]["items"] == []
    assert update["display_check"]["judgments"]["status"] == "판정 불가"
    assert "classify_type" in update["display_check"]["judgments"]["reason"]


def test_judge_display_method_needs_html_and_snapshots():
    state = state_with(classification={"product_type": "리볼빙", "page_type": "업무광고"})
    update = judge_display_method(state, RUNTIME)
    assert update["display_check"]["judgments"]["reason"].startswith("product_page has no html")


def test_generate_persona_explanation_without_sources_calls_no_model(monkeypatch):
    def no_model(*args, **kwargs):
        raise AssertionError("no model call without evidence sources")

    monkeypatch.setattr("financial_disclosure_review.llm.client.ask", no_model)
    update = generate_persona_explanation(empty_state(), RUNTIME)
    assert set(update) == {"persona_explanation"}
    assert update["persona_explanation"]["html"] == ""
    assert update["persona_explanation"]["status"] == "판정 불가"


def test_judge_ad_disclosure_needs_a_classification_an_html_and_an_explanation():
    update = judge_ad_disclosure(empty_state(), RUNTIME)
    assert update["ad_disclosure_check"]["items"][0]["reason"].startswith("classification")
    assert update["ad_disclosure_check"]["original"] == []

    state = state_with(
        classification={"product_type": "리볼빙", "page_type": "업무광고"},
        persona_explanation={"html": "<p>x</p>"},
    )
    update = judge_ad_disclosure(state, RUNTIME)
    assert "product_page.html" in update["ad_disclosure_check"]["items"][0]["reason"]

    state = state_with(
        classification={"product_type": "리볼빙", "page_type": "업무광고"},
        product_page={"html": "<p>x</p>"},
    )
    update = judge_ad_disclosure(state, RUNTIME)
    assert "persona_explanation.html" in update["ad_disclosure_check"]["items"][0]["reason"]


def test_judge_ad_disclosure_keeps_the_original_side_of_a_previous_round():
    previous = {
        "items": [
            {
                "code": "설명01",
                "rubric": "r",
                "applied": True,
                "condition_status": "해당없음",
                "reason": "이전 회차",
            }
        ],
        "original": [{"code": "설명01", "verdict": "적합", "quote": "인용", "reason": "이전 회차"}],
    }
    state = state_with(
        classification={"product_type": "리볼빙", "page_type": "업무광고"},
        product_page={"html": "<p>x</p>"},
        ad_disclosure_check=previous,
    )
    update = judge_ad_disclosure(state, RUNTIME)
    assert update["ad_disclosure_check"]["original"] == previous["original"]
    assert update["ad_disclosure_check"]["overview"] == []


def test_verify_answer_fails_every_module_that_has_no_answer_yet():
    update = verify_answer(empty_state(), RUNTIME)
    assert set(update) == {"verification"}
    assert update["verification"]["passed"] is False
    assert update["verification"]["failed_modules"] == [
        "ad_disclosure_check",
        "display_check",
        "persona_explanation",
    ]


def test_verify_answer_counts_the_loop_forward():
    state = state_with(verification={"loop_count": 2})
    assert verify_answer(state, RUNTIME)["verification"]["loop_count"] == 3


def test_retry_dispatch_writes_only_the_verification_key():
    update = retry_dispatch(empty_state())
    assert set(update) == {"verification"}
    assert update["verification"]["retry_target"] == "", "실패 모듈이 없으면 되돌아갈 노드도 없음"
    assert update["verification"]["retry_history"][0]["loop"] == 0


def test_end_report_writes_only_the_report_key_and_never_passes_an_unjudged_page():
    update = end_report(empty_state(), RUNTIME)
    assert set(update) == {"report"}
    assert update["report"]["status"] == "판정 불가"
    assert update["report"]["markdown"].startswith("---")


def test_a_node_keeps_the_fields_its_module_already_had():
    state = state_with(
        display_check={"note": "이전 회차"},
        product_page={"html": "<p>x</p>", "snapshots": [{}]},
    )
    assert judge_display_method(state, RUNTIME)["display_check"]["note"] == "이전 회차"


def test_verify_answer_keeps_the_retry_history_of_earlier_rounds():
    """2026-09-28 감사 P0-2: 2회차 검증이 retry_* 필드를 지워 보고서가 '재시도 이력: 없음'을
    출력했습니다. 검증은 이번 회차 결과만 덮어쓰고 재시도 기록은 남겨야 합니다."""
    state = empty_state()
    state["verification"] = {
        "loop_count": 1,
        "retry_target": "judge_ad_disclosure",
        "retry_modules": ["ad_disclosure_check"],
        "retry_history": [{"loop": 1, "target": "judge_ad_disclosure"}],
    }
    verification = verify_answer(state, RUNTIME)["verification"]
    assert verification["loop_count"] == 2
    assert verification["retry_history"] == [{"loop": 1, "target": "judge_ad_disclosure"}]
    assert verification["retry_target"] == "judge_ad_disclosure"
