"""generate_persona_explanation with the model faked: a summary paragraph and an advice paragraph
on the explanation-duty items to check elsewhere, held back when either fails its checks."""

import copy

import yaml
from bs4 import BeautifulSoup

from financial_disclosure_review.domain.persona_explanation.generate import (
    CONTROLS,
    MAX_CHARS,
    generate_persona_explanation,
)
from financial_disclosure_review.domain.persona_explanation.profiles import resolve_profile
from financial_disclosure_review.domain.persona_explanation.prompts import PERSONA_TASK
from tests.domain.persona_explanation.persona_fixtures import (
    CLASSIFICATION,
    LOWFIN,
    PROFILES,
    fake_ctx,
    load_persona_fixture,
    scripted_ask,
)

SUMMARY = (
    "스타벅스에서 쓰면 할인을 받을 수 있어요. 전월 이용금액 30만원 이상이면 월 최대 2만원까지"
    " 할인돼요. 일부 가맹점은 할인에서 빠져요."
)
ADVICE = (
    "계약 전에 상품설명서에서 청약을 철회할 수 있는 기한과 방법, 그리고 연회비를 돌려받는 조건을"
    " 꼭 확인해 보세요. 카드를 처음 만드시는 분께 특히 중요합니다."
)
CODES = ["설명16", "설명11"]


def draft(summary: str = SUMMARY, advice: str = ADVICE, codes: list[str] | None = None) -> dict:
    return {"summary": summary, "advice": advice, "advice_codes": CODES if codes is None else codes}


def run(*answers: dict, profile_id: str = LOWFIN, **kwargs):
    fixture = load_persona_fixture("threshold_exclusion")
    fake = scripted_ask(*answers)
    result = generate_persona_explanation(
        fixture["sources"],
        fixture["cards"],
        CLASSIFICATION,
        fake_ctx(),
        ask=fake,
        profile_id=profile_id,
        profiles_path=PROFILES,
        **kwargs,
    )
    return result, fake


def test_the_result_has_the_state_shape_and_one_model_call():
    result, fake = run(draft())
    assert set(result) == {
        "status",
        "reason",
        "profile",
        "overview",
        "advice_codes",
        "problems",
        "html",
        "controls",
    }
    assert fake.calls == ["OverviewDraft"]
    assert result["status"] == "완료" and result["problems"] == []
    assert result["overview"] == [SUMMARY, ADVICE]
    assert result["advice_codes"] == CODES
    assert result["profile"]["id"] == LOWFIN and result["profile"]["status"] == "적용"
    assert result["controls"] == CONTROLS


def test_the_html_holds_the_summary_then_the_advice_and_not_the_page():
    result, _ = run(draft())
    section = BeautifulSoup(result["html"], "html.parser").find("section")
    assert section is not None and section["data-role"] == "overview"
    roles = [(p["data-role"], p.get_text()) for p in section.find_all("p")]
    assert roles == [("summary", SUMMARY), ("advice", ADVICE)]
    assert "data-source-id" not in result["html"]


def test_the_prompt_gets_the_disclosures_to_carry_and_the_explanation_items_to_advise_on():
    _, fake = run(draft())
    data = fake.data[0]
    assert set(data["profile"]) == {
        "reading_preference",
        "financial_familiarity",
        "likely_questions",
        "prohibited_assumptions",
        "analogy_policy",
    }
    assert [s["source_id"] for s in data["sources"]] == ["dom-2"]
    codes = [item["code"] for item in data["disclosure_items"]]
    assert "C01" in codes and "A11" in codes
    assert "C03" not in codes and "C06" not in codes
    explanation = {item["code"]: item for item in data["explanation_items"]}
    assert "설명16" in explanation and explanation["설명16"]["question"].endswith("?")
    # 신용카드에 걸리지 않거나 신청 화면 전용인 항목은 권고 대상이 아니다.
    assert "설명01" not in explanation and "설명19" not in explanation
    assert "previous_feedback" not in data


def test_advice_codes_must_come_from_the_checklist_and_number_two_to_five():
    for codes, marker in (
        (["설명01", "설명16"], "설명의무 항목에 없는 advice_codes: 설명01"),
        (["설명16"], "권고 항목 1개"),
        ([], "권고 항목 0개"),
    ):
        result, fake = run(draft(codes=codes))
        assert len(fake.calls) == 2, "코드 검사에 걸린 답은 한 번 다시 묻는다"
        assert result["status"] == "원문 대체" and result["html"] == ""
        assert any(marker in p for p in result["problems"]), result["problems"]


def test_an_empty_advice_paragraph_is_held_back():
    result, _ = run(draft(advice=""))
    assert any("권고 문단(advice)이 비어 있음" in p for p in result["problems"])


def test_an_invented_number_in_either_paragraph_is_asked_again_and_then_held_back():
    for answer in (
        draft(summary=SUMMARY + " 1년이면 24만원을 아껴요."),
        draft(advice=ADVICE + " 철회 기한은 24일입니다."),
    ):
        result, fake = run(answer)
        assert fake.calls == ["OverviewDraft", "OverviewDraft"]
        assert any("24" in p for p in fake.data[1]["previous_problems"])
        assert result["status"] == "원문 대체"
        assert any("원문에 없는 수치: 24" in p for p in result["problems"])


def test_a_retry_that_fixes_the_answer_is_used():
    result, fake = run(draft(summary=SUMMARY + " 24만원을 아껴요."), draft())
    assert len(fake.calls) == 2
    assert result["status"] == "완료" and result["overview"] == [SUMMARY, ADVICE]


def test_list_numbering_is_not_an_invented_number():
    """2026-09-29 C4: '1) … 2) …' 목록 번호는 사실이 아니므로 원문에 없는 수치로 보지 않습니다."""
    numbered = (
        "1) 전월 이용금액 30만원 이상이어야 해요. 2) 할인은 월 최대 2만원이에요."
        " (3) 일부 가맹점은 빠져요."
    )
    result, _ = run(draft(summary=numbered))
    assert result["status"] == "완료", result["problems"]


def test_too_long_is_held_back():
    result, _ = run(draft(summary="가" * MAX_CHARS))
    assert any(f"(최대 {MAX_CHARS}자)" in p for p in result["problems"])


def test_verdict_words_and_new_absolutes_are_held_back():
    cases = ((" 이 광고는 문제없습니다.", "판정 표현"), (" 누구나 받아요.", "단정·최상급"))
    for extra, marker in cases:
        result, _ = run(draft(summary=SUMMARY + extra))
        assert result["status"] == "원문 대체"
        assert any(marker in p for p in result["problems"]), result["problems"]


def test_an_empty_answer_is_held_back_not_raised():
    result, fake = run(draft(summary="", advice="", codes=[]))
    assert len(fake.calls) == 2
    assert result["status"] == "원문 대체"
    assert "요약 문단(summary)이 비어 있음" in result["problems"]


def test_text_is_escaped_in_the_html():
    result, _ = run(draft(summary="<b>스타벅스</b> 할인 & 혜택이 있어요."))
    assert "&lt;b&gt;스타벅스&lt;/b&gt; 할인 &amp; 혜택" in result["html"]


def test_an_invalid_profile_makes_no_call(tmp_path):
    fixture = load_persona_fixture("threshold_exclusion")
    raw = yaml.safe_load(PROFILES.read_text(encoding="utf-8"))
    for p in raw["profiles"]:
        p["version"] = 99
    bad = tmp_path / "persona_profiles.yaml"
    bad.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    fake = scripted_ask(draft())
    result = generate_persona_explanation(
        fixture["sources"],
        fixture["cards"],
        CLASSIFICATION,
        fake_ctx(),
        ask=fake,
        profile_id=LOWFIN,
        profiles_path=bad,
    )
    assert fake.calls == []
    assert result["status"] == "원문 대체"
    assert result["profile"]["status"] == "무효"
    assert "프로필 무효" in result["reason"]
    assert result["html"] == "" and result["overview"] == [] and result["advice_codes"] == []


def test_an_unknown_profile_id_from_the_context_is_invalid_too():
    fixture = load_persona_fixture("threshold_exclusion")
    fake = scripted_ask(draft())
    ctx = fake_ctx()
    ctx.persona_profile = "not-allowlisted"
    result = generate_persona_explanation(
        fixture["sources"], fixture["cards"], CLASSIFICATION, ctx, ask=fake, profiles_path=PROFILES
    )
    assert fake.calls == [] and result["profile"]["status"] == "무효"


def test_no_cards_or_no_sources_means_no_call():
    fixture = load_persona_fixture("threshold_exclusion")
    fake = scripted_ask(draft())
    result = generate_persona_explanation(
        fixture["sources"], [], CLASSIFICATION, fake_ctx(), ask=fake, profiles_path=PROFILES
    )
    assert result["status"] == "원문 대체"
    result = generate_persona_explanation(
        [], fixture["cards"], CLASSIFICATION, fake_ctx(), ask=fake, profiles_path=PROFILES
    )
    assert result["status"] == "판정 불가"
    assert fake.calls == []


def test_only_this_modules_feedback_reaches_the_prompt():
    feedback = [
        {
            "module": "persona_explanation",
            "code": "C01",
            "reason": "개요에서 연회비가 빠짐",
            "requested_change": "연회비를 원문 표기 그대로 담으세요",
        },
        {"module": "ad_disclosure_check", "reason": "다른 모듈", "requested_change": "x"},
    ]
    _, fake = run(draft(), feedback=feedback)
    assert fake.data[0]["previous_feedback"] == [
        {
            "code": "C01",
            "reason": "개요에서 연회비가 빠짐",
            "requested_change": "연회비를 원문 표기 그대로 담으세요",
        }
    ]


def test_a_given_profile_is_used_as_is_and_its_reader_reaches_the_prompt(tmp_path):
    fixture = load_persona_fixture("threshold_exclusion")
    profile = copy.deepcopy(resolve_profile(LOWFIN, PROFILES))
    profile["id"] = "nemotron:" + "0" * 32
    profile["attributes"]["reader"] = "74세 여자 · 학력 초등학교 · 직업 무직\n가상의 인물입니다."
    fake = scripted_ask(draft())
    result = generate_persona_explanation(
        fixture["sources"],
        fixture["cards"],
        CLASSIFICATION,
        fake_ctx(),
        ask=fake,
        profile_id="unknown-id-that-would-be-invalid",
        profiles_path=tmp_path / "missing.yaml",
        profile=profile,
    )
    assert result["profile"] is profile
    assert result["status"] == "완료"
    assert fake.data[0]["profile"]["reader"] == profile["attributes"]["reader"]


def test_an_invalid_given_profile_makes_no_call():
    profile = {
        **resolve_profile(LOWFIN, PROFILES),
        "status": "무효",
        "reason": "템플릿 버전 불일치",
    }
    result, fake = run(draft(), profile=profile)
    assert result["status"] == "원문 대체" and "템플릿 버전 불일치" in result["reason"]
    assert fake.calls == []


def test_the_task_asks_for_a_summary_and_reader_tailored_advice():
    assert "summary" in PERSONA_TASK and "advice" in PERSONA_TASK
    assert "explanation_items" in PERSONA_TASK and "likely_questions" in PERSONA_TASK
    assert "지어내지 않습니다" in PERSONA_TASK
    assert "자격" in PERSONA_TASK.split("reader", 1)[1]
