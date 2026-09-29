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
    judge_display_method,
    judge_explanation_duty,
    preprocess_product_page,
    report_for,
    retrieve_reference_cases,
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
    builder.add_node("retrieve_reference_cases", retrieve_reference_cases)
    builder.add_node("judge_display_method", judge_display_method)
    builder.add_node("generate_persona_explanation", generate_persona_explanation)
    builder.add_node("judge_explanation_duty", judge_explanation_duty)
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
    builder.add_edge("extract_evidence_cards", "retrieve_reference_cases")
    builder.add_edge("retrieve_reference_cases", "judge_display_method")
    builder.add_edge("judge_display_method", "generate_persona_explanation")
    builder.add_edge("generate_persona_explanation", "judge_explanation_duty")
    builder.add_edge("judge_explanation_duty", "verify_answer")
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
            "judge_explanation_duty": "judge_explanation_duty",
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
