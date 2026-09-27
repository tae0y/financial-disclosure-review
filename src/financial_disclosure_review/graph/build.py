"""Assembling the review graph."""

from langgraph.graph import END, START, StateGraph

from ..core.context import Context
from ..core.state import State
from .nodes import (
    classify_type,
    end_report,
    generate_plain_lang,
    judge_display_method,
    judge_explanation_duty,
    preprocess_product_page,
    retry_dispatch,
    search_cases,
    verify_answer,
)
from .routes import route_after_classify, route_after_verify


def build_review_graph(checkpointer=None):
    builder = StateGraph(State, context_schema=Context)
    builder.add_node("preprocess_product_page", preprocess_product_page)
    builder.add_node("classify_type", classify_type)
    builder.add_node("search_cases", search_cases)
    builder.add_node("judge_display_method", judge_display_method)
    builder.add_node("generate_plain_lang", generate_plain_lang)
    builder.add_node("judge_explanation_duty", judge_explanation_duty)
    builder.add_node("verify_answer", verify_answer)
    builder.add_node("retry_dispatch", retry_dispatch)
    builder.add_node("end_report", end_report)

    builder.add_edge(START, "preprocess_product_page")
    builder.add_edge("preprocess_product_page", "classify_type")
    builder.add_conditional_edges(
        "classify_type",
        route_after_classify,
        {"search_cases": "search_cases", END: END},
    )
    builder.add_edge("search_cases", "judge_display_method")
    builder.add_edge("judge_display_method", "generate_plain_lang")
    builder.add_edge("generate_plain_lang", "judge_explanation_duty")
    builder.add_edge("judge_explanation_duty", "verify_answer")
    builder.add_conditional_edges(
        "verify_answer",
        route_after_verify,
        {"retry_dispatch": "retry_dispatch", "end_report": "end_report"},
    )
    builder.add_edge("retry_dispatch", "judge_display_method")
    builder.add_edge("end_report", END)
    return builder.compile(checkpointer=checkpointer)
