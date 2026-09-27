"""Conditional edges. A non-review result skips the checks; it is not an error.

It still goes through `end_report`, because "이 화면은 검토 대상이 아니다" is an answer the
requester has to receive as a document, with the step and the grounds on it — not as an empty
result. `end_report` makes no model call, so this costs nothing.
"""

from ..core.state import State
from .retry import NODE_ORDER, should_retry

NON_REVIEW = ("범위 밖", "판정 불가")


def route_after_classify(state: State) -> str:
    if state["classification"].get("product_type") in NON_REVIEW:
        return "end_report"
    return "search_cases"


def route_after_verify(state: State) -> str:
    """A failed verification is retried only when a node can act on the feedback; otherwise the
    run ends and `end_report` marks it for a person."""
    return "retry_dispatch" if should_retry(state.get("verification") or {}) else "end_report"


def route_after_retry(state: State) -> str:
    """The node `retry_dispatch` picked. An empty target cannot happen through
    `route_after_verify`, so it ends the run rather than looping."""
    target = (state.get("verification") or {}).get("retry_target")
    return target if target in NODE_ORDER else "end_report"
