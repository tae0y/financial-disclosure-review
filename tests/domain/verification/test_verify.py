"""verify cross-checks the three modules against each other and against the input text."""

import pytest

from financial_disclosure_review.domain.verification import verify

PRODUCT_HTML = (
    "<html><body>"
    "<p>이 카드의 연회비는 15000원입니다.</p>"
    "<p>단기카드대출 이자율은 연 20%입니다.</p>"
    "</body></html>"
)
PLAIN_HTML = (
    "<html><body>"
    "<p>이 카드는 매년 15000원의 회비를 냅니다.</p>"
    "<p>돈을 짧게 빌리면 이자가 연 20%입니다.</p>"
    "</body></html>"
)


def sound_input() -> dict:
    """모든 검사를 무사히 통과하는 최소 입력. 각 시나리오는 이것을 새로 만들어
    필요한 부분만 망가뜨린다."""
    return {
        "page": {"url": "https://example.com", "product": {}, "html": PRODUCT_HTML},
        "display_check": {
            "items": [
                {
                    "code": "E02",
                    "verdict": "적합",
                    "block_ids": ["blk1"],
                    "quotes": ["연회비는 15000원"],
                    "measured": [{"id": "blk1", "pt": 10}],
                    "reason": "폰트 크기 충분",
                },
            ],
            "judgments": {
                "status": "완료",
                "skipped": [{"code": "E07", "reason": "이 상품 유형에는 적용되지 않음"}],
                "blocks": [{"id": "blk1", "pt": 10}],
                "measures": {"E02": {"below_min_pt": []}},
            },
        },
        "plain_language": {
            "accepted_blocks": [
                {
                    "source_id": "b1",
                    "source_quote": "이 카드의 연회비는 15000원입니다.",
                    "text": "이 카드는 매년 15000원의 회비를 냅니다.",
                },
                {
                    "source_id": "b2",
                    "source_quote": "단기카드대출 이자율은 연 20%입니다.",
                    "text": "돈을 짧게 빌리면 이자가 연 20%입니다.",
                },
            ],
            "contract_errors": [],
            "html": PLAIN_HTML,
        },
        "explanation_duty_check": {
            "items": ["E02"],
            "original": [
                {"code": "E02", "verdict": "적합", "quote": "연회비는 15000원", "reason": "기재됨"}
            ],
            "plain": [
                {
                    "code": "E02",
                    "verdict": "적합",
                    "quote": "매년 15000원의 회비",
                    "reason": "기재됨",
                }
            ],
            "fidelity": [],
        },
        "loop_count": 0,
    }


def run(state: dict) -> dict:
    return verify(
        state["page"],
        state["display_check"],
        state["plain_language"],
        state["explanation_duty_check"],
        state["loop_count"],
    )


def test_a_sound_set_of_answers_passes():
    result = run(sound_input())
    assert result["passed"] is True, result
    assert result["failed_modules"] == []
    assert result["loop_count"] == 1


def test_a_missing_upstream_module_fails_that_module():
    state = sound_input()
    state["explanation_duty_check"] = {}
    result = run(state)
    assert result["passed"] is False
    assert "explanation_duty_check" in result["failed_modules"]


def test_a_block_id_that_was_never_measured_fails_display_check():
    state = sound_input()
    state["display_check"]["items"][0]["block_ids"] = ["blk_unknown"]
    result = run(state)
    assert result["passed"] is False
    assert "display_check" in result["failed_modules"]


def test_a_quote_that_is_not_in_the_page_fails_the_explanation_duty_check():
    state = sound_input()
    state["explanation_duty_check"]["original"][0]["quote"] = "이 문장은 원문 어디에도 없습니다"
    result = run(state)
    assert result["passed"] is False
    assert "explanation_duty_check" in result["failed_modules"]


def test_a_quote_request_names_the_side_it_belongs_to():
    """The duty check re-judges only the flagged side, so the request must say which one."""
    state = sound_input()
    state["explanation_duty_check"]["original"][0]["quote"] = "이 문장은 원문 어디에도 없습니다"
    result = run(state)
    requests = [f for f in result["feedback"] if f["module"] == "explanation_duty_check"]
    assert requests, result["feedback"]
    assert {f["target"] for f in requests} == {"original"}
    assert all(f["code"] for f in requests)


def test_a_pass_that_contradicts_the_measurement_fails():
    state = sound_input()
    state["display_check"]["judgments"]["measures"]["E02"]["below_min_pt"] = ["blk1"]
    result = run(state)
    assert result["passed"] is False
    assert "display_check" in result["failed_modules"]
    assert any("모순" in reason for reason in result["reasons"])


def test_a_fidelity_gap_is_the_plain_languages_problem_not_the_duty_checks():
    state = sound_input()
    state["explanation_duty_check"]["fidelity"] = [
        {"source_id": "b2", "kind": "누락", "reason": "이자율 20%가 쉬운말에서 빠졌습니다"}
    ]
    result = run(state)
    assert result["passed"] is False
    assert "plain_language" in result["failed_modules"]
    assert "explanation_duty_check" not in result["failed_modules"]


def test_a_contract_error_left_over_fails_plain_language():
    state = sound_input()
    state["plain_language"]["contract_errors"] = [{"source_id": "b1", "reason": "필수 문구 누락"}]
    result = run(state)
    assert result["passed"] is False
    assert "plain_language" in result["failed_modules"]


@pytest.mark.parametrize("module", ["display_check", "explanation_duty_check"])
def test_an_unjudgeable_answer_is_never_counted_as_a_pass(module):
    state = sound_input()
    if module == "display_check":
        state["display_check"]["judgments"]["status"] = "판정 불가"
        state["display_check"]["judgments"]["reason"] = "필요한 스냅샷 없음"
        state["display_check"]["items"] = []
    else:
        state["explanation_duty_check"]["original"][0]["verdict"] = "판정 불가"
    result = run(state)
    assert result["passed"] is False
    assert module in result["failed_modules"]


def test_the_loop_count_carries_the_previous_value_forward():
    state = sound_input()
    state["loop_count"] = 2
    assert run(state)["loop_count"] == 3


def test_a_nonconforming_row_may_cite_nothing_because_the_explanation_is_missing():
    """부적합은 '설명이 없다'는 판정이라 인용할 문장이 없습니다. 빈 인용을 실패로 보면 재시도가
    같은 답으로 끝나고 상태가 늘 '사람 검토 필요'가 됩니다(2026-09-28 감사 P0-1)."""
    state = sound_input()
    state["explanation_duty_check"]["original"][0].update(verdict="부적합", quote="")
    result = run(state)
    assert "explanation_duty_check" not in result["failed_modules"], result["reasons"]


def test_a_conforming_row_still_needs_a_quote():
    state = sound_input()
    state["explanation_duty_check"]["original"][0].update(verdict="적합", quote="")
    assert "explanation_duty_check" in run(state)["failed_modules"]
