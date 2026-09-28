"""재시도 정책: 조치 가능한 피드백이 있을 때만 되돌아가고, 아니면 사람에게 넘긴다."""

from financial_disclosure_review.core.state import empty_state
from financial_disclosure_review.graph.retry import (
    MAX_LOOPS,
    escalation,
    plan_retry,
    retryable_modules,
    should_retry,
)
from financial_disclosure_review.graph.routes import route_after_retry, route_after_verify


def verification(**fields) -> dict:
    base = {
        "passed": False,
        "reasons": [],
        "failed_modules": [],
        "feedback": [],
        "loop_count": 1,
    }
    return {**base, **fields}


def feedback_for(module: str, change: str = "이 블록을 다시 생성하세요") -> dict:
    return {
        "module": module,
        "code": "",
        "source_id": "b0",
        "reason": "x",
        "requested_change": change,
    }


def state_of(v: dict) -> dict:
    state = empty_state()
    state["verification"] = v  # type: ignore[typeddict-item]
    return dict(state)


def test_a_passed_verification_is_never_retried():
    v = verification(passed=True)
    assert should_retry(v) is False
    assert route_after_verify(state_of(v)) == "end_report"  # type: ignore[arg-type]


def test_a_failure_with_actionable_feedback_goes_back_to_the_owning_node():
    v = verification(
        failed_modules=["persona_explanation"], feedback=[feedback_for("persona_explanation")]
    )
    assert retryable_modules(v) == ["persona_explanation"]
    assert should_retry(v) is True
    assert route_after_verify(state_of(v)) == "retry_dispatch"  # type: ignore[arg-type]
    plan = plan_retry(v)
    assert plan["retry_target"] == "generate_persona_explanation"
    assert plan["retry_modules"] == ["persona_explanation"]
    assert route_after_retry(state_of({**v, **plan})) == "generate_persona_explanation"  # type: ignore[arg-type]


def test_a_failure_with_no_requested_change_is_not_retried():
    v = verification(
        failed_modules=["explanation_duty_check"],
        feedback=[feedback_for("explanation_duty_check", change="")],
    )
    assert retryable_modules(v) == []
    assert should_retry(v) is False
    assert escalation(v)["reason"] == "조치 가능한 피드백 없음"


def test_display_check_is_escalated_instead_of_retried():
    """judge_display는 피드백을 입력으로 받지 않으므로 다시 호출해도 같은 답이 나온다."""
    v = verification(failed_modules=["display_check"], feedback=[feedback_for("display_check")])
    assert should_retry(v) is False
    assert escalation(v)["reason"] == "자동 재시도 불가"
    assert "display_check" in escalation(v)["detail"]


def test_the_loop_stops_at_the_cap():
    v = verification(
        failed_modules=["persona_explanation"],
        feedback=[feedback_for("persona_explanation")],
        loop_count=MAX_LOOPS,
    )
    assert should_retry(v) is False
    assert route_after_verify(state_of(v)) == "end_report"  # type: ignore[arg-type]
    assert escalation(v)["reason"] == "재시도 한도 초과"


def test_the_earliest_failed_node_is_the_target_so_the_rest_follows_by_edges():
    v = verification(
        failed_modules=["explanation_duty_check", "persona_explanation"],
        feedback=[feedback_for("persona_explanation"), feedback_for("explanation_duty_check")],
    )
    assert plan_retry(v)["retry_target"] == "generate_persona_explanation"


def test_every_round_is_recorded_in_the_history():
    v = verification(
        failed_modules=["persona_explanation"], feedback=[feedback_for("persona_explanation")]
    )
    first = plan_retry(v)
    second = plan_retry({**v, **first, "loop_count": 2})
    assert len(second["retry_history"]) == 2
    assert [row["loop"] for row in second["retry_history"]] == [1, 2]


def test_an_empty_target_ends_the_run_rather_than_looping():
    assert route_after_retry(state_of(verification(retry_target=""))) == "end_report"  # type: ignore[arg-type]
