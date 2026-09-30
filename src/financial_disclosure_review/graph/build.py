"""Assembling the review graph."""

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from ..core.context import Context
from ..core.state import State
from ..core.usage import BudgetError
from .nodes import (
    classify_type,
    end_report,
    extract_evidence_cards,
    generate_persona_explanation,
    judge_ad_disclosure,
    judge_disclosure_original,
    judge_display_method,
    preprocess_product_page,
    report_for,
    retry_dispatch,
    verify_answer,
)
from .retry import MAX_LOOPS
from .routes import (
    route_after_classify,
    route_after_preprocess,
    route_after_retry,
    route_after_verify,
)


def build_review_graph(checkpointer=None):
    builder = StateGraph(State, context_schema=Context)
    builder.add_node("preprocess_product_page", preprocess_product_page)
    builder.add_node("classify_type", classify_type)
    builder.add_node("extract_evidence_cards", extract_evidence_cards)
    builder.add_node("judge_display_method", judge_display_method)
    builder.add_node("generate_persona_explanation", generate_persona_explanation)
    builder.add_node("judge_disclosure_original", judge_disclosure_original)
    builder.add_node("judge_ad_disclosure", judge_ad_disclosure)
    builder.add_node("verify_answer", verify_answer)
    builder.add_node("retry_dispatch", retry_dispatch)
    builder.add_node("end_report", end_report)

    builder.add_edge(START, "preprocess_product_page")
    builder.add_conditional_edges(
        "preprocess_product_page",
        route_after_preprocess,
        {"classify_type": "classify_type", "end_report": "end_report"},
    )
    builder.add_conditional_edges(
        "classify_type",
        route_after_classify,
        {"extract_evidence_cards": "extract_evidence_cards", "end_report": "end_report"},
    )
    # LangGraph runs a step's nodes together and waits for all of them, so the original side of
    # the ad-disclosure check (page only) runs beside the persona overview. A node that two
    # finished nodes point to runs once. A retry re-enters at the persona overview alone, which
    # is why the original side has plain edges instead of a join.
    builder.add_edge("extract_evidence_cards", "judge_display_method")
    builder.add_edge("judge_display_method", "generate_persona_explanation")
    builder.add_edge("judge_display_method", "judge_disclosure_original")
    builder.add_edge("generate_persona_explanation", "judge_ad_disclosure")
    builder.add_edge("judge_disclosure_original", "judge_ad_disclosure")
    builder.add_edge("judge_ad_disclosure", "verify_answer")
    builder.add_conditional_edges(
        "verify_answer",
        route_after_verify,
        {"retry_dispatch": "retry_dispatch", "end_report": "end_report"},
    )
    builder.add_conditional_edges(
        "retry_dispatch",
        route_after_retry,
        {
            "generate_persona_explanation": "generate_persona_explanation",
            "judge_ad_disclosure": "judge_ad_disclosure",
            "end_report": "end_report",
        },
    )
    builder.add_edge("end_report", END)
    return builder.compile(checkpointer=checkpointer)


def invoke_to_report(graph, graph_input, config: RunnableConfig, context: Context) -> dict:
    """Run the graph; a budget spent after collection still ends in a 판정 불가 report.

    The failing node's writes are lost, so the report is built from the last checkpoint and
    written back as `end_report`, leaving the thread finished. Without a checkpointer there is
    no state to report from, and the BudgetError propagates.
    """
    try:
        return dict(graph.invoke(graph_input, config, context=context))
    except BudgetError as error:
        if graph.checkpointer is None:
            raise
        # A rerun's config pins an old checkpoint; the state to report is the thread's latest.
        thread: RunnableConfig = {
            "configurable": {"thread_id": (config.get("configurable") or {}).get("thread_id")}
        }
        snapshot = graph.get_state(thread)
        state = dict(snapshot.values)
        at = snapshot.next[0] if snapshot.next else "end_report"
        stop = {
            "reason": "비용 한도 도달",
            "detail": str(error),
            "interrupted_at": at,
            "max_loops": MAX_LOOPS,
        }
        report = report_for(state, context, stop)
        graph.update_state(thread, {"report": report}, as_node="end_report")
        return {**state, "report": report}
