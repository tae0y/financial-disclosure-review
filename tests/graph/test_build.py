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
        "extract_evidence_cards",
        "judge_display_method",
        "generate_persona_explanation",
        "judge_explanation_original",
        "judge_explanation_duty",
        "verify_answer",
        "retry_dispatch",
        "end_report",
    } <= set(graph.nodes)


def initial(url: str = "https://example.test/product") -> State:
    state = empty_state()
    state["product_page"] = {"url": url}
    return state


def fake_cards(page, classification, ctx) -> dict:
    """No cards: the reference-case node then skips without touching any DB or corpus."""
    return {
        "status": "카드 없음",
        "reason": "테스트",
        "sources": [],
        "cards": [],
        "rejected": [],
        "coverage_gaps": [],
        "model_calls": 0,
    }


def fake_persona(sources, cards, classification, ctx, feedback=(), **kwargs) -> dict:
    """A PersonaExplanation with no cards: every source stays original, nothing to trace."""
    quote = visible_text(PAGE_HTML_FOR_PERSONA[0])[:24]
    return {
        "status": "원문 대체",
        "reason": "카드 없음",
        "profile": {"id": "p", "version": 1, "status": "적용"},
        "fact_ledger": [],
        "units": [],
        "html": f'<p data-source-id="dom-0">{quote}</p>',
        "controls": {},
    }


PAGE_HTML_FOR_PERSONA: list[str] = [""]


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


def fake_original(page, classification, ctx) -> dict:
    first = fake_duty(page, classification, {}, ctx, None, None)
    return {"items": first["items"], "original": first["original"]}


def fake_review(monkeypatch, revolving, calls: list[str], verdicts=None) -> None:
    """Every node faked; `calls` names each domain call in order, `verdicts` fakes verification."""
    from financial_disclosure_review.domain.verification import verify

    page = {**make_render_page(), **page_of(revolving)}
    PAGE_HTML_FOR_PERSONA[0] = page["html"]
    monkeypatch.setattr(nodes, "fetch_product_page", lambda url, ctx: page)
    monkeypatch.setattr(nodes, "classify_page", lambda page, model: dict(REVOLVING_CLASSIFICATION))
    monkeypatch.setattr(
        nodes,
        "judge_display",
        lambda page, classification, ctx: {"items": [], "judgments": {"status": "완료"}},
    )
    monkeypatch.setattr(nodes, "extract_cards", fake_cards)

    def persona(*args, **kwargs):
        calls.append("persona")
        return fake_persona(*args, **kwargs)

    def original(*args):
        calls.append("original")
        return fake_original(*args)

    def duty(page, classification, plain, ctx, previous_original, previous_items, **kwargs):
        calls.append("duty" if previous_items is None else "duty(original reused)")
        return fake_duty(page, classification, plain, ctx, previous_original, previous_items)

    rounds = iter(verdicts or [])

    def verdict(*args):
        real = verify(*args)
        return {**real, **next(rounds, {})}

    monkeypatch.setattr(nodes, "generate_persona", persona)
    monkeypatch.setattr(nodes, "judge_original", original)
    monkeypatch.setattr(nodes, "judge_explanation", duty)
    monkeypatch.setattr(nodes, "verify", verdict)


def test_independent_judgments_share_a_step_with_the_explanation(monkeypatch, revolving, tmp_path):
    """Reference cases run beside the display check, and the original side of the explanation
    duty beside the persona explanation, which it does not read."""
    from langgraph.checkpoint.sqlite import SqliteSaver

    calls: list[str] = []
    fake_review(monkeypatch, revolving, calls)
    config: RunnableConfig = {"configurable": {"thread_id": "parallel"}}
    with SqliteSaver.from_conn_string(str(tmp_path / "checkpoints.sqlite")) as saver:
        graph = build_review_graph(saver)
        final = graph.invoke(initial(), config, context=Context(model="fake"))
        steps = [set(state.next) for state in graph.get_state_history(config)]

    assert {"judge_display_method"} in steps
    assert {"generate_persona_explanation", "judge_explanation_original"} in steps
    assert calls == ["persona", "original", "duty(original reused)"] or calls == [
        "original",
        "persona",
        "duty(original reused)",
    ]
    assert final["report"]["status"] == "검토 완료"


def test_a_retry_regenerates_the_explanation_without_judging_the_original_again(
    monkeypatch, revolving
):
    calls: list[str] = []
    failed = {
        "passed": False,
        "failed_modules": ["persona_explanation"],
        "feedback": [
            {
                "module": "persona_explanation",
                "code": "",
                "source_id": "dom-0",
                "reason": "테스트",
                "requested_change": "다시 생성",
                "target": "",
            }
        ],
    }
    fake_review(monkeypatch, revolving, calls, verdicts=[failed])
    final = build_review_graph().invoke(initial(), context=Context(model="fake"))

    assert calls.count("original") == 1
    assert calls.count("persona") == 2
    assert calls[-1] == "duty(original reused)"
    assert final["verification"]["loop_count"] == 2


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
    monkeypatch.setattr(nodes, "extract_cards", fake_cards)
    PAGE_HTML_FOR_PERSONA[0] = page["html"]
    monkeypatch.setattr(nodes, "generate_persona", fake_persona)
    monkeypatch.setattr(nodes, "judge_explanation", fake_duty)
    monkeypatch.setattr(nodes, "judge_original", fake_original)
    final = build_review_graph().invoke(initial(), context=Context(model="fake"))

    assert final["classification"] == REVOLVING_CLASSIFICATION
    assert final["display_check"]["judgments"]["status"] == "완료"
    assert final["evidence_cards"]["status"] == "카드 없음"
    assert final["persona_explanation"]["status"] == "원문 대체"
    assert final["explanation_duty_check"]["original"]
    assert final["verification"]["passed"] is True, final["verification"]
    assert final["verification"]["loop_count"] == 1
    assert final["report"]["status"] == "검토 완료"
    assert final["report"]["findings"] == []
    assert "# 검토 결과 — " in final["report"]["markdown"]


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


def test_a_budget_stop_after_collection_still_ends_in_a_report(monkeypatch, revolving):
    """Audit 2026-09-29 R5: a spent budget is a result, not a crash without a report."""
    from langgraph.checkpoint.memory import InMemorySaver

    from financial_disclosure_review.core.usage import BudgetError
    from financial_disclosure_review.graph.build import invoke_to_report

    monkeypatch.setattr(nodes, "fetch_product_page", lambda url, ctx: page_of(revolving))
    monkeypatch.setattr(nodes, "classify_page", lambda page, model: dict(REVOLVING_CLASSIFICATION))

    def spent(*args, **kwargs):
        raise BudgetError("run budget $0.15 reached ($0.151) before cards")

    monkeypatch.setattr(nodes, "extract_cards", spent)
    config: RunnableConfig = {"configurable": {"thread_id": "budget"}}
    graph = build_review_graph(InMemorySaver())
    final = invoke_to_report(graph, initial(), config, Context(model="fake"))

    report = final["report"]
    assert report["status"] == "판정 불가"
    assert "extract_evidence_cards" in report["decision"]
    assert "$0.15" in report["actions"][0]
    assert report["summary"]["interrupted_at"] == "extract_evidence_cards"
    # The checkpoint ends with the report, so the thread reads as finished.
    snapshot = graph.get_state(config)
    assert snapshot.next == ()
    assert snapshot.values["report"]["status"] == "판정 불가"


def test_a_budget_stop_without_a_checkpointer_still_raises(monkeypatch, revolving):
    from financial_disclosure_review.core.usage import BudgetError
    from financial_disclosure_review.graph.build import invoke_to_report

    monkeypatch.setattr(nodes, "fetch_product_page", lambda url, ctx: page_of(revolving))

    def spent(*args, **kwargs):
        raise BudgetError("cap")

    monkeypatch.setattr(nodes, "classify_page", spent)
    with pytest.raises(BudgetError):
        invoke_to_report(build_review_graph(), initial(), {}, Context(model="fake"))
