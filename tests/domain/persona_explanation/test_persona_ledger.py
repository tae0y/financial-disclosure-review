"""build_fact_ledger: every value an explanation must keep, as literal source strings."""

from financial_disclosure_review.domain.persona_explanation.ledger import (
    build_fact_ledger,
    number_kind,
)
from tests.domain.persona_explanation.persona_fixtures import load_persona_fixture


def _pairs(ledger: list[dict]) -> list[tuple[str, str, str]]:
    return [(f["card_id"], f["kind"], f["value"]) for f in ledger]


def test_threshold_benefit_yields_number_limit_condition_and_exception():
    ledger = build_fact_ledger(load_persona_fixture("threshold_exclusion")["cards"])
    assert _pairs(ledger) == [
        ("b1", "number", "30만원"),
        ("b1", "limit", "2만원"),
        ("b1", "condition", "전월 이용금액 30만원 이상"),
        ("b1", "exception", "일부 가맹점 제외"),
    ]
    assert [f["fact_id"] for f in ledger] == ["f1", "f2", "f3", "f4"]
    assert {f["source_id"] for f in ledger} == {"dom-2"}


def test_a_warning_card_becomes_a_penalty_holding_its_quote():
    fixture = load_persona_fixture("rate_penalty")
    ledger = build_fact_ledger(fixture["cards"])
    warning = fixture["cards"][1]
    assert ("c2", "penalty", warning["quote"]) in _pairs(ledger)
    assert ("c2", "limit", "3%p") in _pairs(ledger)
    assert ("c2", "number", "20%") in _pairs(ledger)


def test_periods_are_recognised_by_their_unit():
    ledger = build_fact_ledger(load_persona_fixture("annual_fee_refund")["cards"])
    assert ("a3", "period", "14일") in _pairs(ledger)
    assert ("a1", "number", "1만원") in _pairs(ledger)
    assert ("a2", "exception", "부가서비스 이용분 제외") in _pairs(ledger)


def test_number_kind_reads_the_quote_around_a_bare_number():
    assert number_kind("12", "할부 기간은 12개월입니다") == "period"
    assert number_kind("2만원", "통합 할인한도 월 2만원") == "limit"
    assert number_kind("2만원", "2만원 한도 내 할인") == "limit"
    assert number_kind("30만원", "30만원 이상 시 월 최대 2만원") == "number"


def test_eligibility_becomes_a_target_and_repeats_are_merged():
    cards = [
        {
            "id": "e1",
            "kind": "eligibility",
            "claim": "만 19세 이상 개인",
            "qualifiers": ["만 19세 이상 개인", "만 19세 이상 개인"],
            "exceptions": [],
            "numbers": ["19세"],
            "quote": "발급 대상: 만 19세 이상 개인",
            "source_id": "dom-9",
        },
        {
            "id": "e2",
            "kind": "eligibility",
            "claim": "원문에 없는 요약",
            "qualifiers": [],
            "exceptions": [],
            "numbers": [],
            "quote": "소득이 있는 개인",
            "source_id": "dom-10",
        },
    ]
    assert _pairs(build_fact_ledger(cards)) == [
        ("e1", "number", "19세"),
        ("e1", "condition", "만 19세 이상 개인"),
        ("e1", "target", "만 19세 이상 개인"),
        ("e2", "target", "소득이 있는 개인"),
    ]


def test_the_ledger_is_deterministic():
    cards = load_persona_fixture("revolving")["cards"]
    assert build_fact_ledger(cards) == build_fact_ledger(cards)
    assert build_fact_ledger([]) == []
