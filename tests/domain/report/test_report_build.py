"""검토 보고서: 판정 불가는 통과가 아니라 사람 확인 항목으로 나와야 한다."""

from financial_disclosure_review.core.usage import start_run
from financial_disclosure_review.domain.report import build_report

PAGE = {
    "url": "https://example.test/card",
    "product": {"product_name": "테스트카드", "summary": "요약", "evidence": "근거"},
}
CLASSIFICATION = {"product_type": "신용카드", "page_type": "상품광고", "reason": "3단계 통과"}
DISPLAY_OK = {
    "items": [
        {"code": "E02", "verdict": "적합", "block_ids": ["v1-3"], "quotes": ["연회비 1만원"],
         "measured": [], "reason": "9pt 이상"},
    ],
    "judgments": {"status": "완료", "assumptions": {"font_size": "px x 0.75"}, "limits": {}},
}
PLAIN_OK = {
    "accepted_blocks": [
        {"source_id": "b0", "source_quote": "연회비 1만원", "text": "1년에 1만원을 냅니다."}
    ],
    "contract_errors": [],
    "term_refs": [{"term": "연회비", "source_id": "b0", "gloss": "카드를 1년 쓰는 값"}],
}
DUTY_OK = {
    "items": [{"code": "설명01", "applied": True, "condition_status": "성립", "reason": ""}],
    "original": [{"code": "설명01", "condition_status": "성립", "verdict": "적합",
                  "quote": "연회비 1만원", "reason": "표기됨"}],
    "plain": [{"code": "설명01", "condition_status": "성립", "verdict": "적합",
               "quote": "1년에 1만원", "reason": "유지됨"}],
    "fidelity": [],
}
PASSED = {"passed": True, "reasons": [], "failed_modules": [], "feedback": [], "loop_count": 1}


def report(**overrides):
    start_run()
    args = {
        "page": PAGE,
        "classification": CLASSIFICATION,
        "display": DISPLAY_OK,
        "plain": PLAIN_OK,
        "duty": DUTY_OK,
        "verification": PASSED,
        "stop": {"max_loops": 2},
    }
    args.update(overrides)
    return build_report(**args)


def test_a_clean_run_is_reported_as_done_and_lists_no_finding():
    result = report()
    assert result["status"] == "검토 완료"
    assert result["decision"].startswith("담당자 확인 후")
    assert result["findings"] == []
    assert result["summary"]["display_violations"] == 0
    assert result["summary"]["plain_blocks"] == 1


def test_the_markdown_carries_the_frontmatter_and_every_section():
    markdown = report()["markdown"]
    assert markdown.startswith("---\nai-generated: true\nhuman-review: false\n---")
    for heading in (
        "## 1. 담당자 조치 목록",
        "## 2. 검토 요약",
        "## 3. 확인이 필요한 항목",
        "## 4. 표시방법 검토 상세",
        "## 5. 설명의무 검토 상세",
        "## 6. 쉬운말 변환 결과",
        "## 7. 자동 검증 결과",
        "## 8. 비용과 소요시간",
        "## 9. 한계와 가정",
    ):
        assert heading in markdown, heading
    assert "1년에 1만원을 냅니다." in markdown, "쉬운말 결과가 보고서에 실려야 함"
    assert "연회비" in markdown, "용어 풀이가 보고서에 실려야 함"


def test_the_actions_are_grouped_by_target_rather_than_one_line_per_item():
    """항목이 수십 개일 때 조치 목록이 수십 줄이 되지 않아야 합니다."""
    duty = {
        **DUTY_OK,
        "original": [
            {"code": f"설명{n:02d}", "condition_status": "성립", "verdict": "부적합",
             "quote": "연회비 1만원", "reason": "누락"}
            for n in range(1, 16)
        ],
    }
    result = report(duty=duty)
    assert len(result["findings"]) == 15
    grouped = [a for a in result["actions"] if a.startswith("원문 위반")]
    assert len(grouped) == 1, result["actions"]
    assert "15건" in grouped[0]
    assert "외 3건" in grouped[0], "12개까지만 코드로 보여 주고 나머지는 건수로"


def test_an_unjudged_display_item_becomes_a_human_task_not_a_pass():
    display = {
        **DISPLAY_OK,
        "items": [
            {"code": "E04", "verdict": "판정 불가", "block_ids": [], "quotes": [],
             "measured": [], "reason": "이미지 안 글자는 측정 불가"}
        ],
    }
    result = report(display=display)
    assert result["status"] == "사람 검토 필요"
    assert [row["code"] for row in result["findings"]] == ["E04"]
    assert any("판정 불가" in action for action in result["actions"])


def test_a_violation_blocks_the_plain_language_from_being_published():
    duty = {
        **DUTY_OK,
        "original": [{"code": "설명01", "condition_status": "성립", "verdict": "부적합",
                      "quote": "연회비 1만원", "reason": "중도해지 손실 문구 없음"}],
    }
    result = report(duty=duty)
    assert result["status"] == "사람 검토 필요"
    assert result["decision"] == "쉬운말 자동 게시 불가 — 원문 유지"
    assert result["summary"]["duty_violations_original"] == 1


def test_a_fidelity_difference_is_reported_as_a_finding():
    duty = {
        **DUTY_OK,
        "fidelity": [{"code": "설명01", "source_id": "b0", "kind": "누락", "reason": "조건 빠짐"}],
    }
    result = report(duty=duty)
    assert result["summary"]["fidelity_diffs"] == 1
    assert any(row["module"] == "explanation_duty_check" for row in result["findings"])


def test_a_failed_verification_escalates_with_the_stop_reason():
    failed = {
        "passed": False,
        "reasons": ["수치 근거 없음"],
        "failed_modules": ["plain_language"],
        "feedback": [],
        "loop_count": 2,
    }
    result = report(
        verification=failed,
        stop={"reason": "재시도 한도 초과", "detail": "2회 모두 미달", "max_loops": 2},
    )
    assert result["status"] == "사람 검토 필요"
    assert result["decision"] == "쉬운말 자동 게시 불가 — 원문 유지"
    assert "에스컬레이션" in result["actions"][0]
    assert "재시도 한도 초과" in result["markdown"]


def test_an_out_of_scope_page_reports_why_and_stops():
    result = report(
        classification={
            "product_type": "범위 밖",
            "page_type": None,
            "reason": "1단계: 목록 페이지",
        },
        display={},
        plain={},
        duty={},
        verification={"passed": False, "failed_modules": ["display_check"], "loop_count": 1},
    )
    assert result["status"] == "검토 대상 아님"
    assert "1단계" in result["actions"][0]


def test_the_cost_is_reported_from_the_run_meter():
    start_run(max_calls=10, max_usd=0.5)
    from financial_disclosure_review.core.usage import current

    current().record("gpt-5-mini", "DisplayVerdicts", 1_000_000, 100_000)
    result = build_report(
        PAGE, CLASSIFICATION, DISPLAY_OK, PLAIN_OK, DUTY_OK, PASSED, {"max_loops": 2}
    )
    assert result["cost"]["calls"] == 1
    assert result["cost"]["usd"] == 0.45
    assert result["cost"]["caps"] == {"max_calls": 10, "max_usd": 0.5}
    assert "$0.45" in result["markdown"]


def test_the_limits_section_always_states_that_a_pass_is_not_legal_compliance():
    assert any("법률 준수" in limit for limit in report()["limits"])
