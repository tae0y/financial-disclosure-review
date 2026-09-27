"""The `search_cases` node writes only `case_search`, and the graph reaches it after classifying.

The node is wired between `classify_type` and `judge_display_method`, so these tests also pin
that placement: a reviewable product goes through `search_cases`, a non-review result does not.
"""

from types import SimpleNamespace
from typing import cast

from langgraph.runtime import Runtime

from financial_disclosure_review.core.context import Context
from financial_disclosure_review.core.state import empty_state
from financial_disclosure_review.graph import nodes
from financial_disclosure_review.graph.build import build_review_graph
from financial_disclosure_review.graph.nodes import search_cases
from financial_disclosure_review.graph.routes import route_after_classify
from financial_disclosure_review.knowledge.build_cases import build_case_db
from tests.helpers import EMBED_VOCAB, FIXTURE_DIR, FakeEmbed, state_with

RUNTIME = cast(Runtime[Context], SimpleNamespace(context=Context(model="fake")))


def case_db(tmp_path) -> str:
    path = tmp_path / "reference.sqlite"
    build_case_db(FIXTURE_DIR / "cases", path, embed=FakeEmbed(), dimensions=len(EMBED_VOCAB))
    return str(path)


def runtime_with(db_path: str) -> Runtime[Context]:
    return cast(Runtime[Context], SimpleNamespace(context=Context(model="fake", db_path=db_path)))


def test_an_empty_classification_is_unjudgeable_and_costs_nothing(monkeypatch):
    calls = []
    monkeypatch.setattr(nodes, "search_cases_for", lambda *a, **k: calls.append(a) or {})
    update = search_cases(empty_state(), RUNTIME)
    assert update["case_search"]["status"] == "판정 불가"
    assert update["case_search"]["hits"] == []
    assert "classify_type" in update["case_search"]["reason"]
    assert calls == []


def test_the_node_fills_case_search_from_the_case_db(monkeypatch, tmp_path):
    fake = FakeEmbed()
    monkeypatch.setattr("financial_disclosure_review.llm.client.embed_texts", fake)
    state = state_with(
        classification={"product_type": "리볼빙", "page_type": "업무광고"},
        product_page={"product": {"product_name": "테스트 리볼빙"}},
    )
    update = search_cases(state, runtime_with(case_db(tmp_path)))
    cases = update["case_search"]
    assert set(update) == {"case_search"}  # the node writes only its own key
    assert cases["status"] == "완료"
    assert cases["hits"] and len(cases["queries"]) == 4
    assert all("리볼빙" in hit["product_types"] for hit in cases["hits"])
    assert all(hit["official_primary_url"] for hit in cases["hits"])


def test_the_node_reports_a_missing_case_db_instead_of_raising(tmp_path, monkeypatch):
    monkeypatch.setattr("financial_disclosure_review.llm.client.embed_texts", FakeEmbed())
    state = state_with(classification={"product_type": "리볼빙", "page_type": "업무광고"})
    update = search_cases(state, runtime_with(str(tmp_path / "absent.sqlite")))
    assert update["case_search"]["status"] == "판정 불가"
    assert "build-cases" in update["case_search"]["reason"]


def test_empty_state_carries_the_new_key():
    assert empty_state()["case_search"] == {}


def test_the_classify_route_goes_to_search_cases():
    state = state_with(classification={"product_type": "리볼빙"})
    assert route_after_classify(state) == "search_cases"
    # 범위 밖은 검토를 건너뛰지만 보고서는 받습니다(`route_after_classify` 참조).
    assert (
        route_after_classify(state_with(classification={"product_type": "범위 밖"})) == "end_report"
    )


def test_the_graph_runs_classify_then_search_cases_then_the_display_check():
    graph = build_review_graph().get_graph()
    assert "search_cases" in graph.nodes
    edges = {(edge.source, edge.target) for edge in graph.edges}
    assert ("classify_type", "search_cases") in edges
    assert ("search_cases", "judge_display_method") in edges
    assert ("classify_type", "judge_display_method") not in edges


def test_an_out_of_scope_page_never_reaches_search_cases(monkeypatch, revolving):
    from tests.helpers import page_of

    seen = []
    monkeypatch.setattr(nodes, "fetch_product_page", lambda url, ctx: page_of(revolving))
    monkeypatch.setattr(
        nodes,
        "classify_page",
        lambda page, model: {"product_type": "범위 밖", "page_type": None, "reason": "1단계"},
    )
    monkeypatch.setattr(nodes, "search_cases_for", lambda *a, **k: seen.append(a) or {})
    state = empty_state()
    state["product_page"] = {"url": "https://example.test/product"}
    final = build_review_graph().invoke(state, context=Context(model="fake"))
    assert final["case_search"] == {}
    assert seen == []
