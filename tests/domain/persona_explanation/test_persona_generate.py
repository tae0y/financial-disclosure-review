"""generate_persona_explanation with the model faked: one paragraph of reader-tailored advice on the
explanation-duty items to check before signing, held back when it fails its checks."""

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

ADVICE = (
    "계약 전에 상품설명서나 상담에서 청약을 철회할 수 있는 기한과 방법, 그리고 연회비를 돌려받는"
    " 조건을 꼭 확인해 보세요. 카드를 처음 만드시는 분께는 마음이 바뀌었을 때 어떻게 되는지가 특히"
    " 중요합니다."
)
CODES = ["설명16", "설명11"]


def draft(advice: str = ADVICE, codes: list[str] | None = None) -> dict:
    return {"advice": advice, "advice_codes": CODES if codes is None else codes}


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
        "advice",
        "advice_codes",
        "problems",
        "html",
        "controls",
    }
    assert fake.calls == ["AdviceDraft"]
    assert result["status"] == "완료" and result["problems"] == []
    assert result["advice"] == ADVICE and result["advice_codes"] == CODES
    assert result["profile"]["id"] == LOWFIN and result["profile"]["status"] == "적용"
    assert result["controls"] == CONTROLS


def test_the_html_is_the_advice_alone_not_the_page():
    result, _ = run(draft())
    section = BeautifulSoup(result["html"], "html.parser").find("section")
    assert section is not None and section["data-role"] == "advice"
    assert [p.get_text() for p in section.find_all("p")] == [ADVICE]
    assert "data-source-id" not in result["html"]


def test_the_prompt_gets_every_page_line_and_the_checklist_to_advise_on():
    fixture = load_persona_fixture("threshold_exclusion")
    _, fake = run(draft())
    data = fake.data[0]
    assert set(data["profile"]) == {
        "reading_preference",
        "financial_familiarity",
        "likely_questions",
        "prohibited_assumptions",
        "analogy_policy",
    }
    # 페이지가 이미 설명한 것을 권하지 않도록, 카드가 인용한 줄만이 아니라 원문 줄 전체를 준다.
    assert [s["source_id"] for s in data["sources"]] == [s["source_id"] for s in fixture["sources"]]
    explanation = {item["code"]: item for item in data["explanation_items"]}
    assert "설명16" in explanation and explanation["설명16"]["question"].endswith("?")
    # 신용카드에 걸리지 않거나 신청 화면 전용인 항목은 권고 대상이 아니다.
    assert "설명01" not in explanation and "설명19" not in explanation
    assert "disclosure_items" not in data and "previous_feedback" not in data


def test_advice_codes_must_come_from_the_checklist_and_number_two_to_five():
    for codes, marker in (
        (["설명01", "설명16"], "설명의무 확인 목록에 없는 advice_codes: 설명01"),
        (["설명16"], "권고 항목 1개"),
        (["설명02", "설명04", "설명05", "설명06", "설명07", "설명08"], "권고 항목 6개"),
    ):
        result, fake = run(draft(codes=codes))
        assert len(fake.calls) == 2, "코드 검사에 걸린 답은 한 번 다시 묻는다"
        assert result["status"] == "원문 대체" and result["html"] == ""
        assert any(marker in p for p in result["problems"]), result["problems"]


def test_a_rubric_code_in_the_text_is_held_back():
    """2026-09-30 샘플: 모델이 본문에 '설명02' 같은 코드를 적었다. 독자에게는 뜻이 없다."""
    result, _ = run(draft(advice=ADVICE + " (설명16, 설명11)"))
    assert any("항목 코드" in p for p in result["problems"]), result["problems"]
    assert not any("원문에 없는 수치" in p for p in result["problems"])


def test_an_invented_term_is_asked_again_and_then_held_back():
    result, fake = run(draft(advice=ADVICE + " 철회 기한은 14일입니다."))
    assert fake.calls == ["AdviceDraft", "AdviceDraft"]
    assert any("14" in p for p in fake.data[1]["previous_problems"])
    assert result["status"] == "원문 대체"
    assert any("원문에 없는 수치: 14" in p for p in result["problems"])


def test_a_retry_that_fixes_the_answer_is_used():
    result, fake = run(draft(advice=ADVICE + " 14일 안에 하세요."), draft())
    assert len(fake.calls) == 2
    assert result["status"] == "완료" and result["advice"] == ADVICE


def test_list_numbering_is_not_an_invented_number():
    numbered = "계약 전에 꼭 확인해 보세요. 1) 청약 철회 방법 2) 연회비 반환 조건."
    result, _ = run(draft(advice=numbered))
    assert result["status"] == "완료", result["problems"]


def test_too_long_empty_verdict_and_absolute_are_held_back():
    for advice, marker in (
        ("가" * (MAX_CHARS + 1), f"(최대 {MAX_CHARS}자)"),
        ("", "권고 문단(advice)이 비어 있음"),
        (ADVICE + " 이 광고는 문제없습니다.", "판정 표현"),
        (ADVICE + " 누구나 받을 수 있어요.", "단정·최상급"),
    ):
        result, _ = run(draft(advice=advice))
        assert result["status"] == "원문 대체"
        assert any(marker in p for p in result["problems"]), result["problems"]


def test_text_is_escaped_in_the_html():
    result, _ = run(draft(advice="<b>청약 철회</b> 방법 & 연회비 반환을 확인해 보세요."))
    assert "&lt;b&gt;청약 철회&lt;/b&gt; 방법 &amp; 연회비" in result["html"]


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
    assert result["html"] == "" and result["advice"] == "" and result["advice_codes"] == []


def test_an_unknown_profile_id_from_the_context_is_invalid_too():
    fixture = load_persona_fixture("threshold_exclusion")
    fake = scripted_ask(draft())
    ctx = fake_ctx()
    ctx.persona_profile = "not-allowlisted"
    result = generate_persona_explanation(
        fixture["sources"], fixture["cards"], CLASSIFICATION, ctx, ask=fake, profiles_path=PROFILES
    )
    assert fake.calls == [] and result["profile"]["status"] == "무효"


def test_no_sources_means_no_call():
    fixture = load_persona_fixture("threshold_exclusion")
    fake = scripted_ask(draft())
    result = generate_persona_explanation(
        [], fixture["cards"], CLASSIFICATION, fake_ctx(), ask=fake, profiles_path=PROFILES
    )
    assert result["status"] == "판정 불가"
    assert fake.calls == []


def test_only_this_modules_feedback_reaches_the_prompt():
    feedback = [
        {
            "module": "persona_explanation",
            "code": "",
            "reason": "원문에 없는 수치",
            "requested_change": "수치를 빼고 무엇을 확인할지만 쓰세요",
        },
        {"module": "ad_disclosure_check", "reason": "다른 모듈", "requested_change": "x"},
    ]
    _, fake = run(draft(), feedback=feedback)
    assert fake.data[0]["previous_feedback"] == [
        {
            "code": "",
            "reason": "원문에 없는 수치",
            "requested_change": "수치를 빼고 무엇을 확인할지만 쓰세요",
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


def test_the_task_asks_for_reader_tailored_advice_and_never_the_answers():
    assert "advice" in PERSONA_TASK and "advice_codes" in PERSONA_TASK
    assert "explanation_items" in PERSONA_TASK and "likely_questions" in PERSONA_TASK
    assert "그 답(기간, 금액, 조건, 비율)은 쓰지 않습니다" in PERSONA_TASK
    assert "code(예: 설명16)는 본문에 쓰지 않습니다" in PERSONA_TASK
    assert "자격" in PERSONA_TASK.split("reader", 1)[1]
