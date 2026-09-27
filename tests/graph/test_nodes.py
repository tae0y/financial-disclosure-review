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
    generate_plain_lang,
    judge_display_method,
    judge_explanation_duty,
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


def test_generate_plain_lang_needs_a_classification_and_an_html():
    update = generate_plain_lang(empty_state(), RUNTIME)
    assert update["plain_language"]["accepted_blocks"] == []
    assert update["plain_language"]["contract_errors"][0]["reason"].startswith("classification")

    state = state_with(classification={"product_type": "리볼빙", "page_type": "업무광고"})
    update = generate_plain_lang(state, RUNTIME)
    assert update["plain_language"]["contract_errors"][0]["reason"].startswith("product_page.html")


def test_judge_explanation_duty_needs_a_classification_an_html_and_a_plain_html():
    update = judge_explanation_duty(empty_state(), RUNTIME)
    assert update["explanation_duty_check"]["items"][0]["reason"].startswith("classification")
    assert update["explanation_duty_check"]["original"] == []

    state = state_with(
        classification={"product_type": "리볼빙", "page_type": "업무광고"},
        plain_language={"html": "<p>x</p>"},
    )
    update = judge_explanation_duty(state, RUNTIME)
    assert "product_page.html" in update["explanation_duty_check"]["items"][0]["reason"]

    state = state_with(
        classification={"product_type": "리볼빙", "page_type": "업무광고"},
        product_page={"html": "<p>x</p>"},
    )
    update = judge_explanation_duty(state, RUNTIME)
    assert "plain_language.html" in update["explanation_duty_check"]["items"][0]["reason"]


def test_judge_explanation_duty_keeps_the_original_side_of_a_previous_round():
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
        explanation_duty_check=previous,
    )
    update = judge_explanation_duty(state, RUNTIME)
    assert update["explanation_duty_check"]["original"] == previous["original"]
    assert update["explanation_duty_check"]["plain"] == []


def test_verify_answer_fails_every_module_that_has_no_answer_yet():
    update = verify_answer(empty_state(), RUNTIME)
    assert set(update) == {"verification"}
    assert update["verification"]["passed"] is False
    assert update["verification"]["failed_modules"] == [
        "display_check",
        "explanation_duty_check",
        "plain_language",
    ]


def test_verify_answer_counts_the_loop_forward():
    state = state_with(verification={"loop_count": 2})
    assert verify_answer(state, RUNTIME)["verification"]["loop_count"] == 3


def test_the_unimplemented_nodes_return_only_their_own_key():
    state = empty_state()
    assert retry_dispatch(state) == {"verification": {}}
    assert end_report(state) == {"report": {}}


def test_a_node_keeps_the_fields_its_module_already_had():
    state = state_with(
        display_check={"note": "이전 회차"},
        product_page={"html": "<p>x</p>", "snapshots": [{}]},
    )
    assert judge_display_method(state, RUNTIME)["display_check"]["note"] == "이전 회차"
