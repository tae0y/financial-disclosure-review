"""verify cross-checks the three modules against each other and against the input text."""

import pytest

from financial_disclosure_review.domain.verification import verify

PRODUCT_HTML = (
    "<html><body>"
    "<p>이 카드의 연회비는 15000원입니다.</p>"
    "<p>단기카드대출 이자율은 연 20%입니다.</p>"
    "</body></html>"
)
ADVICE = "계약 전에 청약 철회 방법과 연회비 반환 조건을 상품설명서에서 꼭 확인해 보세요."
ADVICE_HTML = f'<section data-role="advice"><p>{ADVICE}</p></section>'


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
        "persona_explanation": {
            "status": "완료",
            "advice": ADVICE,
            "advice_codes": ["설명16", "설명11"],
            "problems": [],
            "html": ADVICE_HTML,
        },
        "ad_disclosure_check": {
            "items": ["E02"],
            "original": [
                {"code": "E02", "verdict": "적합", "quote": "연회비는 15000원", "reason": "기재됨"}
            ],
        },
        "loop_count": 0,
    }


def run(state: dict) -> dict:
    return verify(
        state["page"],
        state["display_check"],
        state["persona_explanation"],
        state["ad_disclosure_check"],
        state["loop_count"],
    )


def test_a_sound_set_of_answers_passes():
    result = run(sound_input())
    assert result["passed"] is True, result
    assert result["failed_modules"] == []
    assert result["loop_count"] == 1


def test_a_missing_upstream_module_fails_that_module():
    state = sound_input()
    state["ad_disclosure_check"] = {}
    result = run(state)
    assert result["passed"] is False
    assert "ad_disclosure_check" in result["failed_modules"]


def test_a_block_id_that_was_never_measured_fails_display_check():
    state = sound_input()
    state["display_check"]["items"][0]["block_ids"] = ["blk_unknown"]
    result = run(state)
    assert result["passed"] is False
    assert "display_check" in result["failed_modules"]


def test_a_quote_that_is_not_in_the_page_fails_the_disclosure_check():
    state = sound_input()
    state["ad_disclosure_check"]["original"][0]["quote"] = "이 문장은 원문 어디에도 없습니다"
    result = run(state)
    assert result["passed"] is False
    assert "ad_disclosure_check" in result["failed_modules"]


def test_a_quote_request_names_the_side_it_belongs_to():
    """The disclosure check re-judges only the flagged side, so the request must say which one."""
    state = sound_input()
    state["ad_disclosure_check"]["original"][0]["quote"] = "이 문장은 원문 어디에도 없습니다"
    result = run(state)
    requests = [f for f in result["feedback"] if f["module"] == "ad_disclosure_check"]
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


def test_an_advice_held_back_by_its_checks_asks_for_a_new_draft():
    state = sound_input()
    state["persona_explanation"].update(
        status="원문 대체", html="", problems=["원문에 없는 수치: 24"]
    )
    result = run(state)
    requests = [f for f in result["feedback"] if f["module"] == "persona_explanation"]
    assert requests and "24" in requests[0]["requested_change"]


def test_an_invented_number_in_the_advice_fails():
    state = sound_input()
    state["persona_explanation"]["html"] = "<section><p>이자는 연 25%입니다.</p></section>"
    assert "persona_explanation" in run(state)["failed_modules"]


@pytest.mark.parametrize("module", ["display_check", "ad_disclosure_check"])
def test_an_unjudgeable_answer_is_never_counted_as_a_pass(module):
    state = sound_input()
    if module == "display_check":
        state["display_check"]["judgments"]["status"] = "판정 불가"
        state["display_check"]["judgments"]["reason"] = "필요한 스냅샷 없음"
        state["display_check"]["items"] = []
    else:
        state["ad_disclosure_check"]["original"][0]["verdict"] = "판정 불가"
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
    state["ad_disclosure_check"]["original"][0].update(verdict="부적합", quote="")
    result = run(state)
    assert "ad_disclosure_check" not in result["failed_modules"], result["reasons"]


def test_a_conforming_row_still_needs_a_quote():
    state = sound_input()
    state["ad_disclosure_check"]["original"][0].update(verdict="적합", quote="")
    assert "ad_disclosure_check" in run(state)["failed_modules"]
