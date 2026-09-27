"""Conditional edges. A non-review result ends the graph; it is not an error."""

from langgraph.graph import END

from ..core.state import State


def route_after_classify(state: State) -> str:
    if state["classification"].get("product_type") in ("범위 밖", "판정 불가"):
        return END
    return "judge_display_method"


def route_after_verify(state: State) -> str:
    return "end_report"
