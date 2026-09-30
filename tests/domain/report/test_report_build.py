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
OVERVIEW_OK = {
    "status": "완료",
    "overview": ["1년에 1만원을 냅니다."],
    "problems": [],
    "html": '<section data-role="overview"><p>1년에 1만원을 냅니다.</p></section>',
}
DISCLOSURE_OK = {
    "items": [{"code": "C01", "applied": True, "condition_status": "성립", "reason": ""}],
    "original": [
        {
            "code": "C01",
            "condition_status": "성립",
            "verdict": "적합",
            "quote": "연회비 1만원",
            "reason": "표기됨",
        }
    ],
    "overview": [
        {
            "code": "C01",
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
        "overview": OVERVIEW_OK,
        "disclosure": DISCLOSURE_OK,
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
    assert result["summary"]["overview_paragraphs"] == 1
    assert result["summary"]["overview_withheld"] is False


def test_the_markdown_carries_the_frontmatter_and_every_section():
    markdown = report()["markdown"]
    assert markdown.startswith("---\nai-generated: true\nhuman-review: false\n---")
    headings = ["## 확인할 항목", "## 쉬운말 개요"]
    positions = [markdown.index(heading) for heading in headings]
    assert positions == sorted(positions)
    assert markdown.index(PAGE["url"]) < positions[0], "원문 정보가 먼저"
    assert "적합: 표시방법 1/1 · 광고 의무표시 1/1 · 쉬운말 개요 1/1" in markdown
    assert "확인할 항목이 없습니다." in markdown
    assert "1년에 1만원을 냅니다." in markdown, "쉬운말 결과가 보고서에 실려야 함"


def test_the_actions_are_grouped_by_target_rather_than_one_line_per_item():
    """항목이 수십 개일 때 조치 목록이 수십 줄이 되지 않아야 합니다."""
    duty = {
        **DISCLOSURE_OK,
        "original": [
            {
                "code": f"A{n:02d}",
                "condition_status": "성립",
                "verdict": "부적합",
                "quote": "연회비 1만원",
                "reason": "누락",
            }
            for n in range(1, 16)
        ],
    }
    result = report(disclosure=duty)
    assert len(result["findings"]) == 15
    grouped = [a for a in result["actions"] if a.startswith("원문 위반")]
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
        **DISCLOSURE_OK,
        "original": [
            {
                "code": "C01",
                "condition_status": "성립",
                "verdict": "부적합",
                "quote": "연회비 1만원",
                "reason": "중도해지 손실 문구 없음",
            }
        ],
    }
    result = report(disclosure=duty)
    assert result["status"] == "사람 검토 필요"
    assert result["decision"] == "쉬운말 개요 자동 게시 불가 — 원문만 게시"
    assert result["summary"]["disclosure_violations_original"] == 1


def test_a_fidelity_difference_is_reported_as_a_finding():
    duty = {
        **DISCLOSURE_OK,
        "fidelity": [{"code": "C01", "source_id": "b0", "kind": "누락", "reason": "조건 빠짐"}],
    }
    result = report(disclosure=duty)
    assert result["summary"]["fidelity_diffs"] == 1
    assert any(row["module"] == "ad_disclosure_check" for row in result["findings"])


def test_a_failed_verification_escalates_with_the_stop_reason():
    failed = {
        "passed": False,
        "reasons": ["수치 근거 없음"],
        "failed_modules": ["persona_explanation"],
        "feedback": [],
        "loop_count": 2,
    }
    result = report(
        verification=failed,
        stop={"reason": "재시도 한도 초과", "detail": "2회 모두 미달", "max_loops": 2},
    )
    assert result["status"] == "사람 검토 필요"
    assert result["decision"] == "쉬운말 개요 자동 게시 불가 — 원문만 게시"
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
        overview={},
        disclosure={},
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
        PAGE, CLASSIFICATION, DISPLAY_OK, OVERVIEW_OK, DISCLOSURE_OK, PASSED, {"max_loops": 2}
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
        **DISCLOSURE_OK,
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


def test_a_mandatory_ad_disclosure_binds_an_ad_page_directly_so_its_failure_is_a_violation():
    # 광고 의무표시(금소법 제22조, 협회 광고규정)는 광고 페이지에 직접 걸리는 의무다.
    result = report(disclosure=duty_with("C01"), bindings={"C01": "법령"})
    row = next(f for f in result["findings"] if f["code"] == "C01")
    assert (row["severity"], row["basis"]) == ("위반", "법령")


def test_explanation_duty_items_are_listed_for_the_product_documents_not_judged():
    disclosure = {
        **DISCLOSURE_OK,
        "deferred": [
            {"code": "설명11", "question": "연회비 반환이 설명되어 있는가?"},
            {"code": "설명16", "question": "청약 철회의 기한·행사방법·효과가 설명되어 있는가?"},
        ],
    }
    result = report(disclosure=disclosure)
    assert result["status"] == "검토 완료"
    assert not any(f["code"].startswith("설명") for f in result["findings"])
    assert any("상품설명서에서 확인: 설명11, 설명16" in a for a in result["actions"])
    assert result["summary"]["deferred_explanation_items"] == 2
    assert "## 상품설명서에서 확인할 설명의무 (2개)" in result["markdown"]
    assert "연회비 반환 · 청약 철회의 기한·행사방법·효과" in result["markdown"]


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
        OVERVIEW_OK,
        DISCLOSURE_OK,
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
        overview={},
        disclosure={},
        verification={},
    )
    assert result["status"] == "수집 실패"
    assert any("fetch_error" in action and "HTTP 503" in action for action in result["actions"])
    assert "상품 유형을 확정하지 못해" not in result["markdown"]
    assert "사유: 페이지 수집 수집 실패(fetch_error) — HTTP 503" in result["markdown"]


def test_no_accepted_rule_reads_as_an_insufficient_investigation():
    page = {**FAILED_PAGE, "status": "조사 불충분", "stop_reason": "max_turns", "error": ""}
    empty: dict = {}
    result = report(
        page=page,
        classification=empty,
        display=empty,
        overview=empty,
        disclosure=empty,
        verification=empty,
    )
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


def test_cards_are_counted_but_never_change_the_verdict():
    result = report(cards=CARDS)
    assert result["summary"]["evidence_cards"] == 1
    assert result["status"] == "검토 완료"


def test_a_pass_that_rests_only_on_hidden_text_is_named_as_a_limit():
    """원문 적합의 인용이 화면에 보이지 않은 문장에만 있으면, 사람이 노출 여부를 확인해야 합니다."""
    result = report(cards=CARDS)
    assert any("C01" in limit and "보이지 않았거나" in limit for limit in result["limits"])


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
    "overview": ["카드를 1년 쓰는 값으로 1만원을 냅니다."],
    "problems": [],
    "html": '<section data-role="overview"><p>카드를 1년 쓰는 값으로 1만원을 냅니다.</p></section>',
    "controls": {"ui": ["AI 생성 고지"], "governance": ["사람 승인"]},
}


def test_the_overview_is_reported_as_its_paragraphs():
    result = report(overview=PERSONA)
    assert "카드를 1년 쓰는 값으로 1만원을 냅니다." in result["markdown"]
    assert result["summary"]["overview_paragraphs"] == 1
    assert not any(f["verdict"] == "원문 대체" for f in result["findings"])


def test_an_overview_held_back_by_its_checks_is_a_finding_and_a_limit():
    held = {**PERSONA, "status": "원문 대체", "html": "", "problems": ["원문에 없는 수치: 3"]}
    result = report(overview=held)
    assert result["summary"]["overview_withheld"] is True
    assert result["summary"]["overview_paragraphs"] == 0
    assert any(f["verdict"] == "원문 대체" and "3" in f["reason"] for f in result["findings"])
    assert "(싣지 않음: 원문에 없는 수치: 3)" in result["markdown"]
    assert any("싣지 않았습니다" in limit for limit in result["limits"])


def test_the_report_names_the_reader_by_age_band_and_familiarity_only():
    """데이터셋 페르소나의 이름·인물 묘사는 가상 인물이라 요청자에게 보여 주지 않는다."""
    plain = {
        **OVERVIEW_OK,
        "profile": {
            "id": "nemotron:abc",
            "version": "t1@ada0f5b",
            "status": "적용",
            "attributes": {
                "reader": "74세 남자 · 학력 고등학교 · 직업 무직\n임경호 씨는 바둑을 즐긴다.",
                "financial_familiarity": "낮음",
            },
        },
        "selection": {
            "decided_by": "agent",
            "filters": {"age_min": 70},
            "match_count": 55912,
            "stop_reason": "chosen",
            "reason": "",
        },
    }
    markdown = report(overview=plain)["markdown"]
    assert "독자: 70대 · 금융 익숙도 낮음" in markdown
    assert "임경호" not in markdown and "고등학교" not in markdown


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
    **OVERVIEW_OK,
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


def test_each_agent_loop_that_ran_is_summarized_with_turns_and_stop():
    runs = report(page=AGENT_PAGE, overview=AGENT_SELECTION)["summary"]["agent_runs"]
    assert runs["discovery"] == {
        "ran": "agent",
        "turns": 3,
        "tool_calls": 4,
        "stop_reason": "full_coverage",
    }
    assert runs["reader_selection"] == {
        "ran": "agent",
        "turns": 2,
        "tool_calls": 3,
        "stop_reason": "chosen",
    }


def test_loops_that_did_not_run_say_so():
    page = {**PAGE, "status": "완료", "stop_reason": "rule_reused", "html": "<p>x</p>"}
    plain = {**OVERVIEW_OK, "selection": {"decided_by": "default", "trace": []}}
    runs = report(page=page, overview=plain)["summary"]["agent_runs"]
    assert runs["discovery"]["ran"] == "reuse"
    assert runs["reader_selection"]["ran"] == "default"
    assert all(run["turns"] == 0 for run in runs.values())
    assert set(report()["summary"]["agent_runs"]) == {"discovery", "reader_selection"}


DRAFT = {
    **PERSONA,
    "profile": {"attributes": {"reader": "93세 여자 · 학력 초등학교"}},
    "overview": ["연회비는 1년에 '1만원'이에요.", "늦게 내면 이자가 더 붙어요."],
    "html": "<section><p>연회비는 1년에 &#x27;1만원&#x27;이에요.</p><p>늦게 내면</p></section>",
}
LABELS = {
    "E02": {"question": "의무표시사항은 9포인트 이상인가?", "basis": "여신협회 광고규정 제5조"},
    "C01": {"question": "연회비가 표시되어 있는가?", "basis": "여신협회 광고규정 제4조"},
    "C02": {"question": "연체이자율이 표시되어 있는가?", "basis": "금소법 제22조 외 1"},
}


def _duty_row(code: str, verdict: str, reason: str) -> dict:
    return {"code": code, "condition_status": "", "verdict": verdict, "quote": "", "reason": reason}


def test_the_overview_section_shows_the_reader_and_each_paragraph():
    markdown = report(overview=DRAFT)["markdown"]
    section = markdown[markdown.index("## 쉬운말 개요") :]
    assert "독자: 90대" in section
    assert "연회비는 1년에 '1만원'이에요." in section
    assert "늦게 내면 이자가 더 붙어요." in section


def test_open_rows_read_as_the_rubric_question_with_a_short_basis():
    display = {**DISPLAY_OK, "items": [{**DISPLAY_OK["items"][0], "verdict": "부적합"}]}
    labels = {
        **LABELS,
        "E02": {
            "question": "의무표시사항은 9포인트 이상인가?",
            "basis": "여신협회 광고규정 제5조; 금소법 제22조; 세부지침 제3조",
        },
    }
    markdown = report(display=display, labels=labels)["markdown"]
    assert (
        "| 표시방법 | 의무표시사항은 9포인트 이상인가? | 여신협회 광고규정 제5조 외 2 | 부적합 |"
        in markdown
    )
    assert "| 표시방법 | E02 | - | 부적합 |" in report(display=display)["markdown"], (
        "라벨이 없으면 코드가 대신합니다"
    )


def test_disclosures_list_only_open_items_with_question_and_basis():
    disclosure = {
        **DISCLOSURE_OK,
        "original": [
            _duty_row("C01", "적합", "표기됨"),
            _duty_row("C02", "부적합", "applies_condition 없음(해당없음). 연체이자율 없음"),
        ],
        "overview": [
            _duty_row("C01", "적합", "유지됨"),
            _duty_row("C02", "판정 불가", "근거 부족"),
        ],
    }
    markdown = report(disclosure=disclosure, labels=LABELS)["markdown"]
    checks = markdown[markdown.index("## 확인할 항목") : markdown.index("## 쉬운말 개요")]
    overview = markdown[markdown.index("## 쉬운말 개요") :]
    assert "광고 의무표시 1/2" in checks
    row = (
        "| 의무표시 | 연체이자율이 표시되어 있는가? | 금소법 제22조 외 1 | 부적합"
        " | 연체이자율 없음 |"
    )
    assert row in checks
    assert "연회비가 표시되어 있는가?" not in checks, "적합 항목은 건수로만"
    assert "- 연체이자율이 표시되어 있는가? — 판정 불가: 근거 부족" in overview


def test_a_meaning_change_is_listed_but_an_informational_one_is_not():
    duty = {
        **DISCLOSURE_OK,
        "fidelity": [
            {"code": "A05", "kind": "변경", "reason": "수수료 조건이 바뀜"},
            {"code": "A04", "kind": "판정 불가", "reason": "인용 없음", "informational": True},
        ],
    }
    markdown = report(disclosure=duty)["markdown"]
    assert "- 변경 (A05): 수수료 조건이 바뀜" in markdown
    assert "인용 없음" not in markdown
