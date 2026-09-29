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
    headings = [
        "## 1. 표시방법",
        "## 2. 설명의무 (원문)",
        "## 3. 쉬운말 초안",
        "## 4. 쉬운말 초안의 설명의무",
    ]
    positions = [markdown.index(heading) for heading in headings]
    assert positions == sorted(positions)
    assert markdown.index(PAGE["url"]) < positions[0], "원문 정보가 먼저"
    assert "1년에 1만원을 냅니다." in markdown, "쉬운말 결과가 보고서에 실려야 함"


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
    assert result["decision"] == "독자 맞춤 설명 자동 게시 불가 — 원문 유지"
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
    assert result["decision"] == "독자 맞춤 설명 자동 게시 불가 — 원문 유지"
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
    assert "- 사유: 분류 근거 확인: 1단계" in result["markdown"]
    assert "## 1." not in result["markdown"], "검토하지 않은 섹션은 싣지 않음"


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
    assert result["cost"]["by_step"]["ExplanationJudgments"]["calls"] == 3


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
    assert "사유: 페이지 수집 수집 실패(fetch_error) — HTTP 503" in result["markdown"]


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
    assert "수집: 페이지 수집 조사 불충분(no_viable_control)" in result["markdown"]


def test_a_completed_collection_adds_no_action():
    page = {**PAGE, "html": "<p>연회비 1만원</p>", "status": "완료", "stop_reason": "full_coverage"}
    result = report(page=page)
    assert result["status"] == "검토 완료"
    assert not any(action.startswith("페이지 수집") for action in result["actions"])


def test_unreachable_hidden_text_is_a_listed_limitation_not_a_lower_status():
    page = {
        **PAGE,
        "html": "<p>연회비 1만원</p>",
        "status": "완료",
        "stop_reason": "reachable_coverage",
        "coverage": {
            "gaps": [
                {
                    "id": "gap-2",
                    "kind": "hidden_text",
                    "detail": "hidden text: '약관 요약'",
                    "target": "div.notice > p",
                    "status": "unresolved",
                    "closed_by": "",
                }
            ]
        },
    }
    result = report(page=page)
    assert result["status"] == "검토 완료"
    assert "한계: 열 수 있는 컨트롤을 모두 시도해도 보이지 않은 숨김 글 1건" in result["markdown"]
    assert any("보이지 않은 숨김 글 1건" in limit for limit in result["limits"])


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


def test_cards_and_reference_cases_are_counted_but_never_change_the_verdict():
    result = report(cards=CARDS, references=REFERENCES)
    assert result["summary"]["evidence_cards"] == 1
    assert result["summary"]["reference_links"] == 1
    # A reference link never changes the verdict: the clean run still reads as done.
    assert result["status"] == "검토 완료"


def test_a_pass_that_rests_only_on_hidden_text_is_named_as_a_limit():
    """원문 적합의 인용이 화면에 보이지 않은 문장에만 있으면, 사람이 노출 여부를 확인해야 합니다."""
    result = report(cards=CARDS)
    assert any("설명01" in limit and "보이지 않았거나" in limit for limit in result["limits"])


PERSONA = {
    "status": "완료",
    "reason": "",
    "profile": {
        "id": "nemotron-ko-70s-lowfin",
        "version": 1,
        "source": "nvidia/Nemotron-Personas-Korea uuid=x (CC-BY-4.0)",
        "review_status": "ai-drafted",
        "status": "적용",
    },
    "units": [
        {
            "unit_id": "u1",
            "source_ids": ["dom-0"],
            "exact_fact": "연회비 1만원",
            "explanation": "카드를 1년 쓰는 값으로 1만원을 냅니다.",
            "analogy": "",
            "status": "accepted",
            "problems": [],
        },
        {
            "unit_id": "u2",
            "source_ids": ["dom-1"],
            "exact_fact": "연체 시 신용평점 하락",
            "explanation": "",
            "analogy": "",
            "status": "reverted",
            "problems": ["원문에 없는 수치 3"],
        },
    ],
    "controls": {"ui": ["AI 생성 고지"], "governance": ["사람 승인"]},
}


def test_the_persona_explanation_is_reported_with_its_units():
    duty = {
        **DUTY_OK,
        "ledger": [
            {
                "fact_id": "f1",
                "kind": "number",
                "value": "1만원",
                "verdict": "보존",
                "decided_by": "code",
            }
        ],
    }
    result = report(plain=PERSONA, duty=duty)
    markdown = result["markdown"]
    assert "카드를 1년 쓰는 값으로 1만원을 냅니다." in markdown
    assert "원문 유지 1건" in markdown
    assert result["summary"]["plain_blocks"] == 1
    assert result["summary"]["plain_rejected"] == 1
    assert any(f["verdict"] == "원문 대체" and "dom-1" in f["target"] for f in result["findings"])


def test_a_duty_and_its_f_twin_with_the_same_verdict_are_one_finding():
    """감사 P1-7: 데모의 원문 부적합 19건은 실제 11개 주제였습니다."""
    duty = {
        "items": [],
        "original": [
            {"code": "설명07", "verdict": "부적합", "reason": "연체 불이익 없음", "quote": ""},
            {"code": "F07", "verdict": "부적합", "reason": "연체 이자율 없음", "quote": ""},
            {"code": "F20", "verdict": "부적합", "reason": "강조 없음", "quote": ""},
            {"code": "설명11", "verdict": "판정 불가", "reason": "-", "quote": ""},
            {"code": "F11", "verdict": "부적합", "reason": "-", "quote": ""},
        ],
        "plain": [],
        "fidelity": [],
    }
    result = report(page={**PAGE, "html": "<p>연회비 1만원</p>", "status": "완료"}, duty=duty)
    codes = [f["code"] for f in result["findings"] if f["module"] == "explanation_duty_check"]
    assert codes.count("설명07/F07") == 1
    assert "설명07" not in codes and "F07" not in codes
    assert "F20" in codes
    assert "설명11" in codes and "F11" in codes  # different verdicts stay apart
    assert result["summary"]["duty_violations_original"] == 4
    assert result["summary"]["duty_topics_violated_original"] == 3


def test_the_report_names_the_reader():
    plain = {
        **PLAIN_OK,
        "units": [],
        "profile": {
            "id": "nemotron:abc",
            "version": "t1@ada0f5b",
            "status": "적용",
            "attributes": {"reader": "74세 남성, 초등학교, 하역 종사원"},
        },
        "selection": {
            "decided_by": "agent",
            "filters": {"age_min": 70},
            "match_count": 55912,
            "stop_reason": "chosen",
            "reason": "",
        },
    }
    markdown = report(plain=plain)["markdown"]
    assert "독자: 74세 남성" in markdown


def test_agent_links_report_their_search_and_stop():
    references = {
        "status": "완료",
        "method": {"linking": "agent", "searches": 3, "reads": 2, "cases_from": "db"},
        "stop_reason": "finished",
        "candidates": [{"case_id": "case.x"}],
        "links": [],
    }
    runs = report(references=references)["summary"]["agent_runs"]
    assert runs["case_link"]["stop_reason"] == "finished"


# Audit 2026-09-29 R2: which agent loops actually ran in this request, and how far.
AGENT_PAGE = {
    **PAGE,
    "status": "완료",
    "stop_reason": "full_coverage",
    "html": "<p>x</p>",
    "agent_trace": [
        {"turn": 1, "tool": "inspect_page"},
        {"turn": 2, "tool": "interact"},
        {"turn": 2, "tool": "probe_selector"},
        {"turn": 3, "tool": "submit_rule"},
    ],
}
AGENT_SELECTION = {
    **PLAIN_OK,
    "selection": {
        "decided_by": "agent",
        "stop_reason": "chosen",
        "trace": [
            {"turn": 1, "tool": "list_values"},
            {"turn": 1, "tool": "list_values"},
            {"turn": 2, "tool": "choose"},
        ],
    },
}
AGENT_REFERENCES = {
    "status": "부분 완료",
    "method": {"linking": "agent"},
    "stop_reason": "max_turns",
    "agent_trace": [{"turn": t, "tool": "search_cases"} for t in range(1, 9)],
    "links": [],
}


def test_each_agent_loop_that_ran_is_summarized_with_turns_and_stop():
    runs = report(page=AGENT_PAGE, plain=AGENT_SELECTION, references=AGENT_REFERENCES)["summary"][
        "agent_runs"
    ]
    assert runs["discovery"] == {
        "ran": "agent",
        "turns": 3,
        "tool_calls": 4,
        "stop_reason": "full_coverage",
    }
    assert runs["case_link"] == {
        "ran": "agent",
        "turns": 8,
        "tool_calls": 8,
        "stop_reason": "max_turns",
    }
    assert runs["reader_selection"] == {
        "ran": "agent",
        "turns": 2,
        "tool_calls": 3,
        "stop_reason": "chosen",
    }


def test_loops_that_did_not_run_say_so():
    page = {**PAGE, "status": "완료", "stop_reason": "rule_reused", "html": "<p>x</p>"}
    plain = {**PLAIN_OK, "selection": {"decided_by": "default", "trace": []}}
    references = {"status": "건너뜀", "method": {"linking": "agent"}, "links": []}
    runs = report(page=page, plain=plain, references=references)["summary"]["agent_runs"]
    assert runs["discovery"]["ran"] == "reuse"
    assert runs["case_link"]["ran"] == "skipped"
    assert runs["reader_selection"]["ran"] == "default"
    assert all(run["turns"] == 0 for run in runs.values())
    assert report()["summary"]["agent_runs"]["case_link"]["ran"] == "not_run"


DRAFT = {
    "status": "완료",
    "profile": {"attributes": {"reader": "93세 어르신"}},
    "units": [
        {"unit_id": "u1", "source_ids": ["dom-1"], "status": "accepted"},
        {"unit_id": "u2", "source_ids": ["dom-3"], "status": "reverted"},
    ],
    "html": (
        '<p data-source-id="dom-0">연회비</p>'
        '<section data-unit-id="u1" data-source-ids="dom-1">'
        '<p data-role="exact-fact"><strong>연회비 1만원</strong></p>'
        '<p data-role="explanation">1년에 &#x27;1만원&#x27;을 냅니다.</p>'
        '<p data-role="analogy">회비와 비슷합니다.</p></section>'
        '<p data-source-id="dom-2">국내전용</p><p data-source-id="dom-3">해외겸용</p>'
    ),
}
LABELS = {
    "E02": {"question": "의무표시사항은 9포인트 이상인가?", "basis": "여신협회 광고규정 제5조"},
    "설명01": {"question": "금리가 설명되어 있는가?", "basis": "금소법 제19조제1항"},
    "설명02": {"question": "상환금액이 설명되어 있는가?", "basis": "금소법 제19조제1항 외 1"},
    "F02": {"question": "F02 질문은 쓰이지 않아야 합니다?", "basis": "-"},
}


def _duty_row(code: str, verdict: str, reason: str) -> dict:
    return {"code": code, "condition_status": "", "verdict": verdict, "quote": "", "reason": reason}


def test_the_draft_shows_each_explained_line_and_leaves_out_unchanged_ones():
    markdown = report(plain=DRAFT)["markdown"]
    draft = markdown[markdown.index("## 3.") : markdown.index("## 4.")]
    assert "독자: 93세 어르신" in draft
    assert "원문 유지 1건" in draft
    assert (
        "- **원문** 연회비 1만원 → **쉬운말** 1년에 '1만원'을 냅니다. (비유: 회비와 비슷합니다.)"
        in draft
    )
    assert "국내전용" not in draft, "그대로 둔 원문 줄은 싣지 않음"


def test_display_rows_read_as_the_rubric_question_with_its_basis():
    markdown = report(labels=LABELS)["markdown"]
    assert "| 의무표시사항은 9포인트 이상인가? | 여신협회 광고규정 제5조 | 적합 |" in markdown
    assert "| E02 |" not in markdown
    assert "| E02 | - | 적합 |" in report()["markdown"], "라벨이 없으면 코드가 대신합니다"


def test_duty_lists_only_open_topics_once_with_question_and_basis():
    duty = {
        **DUTY_OK,
        "original": [
            _duty_row("설명01", "적합", "표기됨"),
            _duty_row("설명02", "부적합", "applies_condition 없음(해당없음). 상환금액 없음"),
            _duty_row("F02", "부적합", "상환금액 없음"),
        ],
        "plain": [
            _duty_row("설명01", "적합", "유지됨"),
            _duty_row("설명02", "판정 불가", "할부 개월 수가 존재(성립). 근거 부족"),
            _duty_row("F02", "판정 불가", "근거 부족"),
        ],
    }
    markdown = report(duty=duty, labels=LABELS)["markdown"]
    original = markdown[markdown.index("## 2.") : markdown.index("## 3.")]
    plain = markdown[markdown.index("## 4.") :]
    assert "적합 1건, 확인 필요 1건" in original
    row = "| 상환금액이 설명되어 있는가? | 금소법 제19조제1항 외 1 | 부적합 | 상환금액 없음 |"
    assert row in original
    assert "금리가 설명되어 있는가?" not in original, "적합 항목은 건수로만"
    assert "F02 질문" not in markdown, "F 쌍둥이는 설명 코드 하나로 묶임"
    assert "| 판정 불가 | 근거 부족 |" in plain


def test_a_meaning_change_is_listed_but_an_informational_one_is_not():
    duty = {
        **DUTY_OK,
        "fidelity": [
            {"code": "설명05", "kind": "변경", "reason": "반환 시한이 바뀜"},
            {"code": "설명09", "kind": "판정 불가", "reason": "인용 없음", "informational": True},
        ],
    }
    markdown = report(duty=duty)["markdown"]
    assert "- 변경: 반환 시한이 바뀜" in markdown
    assert "인용 없음" not in markdown
