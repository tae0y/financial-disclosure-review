"""Conditional edges; a non-review result still goes through the free `end_report`, not empty."""

from ..core.state import State
from .retry import NODE_ORDER, should_retry

NON_REVIEW = ("범위 밖", "판정 불가")


def route_after_preprocess(state: State) -> str:
    """No collected html (수집 실패, or no accepted rule) means nothing to review: report why."""
    return "classify_type" if (state.get("product_page") or {}).get("html") else "end_report"


def route_after_classify(state: State) -> str:
    if state["classification"].get("product_type") in NON_REVIEW:
        return "end_report"
    return "extract_evidence_cards"


def route_after_verify(state: State) -> str:
    """Retry only when a node can act on feedback; otherwise `end_report` marks it for a person."""
    return "retry_dispatch" if should_retry(state.get("verification") or {}) else "end_report"


def route_after_retry(state: State) -> list[str] | str:
    """Every node `retry_dispatch` picked (they run in one step); `end_report` when there is none,
    instead of looping on empty."""
    verification = state.get("verification") or {}
    targets = [n for n in verification.get("retry_targets") or [] if n in NODE_ORDER]
    target = verification.get("retry_target")
    if not targets and target in NODE_ORDER:
        targets = [str(target)]
    return targets or "end_report"
