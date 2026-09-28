"""The compiled graph runs to END with the fetch and the model calls faked."""

import pytest
from langchain_core.runnables import RunnableConfig

from financial_disclosure_review.core.context import Context
from financial_disclosure_review.core.state import State, empty_state
from financial_disclosure_review.core.text import visible_text
from financial_disclosure_review.domain.classification import classify_page
from financial_disclosure_review.graph import nodes
from financial_disclosure_review.graph.build import build_review_graph
from tests.helpers import make_fake_ask, make_render_page, page_of

REVOLVING_CLASSIFICATION = {
    "product_type": "리볼빙",
    "page_type": "업무광고",
    "reason": "테스트",
}


def test_the_graph_compiles_with_every_node_and_edge():
    graph = build_review_graph().get_graph()
    assert {
        "preprocess_product_page",
        "classify_type",
        "judge_display_method",
        "generate_plain_lang",
        "judge_explanation_duty",
        "verify_answer",
        "retry_dispatch",
        "end_report",
    } <= set(graph.nodes)


def initial(url: str = "https://example.test/product") -> State:
    state = empty_state()
    state["product_page"] = {"url": url}
    return state


def fake_plain(page, classification, feedback, ctx) -> dict:
    """A PlainLanguage value whose one block really is in the page, so verify can pass on it."""
    quote = visible_text(page["html"])[:24]
    return {
        "items": [],
        "draft": [{"id": "b0", "text": quote, "terms": []}],
        "html": f'<p data-source-id="b0">{quote}</p>',
        "term_refs": [],
        "accepted_blocks": [{"source_id": "b0", "source_quote": quote, "text": quote}],
        "contract_errors": [],
    }


def fake_duty(
    page, classification, plain, ctx, previous_original, previous_items, *, feedback=()
) -> dict:
    row = {
        "code": "설명01",
        "verdict": "적합",
        "quote": visible_text(page["html"])[:24],
        "reason": "테스트",
    }
    return {
        "items": [
            {
                **row,
                "rubric": "plain_service_rubric",
                "applied": True,
                "condition_status": "해당없음",
            }
        ],
        "original": [dict(row)],
        "plain": [dict(row)],
        "fidelity": [],
    }


def test_a_reviewable_page_runs_through_to_the_report(monkeypatch, revolving):
    page = {**make_render_page(), **page_of(revolving)}
    page["snapshots"] = make_render_page()["snapshots"]
    monkeypatch.setattr(nodes, "fetch_product_page", lambda url, ctx: page)
    monkeypatch.setattr(
        nodes,
        "classify_page",
        lambda page, model: dict(REVOLVING_CLASSIFICATION),
    )
    monkeypatch.setattr(
        nodes,
        "judge_display",
        lambda page, classification, ctx: {"items": [], "judgments": {"status": "완료"}},
    )
    monkeypatch.setattr(nodes, "generate_plain", fake_plain)
    monkeypatch.setattr(nodes, "judge_explanation", fake_duty)
    final = build_review_graph().invoke(initial(), context=Context(model="fake"))

    assert final["classification"] == REVOLVING_CLASSIFICATION
    assert final["display_check"]["judgments"]["status"] == "완료"
    assert final["plain_language"]["accepted_blocks"]
    assert final["explanation_duty_check"]["original"]
    assert final["verification"]["passed"] is True, final["verification"]
    assert final["verification"]["loop_count"] == 1
    assert final["report"]["status"] == "검토 완료"
    assert final["report"]["findings"] == []
    assert "# 금융상품 판매화면 검토 결과" in final["report"]["markdown"]


def test_an_out_of_scope_page_stops_after_the_classification(monkeypatch, revolving):
    monkeypatch.setattr(nodes, "fetch_product_page", lambda url, ctx: page_of(revolving))
    monkeypatch.setattr(
        nodes,
        "classify_page",
        lambda page, model: {"product_type": "범위 밖", "page_type": None, "reason": "1단계"},
    )
    final = build_review_graph().invoke(initial(), context=Context(model="fake"))

    assert final["classification"]["product_type"] == "범위 밖"
    assert final["display_check"] == {}


def test_a_page_the_fake_model_cannot_judge_also_stops(monkeypatch, revolving):
    fake = make_fake_ask(revolving, quote="이 문장은 페이지 어디에도 없습니다")
    monkeypatch.setattr(nodes, "fetch_product_page", lambda url, ctx: page_of(revolving))
    monkeypatch.setattr(
        nodes, "classify_page", lambda page, model: classify_page(page, model, ask=fake)
    )
    final = build_review_graph().invoke(initial(), context=Context(model="fake"))
    assert final["classification"]["product_type"] == "판정 불가"
    assert final["display_check"] == {}


def test_the_checkpointer_records_every_step(monkeypatch, revolving, tmp_path):
    from langgraph.checkpoint.sqlite import SqliteSaver

    monkeypatch.setattr(nodes, "fetch_product_page", lambda url, ctx: page_of(revolving))
    monkeypatch.setattr(
        nodes,
        "classify_page",
        lambda page, model: {"product_type": "범위 밖", "page_type": None, "reason": "1단계"},
    )
    config: RunnableConfig = {"configurable": {"thread_id": "test"}}
    with SqliteSaver.from_conn_string(str(tmp_path / "checkpoints.sqlite")) as saver:
        graph = build_review_graph(saver)
        graph.invoke(initial(), config, context=Context(model="fake"))
        history = list(graph.get_state_history(config))
    assert any("classify_type" in state.next for state in history)


@pytest.mark.use_network
@pytest.mark.use_llm
def test_the_sample_urls_run_end_to_end():
    from pathlib import Path

    urls = [u for u in Path("data/sample_urls.txt").read_text().split() if u]
    assert urls
    graph = build_review_graph()
    for url in urls:
        final = graph.invoke(initial(url), context=Context())
        page = final["product_page"]
        assert page.get("html")
        assert set(final["classification"]) == {"product_type", "page_type", "reason"}
        assert set(final["display_check"]) <= {"items", "judgments"}


def test_a_collection_failure_reaches_a_report_without_any_model_call(monkeypatch):
    failed = {
        "url": "https://example.test/product",
        "product": {},
        "actions": [],
        "snapshots": [],
        "html": "",
        "status": "수집 실패",
        "stop_reason": "fetch_error",
        "error": "navigation failed",
        "coverage": {"before": {}, "after": {}, "gaps": []},
        "agent_trace": [],
    }
    monkeypatch.setattr(nodes, "fetch_product_page", lambda url, ctx: failed)

    def no_model(*args, **kwargs):
        raise AssertionError("no model call after a collection failure")

    monkeypatch.setattr(nodes, "classify_page", no_model)
    final = build_review_graph().invoke(initial(), context=Context(model="fake"))
    assert final["classification"] == {}
    assert final["report"]["status"] == "수집 실패"
    assert "navigation failed" in final["report"]["markdown"]
