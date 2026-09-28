"""`summarize` narrows the final State for the wire. What it must never carry is the page itself."""

from financial_disclosure_review.serving.agent.runner import new_thread_id, summarize
from financial_disclosure_review.serving.schemas import Detail

STATE = {
    "product_page": {
        "url": "https://example.test/card",
        "product": {"product_name": "카드", "summary": "요약"},
        "html": "<html>" + "x" * 500_000 + "</html>",
        "snapshots": ["a.html", "b.html", "c.html"],
        "actions": [{"kind": "click", "selector": "#more"}],
    },
    "classification": {"product_type": "신용카드", "page_type": "상품안내", "reason": "이유"},
    "display_check": {
        "items": [
            {"code": "D-01", "verdict": "적합", "reason": "충족", "quotes": ["인용"]},
            {"code": "D-02", "verdict": "부적합", "reason": "누락", "quotes": []},
        ],
        "judgments": {"status": "부적합", "reason": "1건 위반"},
    },
    "plain_language": {
        "accepted_blocks": ["b1", "b2"],
        "contract_errors": ["e1"],
        "html": "<section>쉬운말</section>",
        "items": [{"block": "b1"}],
    },
    "explanation_duty_check": {
        "items": [{"code": "E-01", "applied": True}, {"code": "E-02", "applied": False}],
        "original": [{"code": "E-01", "verdict": "적합"}],
        "plain": [{"code": "E-01", "verdict": "적합"}],
        "fidelity": [{"code": "E-01", "kind": "축약"}],
    },
    "verification": {"passed": False, "failed_modules": ["display_check"], "loop_count": 1},
    "report": {"status": "사람 검토 필요", "markdown": "# 보고서"},
}


def _flat(value) -> str:
    """Every string anywhere in the view, so a leak cannot hide inside a nested dict."""
    if isinstance(value, dict):
        return "".join(_flat(item) for item in value.values())
    if isinstance(value, list):
        return "".join(_flat(item) for item in value)
    return str(value)


def test_summary_reports_page_size_instead_of_the_page() -> None:
    view = summarize(STATE)
    assert view["product_page"]["html_chars"] == len(STATE["product_page"]["html"])
    assert view["product_page"]["snapshot_count"] == 3
    assert "html" not in view["product_page"]
    assert "x" * 1000 not in _flat(view)


def test_full_detail_still_withholds_the_source_page() -> None:
    view = summarize(STATE, Detail.full)
    assert view["plain_language"]["html"] == "<section>쉬운말</section>"
    assert view["explanation_duty_check"]["fidelity"] == [{"code": "E-01", "kind": "축약"}]
    assert "html" not in view["product_page"]
    assert "x" * 1000 not in _flat(view)


def test_summary_counts_what_a_caller_polls_for() -> None:
    view = summarize(STATE)
    assert view["display_check"]["status"] == "부적합"
    assert view["display_check"]["item_count"] == 2
    assert [row["verdict"] for row in view["display_check"]["verdicts"]] == ["적합", "부적합"]
    assert view["plain_language"]["accepted_blocks"] == 2
    assert view["plain_language"]["contract_errors"] == 1
    assert view["explanation_duty_check"]["applied"] == 1
    assert view["explanation_duty_check"]["fidelity_differences"] == 1
    assert view["verification"]["passed"] is False


def test_summary_omits_the_item_rows_that_full_adds() -> None:
    summary, full = summarize(STATE), summarize(STATE, Detail.full)
    assert "items" not in summary["display_check"]
    assert "items" in full["display_check"]
    assert "fidelity" not in summary["explanation_duty_check"]


def test_an_empty_state_summarizes_without_raising() -> None:
    view = summarize({key: {} for key in STATE})
    assert view["product_page"] == {
        "url": None,
        "product": None,
        "html_chars": 0,
        "snapshot_count": 0,
        "status": None,
        "stop_reason": None,
        "error": None,
        "open_gaps": 0,
        "agent_steps": 0,
    }
    assert view["display_check"]["item_count"] == 0
    assert view["verification"]["passed"] is None


def test_thread_ids_do_not_collide_within_a_second() -> None:
    ids = {new_thread_id() for _ in range(50)}
    assert len(ids) == 50
    assert all(name.startswith("review-") for name in ids)
