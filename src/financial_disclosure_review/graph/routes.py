"""Conditional edges; a non-review result still goes through the free `end_report`, not empty."""

from ..core.state import State
from .retry import NODE_ORDER, should_retry

NON_REVIEW = ("범위 밖", "판정 불가")


def route_after_classify(state: State) -> str:
    if state["classification"].get("product_type") in NON_REVIEW:
        return "end_report"
    return "search_cases"


def route_after_verify(state: State) -> str:
    """Retry only when a node can act on feedback; otherwise `end_report` marks it for a person."""
    return "retry_dispatch" if should_retry(state.get("verification") or {}) else "end_report"


def route_after_retry(state: State) -> str:
    """The node `retry_dispatch` picked; falls back to `end_report` instead of looping on empty."""
    target = (state.get("verification") or {}).get("retry_target")
    return target if target in NODE_ORDER else "end_report"
