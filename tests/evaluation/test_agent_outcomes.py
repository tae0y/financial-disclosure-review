"""Failures count in the denominator (audit 2026-09-29 R5): a page without a report or a
checkpoint is a failed page, and a partial result is not a completed one."""

import pytest

from financial_disclosure_review.evaluation.agent_outcomes import outcome_rates, page_outcome


def state(page_status="완료", report_status="검토 완료", interrupted=""):
    report = (
        {"status": report_status, "summary": {"interrupted_at": interrupted}}
        if report_status
        else {}
    )
    return {"product_page": {"status": page_status}, "report": report}


@pytest.mark.parametrize(
    ("given", "outcome"),
    [
        (state(), "complete"),
        (state(report_status="사람 검토 필요"), "complete"),
        (state(page_status="조사 불충분", report_status="조사 불충분"), "insufficient"),
        (state(page_status="수집 실패", report_status="수집 실패"), "collection_failed"),
        (state(report_status=""), "no_report"),
        (state(report_status="판정 불가", interrupted="judge_display_method"), "interrupted"),
        (None, "no_checkpoint"),
    ],
)
def test_each_page_gets_one_outcome(given, outcome):
    assert page_outcome(given) == outcome


def test_rates_use_every_requested_page_as_the_denominator():
    rates = outcome_rates(["complete", "complete", "insufficient", "no_report", "no_checkpoint"])
    assert rates["requested"] == 5
    assert rates["success_rate"] == 0.4
    assert rates["report_rate"] == 0.6
    assert rates["outcomes"] == {
        "complete": 2,
        "insufficient": 1,
        "no_report": 1,
        "no_checkpoint": 1,
    }


def test_no_pages_give_no_rate():
    assert outcome_rates([])["success_rate"] is None
