"""`extract_evidence_cards` writes only its own key, and the graph reaches it right after a
reviewable classification, before the display check."""

from types import SimpleNamespace
from typing import cast

from langgraph.runtime import Runtime

from financial_disclosure_review.core.context import Context
from financial_disclosure_review.graph import nodes
from financial_disclosure_review.graph.nodes import card_ids_for, extract_evidence_cards
from tests.helpers import state_with

CARD = {
    "id": "c1",
    "kind": "rate_claim",
    "subject": "리볼빙 이자율",
    "claim": "리볼빙 이자율은 최소 이자율만 첫 화면에 표기하고 평균 이자율은 안내하지 않습니다",
    "qualifiers": [],
    "exceptions": [],
    "numbers": ["5.4%"],
    "quote": "리볼빙 이자율은 최소 5.4%부터 적용됩니다",
    "source_id": "dom-1",
    "visibility": "default_visible",
}


def runtime(**overrides) -> Runtime[Context]:
    return cast(Runtime[Context], SimpleNamespace(context=Context(model="fake", **overrides)))


def test_extract_without_a_classification_is_unjudgeable_and_calls_no_model():
    update = extract_evidence_cards(state_with(product_page={"html": "<p>본문</p>"}), runtime())
    assert set(update) == {"evidence_cards"}
    assert update["evidence_cards"]["status"] == "판정 불가"
    assert update["evidence_cards"]["model_calls"] == 0


def test_display_items_carry_the_cards_their_quotes_overlap(monkeypatch):
    monkeypatch.setattr(
        nodes,
        "judge_display",
        lambda page, classification, ctx: {
            "items": [{"code": "E02", "verdict": "적합", "quotes": ["최소 5.4%부터"]}],
            "judgments": {"status": "완료"},
        },
    )
    state = state_with(
        product_page={"html": "<p>x</p>", "snapshots": [{}]},
        classification={"product_type": "리볼빙", "page_type": "업무광고"},
        evidence_cards={"cards": [CARD]},
    )
    update = nodes.judge_display_method(state, runtime())
    assert update["display_check"]["items"][0]["card_ids"] == ["c1"]


def test_card_ids_for_ignores_empty_quotes():
    assert card_ids_for(["", "  "], [CARD]) == []
    assert card_ids_for(["리볼빙 이자율은 최소 5.4%부터 적용됩니다 (연)"], [CARD]) == ["c1"]
