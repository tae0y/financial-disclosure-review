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
        {
            "code": "E02",
            "verdict": "적합",
            "block_ids": ["v1-3"],
            "quotes": ["연회비 1만원"],
            "measured": [],
            "reason": "9pt 이상",
        },
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
    "original": [
        {
            "code": "설명01",
            "condition_status": "성립",
            "verdict": "적합",
            "quote": "연회비 1만원",
            "reason": "표기됨",
        }
    ],
    "plain": [
        {
            "code": "설명01",
            "condition_status": "성립",
            "verdict": "적합",
            "quote": "1년에 1만원",
            "reason": "유지됨",
        }
    ],
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
            {
                "code": f"설명{n:02d}",
                "condition_status": "성립",
                "verdict": "부적합",
                "quote": "연회비 1만원",
                "reason": "누락",
            }
            for n in range(1, 16)
        ],
    }
    result = report(duty=duty)
    assert len(result["findings"]) == 15
    grouped = [a for a in result["actions"] if a.startswith("원문 권고 미충족")]
    assert len(grouped) == 1, result["actions"]
    assert "15건" in grouped[0]
    assert "외 3건" in grouped[0], "12개까지만 코드로 보여 주고 나머지는 건수로"


def test_an_unjudged_display_item_becomes_a_human_task_not_a_pass():
    display = {
        **DISPLAY_OK,
        "items": [
            {
                "code": "E04",
                "verdict": "판정 불가",
                "block_ids": [],
                "quotes": [],
                "measured": [],
                "reason": "이미지 안 글자는 측정 불가",
            }
        ],
    }
    result = report(display=display)
    assert result["status"] == "사람 검토 필요"
    assert [row["code"] for row in result["findings"]] == ["E04"]
    assert any("판정 불가" in action for action in result["actions"])


def test_a_violation_blocks_the_plain_language_from_being_published():
    duty = {
        **DUTY_OK,
        "original": [
            {
                "code": "설명01",
                "condition_status": "성립",
                "verdict": "부적합",
                "quote": "연회비 1만원",
                "reason": "중도해지 손실 문구 없음",
            }
        ],
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


def display_with(code: str, verdict: str = "부적합") -> dict:
    return {
        **DISPLAY_OK,
        "items": [
            {
                "code": code,
                "verdict": verdict,
                "block_ids": [],
                "quotes": [],
                "measured": [],
                "reason": "측정값 미달",
            }
        ],
    }


def duty_with(code: str) -> dict:
    return {
        **DUTY_OK,
        "original": [
            {
                "code": code,
                "condition_status": "해당없음",
                "verdict": "부적합",
                "quote": "",
                "reason": "누락",
            }
        ],
    }


def test_a_display_rule_binds_an_ad_page_directly_so_its_failure_is_a_violation():
    result = report(display=display_with("E02"), bindings={"E02": "협회 자율규제"})
    row = next(f for f in result["findings"] if f["code"] == "E02")
    assert (row["severity"], row["basis"]) == ("위반", "협회 자율규제")
    expected = "판매 화면 표시방법 위반(협회 자율규제) 1건"
    assert any(a.startswith(expected) for a in result["actions"]), result["actions"]
    assert result["summary"]["violations"] == 1 and result["summary"]["shortfalls"] == 0


def test_an_explanation_item_on_an_ad_page_is_applied_by_analogy_so_it_is_a_shortfall():
    # 설명의무(제19조) is a contract-stage duty; on an ad page it is applied by analogy.
    result = report(duty=duty_with("F01"), bindings={"F01": "법령"})
    row = next(f for f in result["findings"] if f["code"] == "F01")
    assert (row["severity"], row["basis"]) == ("권고 미충족", "설명의무 준용")
    assert "권고 미충족(설명의무 준용)" in result["markdown"]


def test_the_same_item_on_a_solicitation_screen_is_a_violation():
    screen = {**CLASSIFICATION, "page_type": "권유"}
    result = report(classification=screen, duty=duty_with("F01"), bindings={"F01": "법령"})
    row = next(f for f in result["findings"] if f["code"] == "F01")
    assert (row["severity"], row["basis"]) == ("위반", "법령")


def test_a_guideline_never_makes_a_violation():
    result = report(display=display_with("E09"), bindings={"E09": "금융위 가이드라인"})
    row = next(f for f in result["findings"] if f["code"] == "E09")
    assert (row["severity"], row["basis"]) == ("권고 미충족", "금융위 가이드라인")


def test_an_item_of_unknown_binding_keeps_the_stricter_reading():
    result = report(display=display_with("E02"))
    row = next(f for f in result["findings"] if f["code"] == "E02")
    assert (row["severity"], row["basis"]) == ("위반", "구속력 미상")


def test_a_rebuilt_report_carries_the_reviews_own_cost_forward():
    """Rebuilding from a checkpoint makes no call; the reviewer must still see what the review
    cost, not the rebuild's zero."""
    recorded = {
        "calls": 20,
        "elapsed_seconds": 513.1,
        "input_tokens": 160934,
        "output_tokens": 53767,
        "usd": 0.147718,
        "krw": 206.8,
        "usd_krw": 1400.0,
        "by_step": {"ExplanationJudgments": {"calls": 3, "input": 1, "output": 1, "usd": 0.06}},
        "caps": {"max_calls": 60, "max_usd": 1.0},
    }
    result = report(previous_cost=recorded)
    assert result["cost"]["calls"] == 20 and result["cost"]["carried_forward"] is True
    assert "원래 검토 실행" in result["markdown"]
    assert "모델 호출 20회" in result["markdown"]
    assert "ExplanationJudgments 3회" in result["markdown"]


def test_a_run_that_made_calls_reports_its_own_cost_not_the_previous_one():
    from financial_disclosure_review.core.usage import current

    start_run()
    current().record("gpt-5-mini", "ExplanationJudgments", 1000, 500)
    result = build_report(
        PAGE,
        CLASSIFICATION,
        DISPLAY_OK,
        PLAIN_OK,
        DUTY_OK,
        PASSED,
        {"max_loops": 2},
        previous_cost={"calls": 99, "usd": 9.9},
    )
    assert result["cost"]["calls"] == 1
    assert "carried_forward" not in result["cost"]


FAILED_PAGE = {
    "url": "https://example.test/card",
    "html": "",
    "status": "수집 실패",
    "stop_reason": "fetch_error",
    "error": "HTTP 503 Service Unavailable",
    "coverage": {"before": {}, "after": {}, "gaps": []},
    "agent_trace": [],
}


def test_a_collection_failure_is_reported_as_such_not_as_a_classification_problem():
    result = report(
        page=FAILED_PAGE,
        classification={},
        display={},
        plain={},
        duty={},
        verification={},
    )
    assert result["status"] == "수집 실패"
    assert any("fetch_error" in action and "HTTP 503" in action for action in result["actions"])
    assert "상품 유형을 확정하지 못해" not in result["markdown"]
    assert "## 10. 페이지 수집 agent 기록" in result["markdown"]


def test_no_accepted_rule_reads_as_an_insufficient_investigation():
    page = {**FAILED_PAGE, "status": "조사 불충분", "stop_reason": "max_turns", "error": ""}
    result = report(page=page, classification={}, display={}, plain={}, duty={}, verification={})
    assert result["status"] == "조사 불충분"
    assert any("max_turns" in action for action in result["actions"])


def test_an_open_evidence_gap_keeps_a_clean_run_from_reading_as_done():
    page = {
        **PAGE,
        "html": "<p>연회비 1만원</p>",
        "status": "조사 불충분",
        "stop_reason": "no_viable_control",
        "coverage": {
            "before": {"hidden_text_blocks": 2},
            "after": {"hidden_text_blocks": 2},
            "gaps": [
                {
                    "id": "gap-1",
                    "kind": "hidden_text",
                    "detail": "본문 영역에 숨은 텍스트 2개",
                    "target": "div.notice",
                    "status": "unresolved",
                    "closed_by": None,
                }
            ],
        },
        "agent_trace": [
            {
                "turn": 1,
                "tool": "inspect_page",
                "args": {},
                "rationale": {},
                "blocked": False,
                "new_evidence": False,
            }
        ],
    }
    result = report(page=page)
    assert result["status"] == "사람 검토 필요"
    assert result["actions"][0].startswith("페이지 수집 조사 불충분(no_viable_control)")
    assert "gap-1" in result["markdown"]
    assert "누락의 증거가 아닙니다" in result["markdown"]


def test_a_completed_collection_adds_no_action():
    page = {**PAGE, "html": "<p>연회비 1만원</p>", "status": "완료", "stop_reason": "full_coverage"}
    result = report(page=page)
    assert result["status"] == "검토 완료"
    assert not any(action.startswith("페이지 수집") for action in result["actions"])


CARDS = {
    "status": "완료",
    "reason": "",
    "sources": [
        {"source_id": "dom-0", "text": "연회비 1만원", "visibility": "hidden"},
        {"source_id": "dom-1", "text": "커피 10% 할인", "visibility": "default_visible"},
    ],
    "cards": [
        {
            "id": "c1",
            "kind": "fee_claim",
            "quote": "연회비 1만원",
            "qualifiers": [],
            "exceptions": [],
            "numbers": ["1만원"],
            "source_id": "dom-0",
            "visibility": "hidden",
        }
    ],
    "rejected": [],
    "coverage_gaps": [{"kind": "hidden_text", "card_ids": ["c1"], "status": "unresolved"}],
}
REFERENCES = {
    "status": "완료",
    "method": {"threshold": 10.0, "cases_from": "db"},
    "candidates": [{"case_id": "case.x"}],
    "links": [
        {
            "case_id": "case.x",
            "card_ids": ["c1"],
            "page_quote": "연회비 1만원",
            "case_quote": "",
            "case_quote_note": "원문 재확인 필요",
            "material_difference": ["record_type 지적사례"],
            "page_only_detectability": "partial",
            "page_only_note": "페이지 단독 판단 불가",
            "official_url": "https://example.test/case",
        }
    ],
}


def test_cards_and_reference_cases_get_their_own_report_only_sections():
    result = report(cards=CARDS, references=REFERENCES)
    markdown = result["markdown"]
    assert "## 11. 증거 카드와 조사 공백" in markdown
    assert "## 12. 참고 사례 (판정에 사용하지 않음)" in markdown
    assert "페이지 단독 판단 불가" in markdown and "원문 재확인 필요" in markdown
    assert result["summary"]["evidence_cards"] == 1
    assert result["summary"]["reference_links"] == 1
    # A reference link never changes the verdict: the clean run still reads as done.
    assert result["status"] == "검토 완료"


def test_a_pass_that_rests_only_on_hidden_text_is_named_as_a_limit():
    """원문 적합의 인용이 화면에 보이지 않은 문장에만 있으면, 사람이 노출 여부를 확인해야 합니다."""
    result = report(cards=CARDS)
    assert any("설명01" in limit and "보이지 않았거나" in limit for limit in result["limits"])
