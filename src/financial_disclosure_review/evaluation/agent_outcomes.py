"""One outcome per requested page of a live review batch, and rates over all of them.

A page that crashed without a report, or whose thread was never checkpointed, is a failed
page in the denominator, not a page left out (audit 2026-09-29 R5). `complete` means the page
agent finished collection and the review produced a report; the report's own verdict (검토
완료, 사람 검토 필요, ...) is a judgment outcome, measured elsewhere.
"""

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

WITH_REPORT = ("complete", "insufficient", "collection_failed", "interrupted")


def page_outcome(state: Mapping[str, Any] | None) -> str:
    """complete | insufficient | collection_failed | interrupted | no_report | no_checkpoint"""
    if state is None:
        return "no_checkpoint"
    report = state.get("report") or {}
    if not report.get("status"):
        return "no_report"
    if (report.get("summary") or {}).get("interrupted_at"):
        return "interrupted"
    page_status = (state.get("product_page") or {}).get("status")
    if page_status == "수집 실패":
        return "collection_failed"
    if page_status == "조사 불충분":
        return "insufficient"
    return "complete" if page_status == "완료" else "no_report"


def outcome_rates(outcomes: Iterable[str]) -> dict[str, Any]:
    outcomes = list(outcomes)
    count = len(outcomes)

    def rate(n: int) -> float | None:
        return round(n / count, 3) if count else None

    return {
        "requested": count,
        "success_rate": rate(sum(o == "complete" for o in outcomes)),
        "report_rate": rate(sum(o in WITH_REPORT for o in outcomes)),
        "outcomes": dict(Counter(outcomes)),
    }
