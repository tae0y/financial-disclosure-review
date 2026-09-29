"""generate_persona_explanation with the model faked: code keeps only traceable units."""

import copy

import yaml
from bs4 import BeautifulSoup

from financial_disclosure_review.core.text import visible_text
from financial_disclosure_review.domain.persona_explanation.generate import (
    CONTROLS,
    generate_persona_explanation,
)
from financial_disclosure_review.domain.persona_explanation.profiles import resolve_profile
from financial_disclosure_review.domain.persona_explanation.prompts import PERSONA_TASK
from tests.domain.persona_explanation.persona_fixtures import (
    CLASSIFICATION,
    FIRSTCARD,
    LOANFAMILIAR,
    LOWFIN,
    PROFILES,
    fake_ctx,
    load_persona_fixture,
    scripted_ask,
    top_level_ids,
)


def run(fixture: dict, drafts: list[dict], profile_id: str = LOWFIN, **kwargs):
    fake = scripted_ask({"items": drafts})
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


def _originals(fixture: dict) -> list[str]:
    return [s["source_id"] for s in fixture["sources"]]


def test_the_result_has_the_state_shape_and_one_model_call():
    fixture = load_persona_fixture("threshold_exclusion")
    result, fake = run(fixture, fixture["drafts"]["lowfin"])
    assert set(result) == {
        "status",
        "reason",
        "profile",
        "fact_ledger",
        "units",
        "html",
        "controls",
    }
    assert fake.calls == ["PersonaUnitDrafts"]
    assert result["status"] == "완료"
    assert result["profile"]["id"] == LOWFIN and result["profile"]["status"] == "적용"
    assert result["controls"] == CONTROLS
    unit = result["units"][0]
    assert unit["status"] == "accepted" and unit["problems"] == []
    # A benefit card, a benefit_only reader and no risk words: the analogy survives.
    assert unit["analogy"]


def test_the_prompt_gets_derived_profile_attributes_cards_and_the_ledger_only():
    fixture = load_persona_fixture("threshold_exclusion")
    _, fake = run(fixture, fixture["drafts"]["lowfin"])
    data = fake.data[0]
    assert set(data["profile"]) == {
        "reading_preference",
        "financial_familiarity",
        "likely_questions",
        "prohibited_assumptions",
        "analogy_policy",
    }
    assert [s["source_id"] for s in data["sources"]] == ["dom-2"]
    assert [f["value"] for f in data["fact_ledger"]] == [
        "30만원",
        "2만원",
        "전월 이용금액 30만원 이상",
        "일부 가맹점 제외",
    ]
    assert "previous_feedback" not in data


def test_revolving_units_are_kept_but_every_analogy_is_dropped():
    fixture = load_persona_fixture("revolving")
    result, _ = run(fixture, fixture["drafts"])
    assert [u["status"] for u in result["units"]] == ["accepted"] * 3
    rate_unit = result["units"][1]
    assert rate_unit["analogy"] == ""
    assert any(p.startswith("analogy_dropped") for p in rate_unit["problems"])
    assert 'data-role="analogy"' not in result["html"]
    assert top_level_ids(result["html"]) == ["dom-1", "unit:u1", "unit:u2", "unit:u3"]


def test_annual_fee_and_refund_keep_every_amount_period_and_exclusion():
    fixture = load_persona_fixture("annual_fee_refund")
    result, _ = run(fixture, fixture["drafts"], profile_id=FIRSTCARD)
    assert result["status"] == "완료"
    assert [u["status"] for u in result["units"]] == ["accepted"] * 3
    # The fee card is a risk concept: its analogy goes, the unit stays.
    assert result["units"][0]["analogy"] == ""
    text = visible_text(result["html"])
    for fact in result["fact_ledger"]:
        assert "".join(fact["value"].split()) in "".join(text.split())


def test_a_threshold_benefit_that_drops_its_exclusion_is_reverted():
    fixture = load_persona_fixture("threshold_exclusion")
    result, _ = run(fixture, fixture["drafts"]["dropped_exception"])
    unit = result["units"][0]
    assert unit["status"] == "reverted"
    assert any("사실 원장 값 누락: f4" in p for p in unit["problems"])
    assert result["status"] == "원문 대체"
    assert top_level_ids(result["html"]) == _originals(fixture)


def test_rate_and_penalty_analogies_are_dropped_for_every_reader():
    fixture = load_persona_fixture("rate_penalty")
    for profile_id, reason in ((LOWFIN, "위험 개념 카드"), (LOANFAMILIAR, "none")):
        result, _ = run(fixture, fixture["drafts"], profile_id=profile_id)
        assert [u["status"] for u in result["units"]] == ["accepted", "accepted"]
        for unit in result["units"]:
            assert unit["analogy"] == ""
            assert any(reason in p for p in unit["problems"] if p.startswith("analogy_dropped"))


def test_list_numbering_is_not_an_invented_number():
    """2026-09-29 C4: 금융 친숙 독자에게 모델이 '1) … 2) …' 목록으로 쓰자 번호가 원문에 없는 수치로
    잡혀 단위가 모두 원문으로 되돌아갔습니다. 목록 번호는 사실이 아닙니다."""
    fixture = load_persona_fixture("threshold_exclusion")
    draft = copy.deepcopy(fixture["drafts"]["lowfin"])
    draft[0]["explanation"] = (
        "1) 전월 이용금액이 30만원 이상이어야 합니다. 2) 할인은 월 최대 2만원입니다."
        " (3) 일부 가맹점 제외 조건이 있습니다."
    )
    draft[0]["analogy"] = ""
    result, _ = run(fixture, draft)
    assert result["units"][0]["status"] == "accepted", result["units"][0]["problems"]
    draft[0]["explanation"] += " 1년이면 24만원입니다."
    result, _ = run(fixture, draft)
    assert any("근거 원문에 없는 수치: 24" in p for p in result["units"][0]["problems"])


def test_an_invented_number_reverts_the_unit_to_the_original_line():
    fixture = load_persona_fixture("threshold_exclusion")
    result, _ = run(fixture, fixture["drafts"]["invented_number"])
    unit = result["units"][0]
    assert unit["status"] == "reverted"
    assert any("근거 원문에 없는 수치: 24" in p for p in unit["problems"])
    soup = BeautifulSoup(result["html"], "html.parser")
    assert soup.find("section") is None
    line = soup.find("p", attrs={"data-source-id": "dom-2"})
    assert line is not None and line.get_text() == fixture["sources"][1]["text"]
    assert "24" not in result["html"]


def test_an_invalid_profile_makes_no_call_and_keeps_the_original(tmp_path):
    fixture = load_persona_fixture("threshold_exclusion")
    raw = yaml.safe_load(PROFILES.read_text(encoding="utf-8"))
    for p in raw["profiles"]:
        p["version"] = 99
    bad = tmp_path / "persona_profiles.yaml"
    bad.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    fake = scripted_ask({"items": fixture["drafts"]["lowfin"]})
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
    assert result["units"] == []
    assert top_level_ids(result["html"]) == _originals(fixture)
    assert len(result["fact_ledger"]) == 4


def test_an_unknown_profile_id_from_the_context_is_invalid_too():
    fixture = load_persona_fixture("threshold_exclusion")
    fake = scripted_ask({"items": fixture["drafts"]["lowfin"]})
    ctx = fake_ctx()
    ctx.persona_profile = "not-allowlisted"
    result = generate_persona_explanation(
        fixture["sources"], fixture["cards"], CLASSIFICATION, ctx, ask=fake, profiles_path=PROFILES
    )
    assert fake.calls == [] and result["profile"]["status"] == "무효"


def test_no_cards_means_no_call_and_the_original_text():
    fixture = load_persona_fixture("threshold_exclusion")
    fake = scripted_ask({"items": []})
    result = generate_persona_explanation(
        fixture["sources"], [], CLASSIFICATION, fake_ctx(), ask=fake, profiles_path=PROFILES
    )
    assert fake.calls == []
    assert result["status"] == "원문 대체"
    assert top_level_ids(result["html"]) == _originals(fixture)


def test_the_html_keeps_every_source_in_page_order_and_replaces_only_a_units_first_line():
    fixture = load_persona_fixture("revolving")
    joint = {
        "card_ids": ["r2", "r1"],
        "source_ids": ["dom-3", "dom-2"],
        "exact_fact": fixture["sources"][1]["text"],
        "explanation": (
            "10%만 내면 남은 돈이 다음 달로 넘어가고, 이월된 금액에는 연 5.9%에서 19.9% 사이 "
            "수수료율이 붙습니다. 결제하실 금액의 10%만 결제하면 이렇게 됩니다."
        ),
        "analogy": "",
        "persona_question_answered": "모르고 지나치면 손해 보는 조건이 있나요?",
    }
    result, _ = run(fixture, [joint])
    unit = result["units"][0]
    assert unit["status"] == "accepted", unit["problems"]
    assert unit["replaces"] == "dom-2"
    assert top_level_ids(result["html"]) == ["dom-1", "unit:u1", "dom-3", "dom-4"]
    section = BeautifulSoup(result["html"], "html.parser").find("section")
    assert section is not None
    assert section["data-source-ids"] == "dom-3 dom-2"
    roles = [p["data-role"] for p in section.find_all("p")]
    assert roles == ["exact-fact", "explanation"]


def test_text_is_escaped_in_the_html():
    fixture = load_persona_fixture("threshold_exclusion")
    fixture = copy.deepcopy(fixture)
    fixture["sources"][0]["text"] = "<b>스타벅스</b> 할인 & 혜택"
    result, _ = run(fixture, fixture["drafts"]["lowfin"])
    assert "&lt;b&gt;스타벅스&lt;/b&gt; 할인 &amp; 혜택" in result["html"]


def test_a_second_unit_for_the_same_line_is_reverted():
    fixture = load_persona_fixture("threshold_exclusion")
    drafts = fixture["drafts"]["lowfin"] + fixture["drafts"]["firstcard"]
    result, _ = run(fixture, drafts)
    assert [u["status"] for u in result["units"]] == ["accepted", "reverted"]
    assert "이미 설명함" in result["units"][1]["problems"][0]
    assert result["fact_ledger"][0]["unit_ids"] == ["u1", "u2"]


def test_unknown_cards_foreign_sources_verdicts_and_absolutes_are_reverted():
    fixture = load_persona_fixture("revolving")
    good = fixture["drafts"]
    bad_card = {**good[0], "card_ids": ["zz"]}
    foreign_source = {**good[2], "source_ids": ["dom-4", "dom-1"]}
    verdict = {**good[2], "explanation": good[2]["explanation"] + " 이 표시는 문제없습니다."}
    absolute = {**good[0], "explanation": good[0]["explanation"] + " 누구나 이용할 수 있습니다."}
    for draft, marker in (
        (bad_card, "알 수 없는 card_id"),
        (foreign_source, "인용 카드의 출처가 아닌 source_id"),
        (verdict, "판정 표현"),
        (absolute, "단정·최상급"),
    ):
        result, _ = run(fixture, [draft])
        unit = result["units"][0]
        assert unit["status"] == "reverted"
        assert any(marker in p for p in unit["problems"]), unit["problems"]


def test_an_exact_fact_not_in_the_source_is_reverted():
    fixture = load_persona_fixture("threshold_exclusion")
    draft = {**fixture["drafts"]["firstcard"][0], "exact_fact": "전월 30만원 쓰면 2만원 할인"}
    result, _ = run(fixture, [draft])
    assert result["units"][0]["status"] == "reverted"
    assert any("exact_fact" in p for p in result["units"][0]["problems"])


def test_a_broken_answer_is_retried_once_and_the_retry_is_used():
    fixture = load_persona_fixture("threshold_exclusion")
    fake = scripted_ask({"items": []}, {"items": fixture["drafts"]["lowfin"]})
    result = generate_persona_explanation(
        fixture["sources"],
        fixture["cards"],
        CLASSIFICATION,
        fake_ctx(),
        ask=fake,
        profile_id=LOWFIN,
        profiles_path=PROFILES,
    )
    assert fake.calls == ["PersonaUnitDrafts", "PersonaUnitDrafts"]
    assert fake.data[1]["previous_problems"]
    assert result["status"] == "완료"


def test_two_broken_answers_are_salvaged_not_raised():
    fixture = load_persona_fixture("threshold_exclusion")
    broken = {**fixture["drafts"]["lowfin"][0], "card_ids": ["nope"], "source_ids": ["dom-99"]}
    fake = scripted_ask({"items": [broken]})
    result = generate_persona_explanation(
        fixture["sources"],
        fixture["cards"],
        CLASSIFICATION,
        fake_ctx(),
        ask=fake,
        profile_id=LOWFIN,
        profiles_path=PROFILES,
    )
    assert len(fake.calls) == 2
    assert result["status"] == "원문 대체"
    assert result["units"][0]["status"] == "reverted"
    assert top_level_ids(result["html"]) == _originals(fixture)

    empty = scripted_ask({"items": []})
    result = generate_persona_explanation(
        fixture["sources"],
        fixture["cards"],
        CLASSIFICATION,
        fake_ctx(),
        ask=empty,
        profile_id=LOWFIN,
        profiles_path=PROFILES,
    )
    assert result["status"] == "원문 대체" and result["units"] == []


def test_only_this_modules_feedback_reaches_the_prompt():
    fixture = load_persona_fixture("threshold_exclusion")
    feedback = [
        {
            "module": "persona_explanation",
            "source_id": "dom-2",
            "reason": "사실 원장 값 누락",
            "requested_change": "일부 가맹점 제외를 남기세요",
        },
        {"module": "explanation_duty_check", "reason": "다른 모듈", "requested_change": "x"},
    ]
    _, fake = run(fixture, fixture["drafts"]["lowfin"], feedback=feedback)
    assert fake.data[0]["previous_feedback"] == [
        {
            "source_id": "dom-2",
            "reason": "사실 원장 값 누락",
            "requested_change": "일부 가맹점 제외를 남기세요",
        }
    ]


def test_a_given_profile_is_used_as_is_and_its_reader_reaches_the_prompt(tmp_path):
    fixture = load_persona_fixture("threshold_exclusion")
    profile = copy.deepcopy(resolve_profile(LOWFIN, PROFILES))
    profile["id"] = "nemotron:" + "0" * 32
    profile["attributes"]["reader"] = "74세 여자 · 학력 초등학교 · 직업 무직\n가상의 인물입니다."
    fake = scripted_ask({"items": fixture["drafts"]["lowfin"]})
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


def test_an_invalid_given_profile_keeps_the_original_text():
    fixture = load_persona_fixture("threshold_exclusion")
    profile = {
        **resolve_profile(LOWFIN, PROFILES),
        "status": "무효",
        "reason": "템플릿 버전 불일치",
    }
    result, fake = run(fixture, fixture["drafts"]["lowfin"], profile=profile)
    assert result["status"] == "원문 대체" and "템플릿 버전 불일치" in result["reason"]
    assert fake.calls == []


def test_the_task_limits_the_reader_sketch_to_register():
    assert "reader" in PERSONA_TASK
    assert "자격" in PERSONA_TASK.split("reader", 1)[1]
