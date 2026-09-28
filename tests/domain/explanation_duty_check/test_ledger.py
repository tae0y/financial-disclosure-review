"""check_ledger: code decides literal presence; one model call covers only what code cannot."""

from financial_disclosure_review.core.text import visible_text
from financial_disclosure_review.domain.explanation_duty_check.ledger import (
    UNMAPPED_SOURCE,
    check_ledger,
)
from financial_disclosure_review.domain.persona_explanation.generate import (
    generate_persona_explanation,
)
from tests.domain.persona_explanation.persona_fixtures import (
    CLASSIFICATION,
    FIRSTCARD,
    LOWFIN,
    PROFILES,
    fake_ctx,
    load_persona_fixture,
    scripted_ask,
)


def _explain(name: str, drafts: list[dict], profile_id: str = LOWFIN) -> tuple[dict, dict]:
    fixture = load_persona_fixture(name)
    result = generate_persona_explanation(
        fixture["sources"],
        fixture["cards"],
        CLASSIFICATION,
        fake_ctx(),
        ask=scripted_ask({"items": drafts}),
        profile_id=profile_id,
        profiles_path=PROFILES,
    )
    return fixture, result


def _original_text(fixture: dict) -> str:
    return " ".join(s["text"] for s in fixture["sources"])


def _run_check(fixture: dict, result: dict, fake, explanation_text: str | None = None) -> dict:
    return check_ledger(
        result["fact_ledger"],
        result["units"],
        _original_text(fixture),
        explanation_text if explanation_text is not None else visible_text(result["html"]),
        "fake",
        fake,
    )


def test_all_values_present_means_zero_model_calls():
    fixture, result = _explain("threshold_exclusion", fixture_drafts("lowfin"))
    fake = scripted_ask({"items": []})
    checked = _run_check(fixture, result, fake)
    assert fake.calls == []
    assert {r["verdict"] for r in checked["ledger"]} == {"보존"}
    assert {r["decided_by"] for r in checked["ledger"]} == {"code"}
    assert checked["fidelity"] == []


def test_two_persona_phrasings_give_the_same_code_decided_ledger():
    fixture = load_persona_fixture("threshold_exclusion")
    rows = []
    for key, profile_id in (("lowfin", LOWFIN), ("firstcard", FIRSTCARD)):
        _, result = _explain("threshold_exclusion", fixture["drafts"][key], profile_id)
        assert result["units"][0]["status"] == "accepted"
        fake = scripted_ask({"items": []})
        checked = _run_check(fixture, result, fake)
        assert fake.calls == []
        rows.append(
            [(r["fact_id"], r["kind"], r["verdict"], r["decided_by"]) for r in checked["ledger"]]
        )
    assert rows[0] == rows[1]
    # The two explanations really are worded differently.
    lowfin = fixture["drafts"]["lowfin"][0]["explanation"]
    assert lowfin != fixture["drafts"]["firstcard"][0]["explanation"]


def test_absent_values_go_to_exactly_one_model_call():
    fixture, result = _explain("threshold_exclusion", fixture_drafts("lowfin"))
    explanation = "지난달 30만원 넘게 쓰면 한 달 2만원까지 깎아 줍니다. 몇몇 매장은 빠집니다."
    fake = scripted_ask(
        {
            "items": [
                {
                    "fact_id": "f3",
                    "verdict": "약화",
                    "quote": "지난달 30만원 넘게 쓰면",
                    "reason": "이상이 넘게로 바뀌어 경계값이 흐려짐",
                },
                {
                    "fact_id": "f4",
                    "verdict": "보존",
                    "quote": "몇몇 매장은 빠집니다.",
                    "reason": "제외 대상이 남아 있음",
                },
            ]
        }
    )
    checked = _run_check(fixture, result, fake, explanation)
    assert fake.calls == ["LedgerSemantics"]
    assert [i["fact_id"] for i in fake.data[0]["items"]] == ["f3", "f4"]
    by_id = {r["fact_id"]: r for r in checked["ledger"]}
    assert by_id["f1"]["decided_by"] == "code" and by_id["f1"]["verdict"] == "보존"
    assert by_id["f3"]["decided_by"] == "model" and by_id["f3"]["verdict"] == "약화"
    assert by_id["f4"]["verdict"] == "보존"
    assert [(f["code"], f["kind"]) for f in checked["fidelity"]] == [("f3", "약화")]
    row = checked["fidelity"][0]
    assert row["source_ids"] == ["dom-2"]
    assert row["informational"] is False


def fixture_drafts(key: str) -> list[dict]:
    return load_persona_fixture("threshold_exclusion")["drafts"][key]


def test_a_quote_not_in_the_explanation_is_salvaged_to_cannot_judge():
    fixture, result = _explain("threshold_exclusion", fixture_drafts("lowfin"))
    explanation = "지난달 많이 쓰면 할인됩니다."
    wrong = {
        "items": [
            {"fact_id": f, "verdict": "보존", "quote": "지어낸 인용", "reason": "있음"}
            for f in ("f1", "f2", "f3", "f4")
        ]
    }
    fake = scripted_ask(wrong)
    checked = _run_check(fixture, result, fake, explanation)
    assert len(fake.calls) == 2
    assert {r["verdict"] for r in checked["ledger"]} == {"판정 불가"}
    assert {f["kind"] for f in checked["fidelity"]} == {"판정 불가"}


def test_a_structurally_wrong_answer_marks_every_pending_fact_cannot_judge():
    fixture, result = _explain("threshold_exclusion", fixture_drafts("lowfin"))
    fake = scripted_ask(
        {"items": [{"fact_id": "f9", "verdict": "누락", "quote": "", "reason": "x"}]}
    )
    checked = _run_check(fixture, result, fake, "빈 설명")
    assert len(fake.calls) == 2
    assert [r["verdict"] for r in checked["ledger"]] == ["판정 불가"] * 4


def test_fidelity_rows_on_reverted_units_are_informational():
    fixture, result = _explain("threshold_exclusion", fixture_drafts("invented_number"))
    assert result["units"][0]["status"] == "reverted"
    fake = scripted_ask(
        {
            "items": [
                {"fact_id": "f4", "verdict": "누락", "quote": "", "reason": "제외 조건 없음"},
            ]
        }
    )
    explanation = "전월 이용금액 30만원 이상 시 월 최대 2만원 할인"
    checked = _run_check(fixture, result, fake, explanation)
    assert [(f["code"], f["kind"]) for f in checked["fidelity"]] == [("f4", "누락")]
    assert checked["fidelity"][0]["informational"] is True
    assert checked["fidelity"][0]["unit_ids"] == ["u1"]


def test_an_added_number_is_detected_by_code_and_mapped_to_its_unit():
    fixture, result = _explain("threshold_exclusion", fixture_drafts("lowfin"))
    unit = dict(result["units"][0])
    unit["explanation"] += " 1년이면 24만원입니다."
    explanation = visible_text(result["html"]) + " 1년이면 24만원입니다."
    fake = scripted_ask({"items": []})
    checked = check_ledger(
        result["fact_ledger"], [unit], _original_text(fixture), explanation, "fake", fake
    )
    assert fake.calls == []
    added = [f for f in checked["fidelity"] if f["kind"] == "추가"]
    assert [(f["code"], f["quote"], f["decided_by"]) for f in added] == [("NUM", "24", "code")]
    assert added[0]["source_ids"] == ["dom-2"] and added[0]["unit_ids"] == ["u1"]
    assert added[0]["informational"] is False


def test_fidelity_source_ids_are_never_empty():
    ledger = [
        {"fact_id": "f1", "card_id": "x1", "source_id": "", "kind": "number", "value": "7만원"},
    ]
    fake = scripted_ask(
        {"items": [{"fact_id": "f1", "verdict": "누락", "quote": "", "reason": "없음"}]}
    )
    checked = check_ledger(ledger, [], "연회비 7만원", "연회비가 있습니다. 99원", "fake", fake)
    assert checked["fidelity"]
    for row in checked["fidelity"]:
        assert row["source_ids"] and all(row["source_ids"])
    assert checked["fidelity"][0]["source_ids"] == [UNMAPPED_SOURCE]
    # A fact with no related unit only shows original text, so it is informational; an added
    # number that no unit claims is not.
    by_kind = {f["kind"]: f for f in checked["fidelity"]}
    assert by_kind["누락"]["informational"] is True
    assert by_kind["추가"]["informational"] is False


def test_every_fixture_explanation_keeps_non_empty_fidelity_sources():
    for name in ("revolving", "annual_fee_refund", "rate_penalty"):
        fixture = load_persona_fixture(name)
        _, result = _explain(name, fixture["drafts"])
        fake = scripted_ask({"items": []})
        checked = _run_check(fixture, result, fake)
        assert fake.calls == [], name
        assert all(r["source_ids"] for r in checked["ledger"])
        assert checked["fidelity"] == [], name
