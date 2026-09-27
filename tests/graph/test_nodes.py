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
    from financial_disclosure_review.classification import classify_page

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


def test_the_stub_nodes_return_only_their_own_key():
    state = empty_state()
    assert generate_plain_lang(state, RUNTIME) == {"plain_language": {}}
    assert judge_explanation_duty(state, RUNTIME) == {"explanation_duty_check": {}}
    assert verify_answer(state, RUNTIME) == {"verification": {}}
    assert retry_dispatch(state) == {"verification": {}}
    assert end_report(state) == {"report": {}}


def test_a_node_keeps_the_fields_its_module_already_had():
    state = state_with(verification={"loop_count": 2})
    assert verify_answer(state, RUNTIME) == {"verification": {"loop_count": 2}}
