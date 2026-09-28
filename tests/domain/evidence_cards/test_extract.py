from financial_disclosure_review.core.context import Context
from financial_disclosure_review.domain.evidence_cards.blocks import page_sources
from financial_disclosure_review.domain.evidence_cards.extract import extract_evidence_cards
from financial_disclosure_review.domain.evidence_cards.schema import EvidenceCardDrafts
from tests.helpers import FEE, FakeAsk, make_render_page

CTX = Context(model="test-model")
CLASSIFICATION = {"product_type": "신용카드", "page_type": "상품광고", "reason": "이유"}


def card_draft(**overrides) -> dict:
    base = {
        "kind": "fee_claim",
        "subject": "연회비",
        "claim": "연회비는 연 1만원",
        "qualifiers": [],
        "exceptions": [],
        "numbers": [],
        "quote": FEE,
        "source_id": "dom-3",
    }
    base.update(overrides)
    return base


def fake_items(*items) -> FakeAsk:
    def answer(schema, data):
        assert schema is EvidenceCardDrafts
        return {"items": list(items)}

    return FakeAsk(answer)


def test_page_sources_marks_default_default_revealed_visibility():
    page = make_render_page()
    sources = page_sources(page)
    by_text = {s["text"]: s for s in sources}
    assert by_text["테스트 신용카드"]["visibility"] == "default_visible"
    assert by_text[FEE]["visibility"] == "revealed"
    assert [s["source_id"] for s in sources] == ["dom-0", "dom-1", "dom-2", "dom-3"]


def test_valid_card_kept_with_source_visibility():
    page = make_render_page()
    fake = fake_items(card_draft())
    result = extract_evidence_cards(page, CLASSIFICATION, CTX, ask=fake)
    assert result["status"] == "완료"
    assert result["model_calls"] == 1
    assert len(result["cards"]) == 1
    card = result["cards"][0]
    assert card["id"] == "c1"
    assert card["quote"] == FEE
    assert card["source_id"] == "dom-3"
    assert card["visibility"] == "revealed"  # FEE is hidden by default, revealed by the expand
    assert result["rejected"] == []


def test_quote_not_in_source_rejected():
    page = make_render_page()
    fake = fake_items(card_draft(quote="원문에 없는 문장입니다"))
    result = extract_evidence_cards(page, CLASSIFICATION, CTX, ask=fake)
    assert result["status"] == "카드 없음"
    assert result["cards"] == []
    assert len(result["rejected"]) == 1
    assert "quote" in result["rejected"][0]["reason"]
    assert len(fake.calls) == 2  # one retry, then salvage


def test_invented_number_rejected():
    page = make_render_page()
    fake = fake_items(card_draft(numbers=["999999"]))
    result = extract_evidence_cards(page, CLASSIFICATION, CTX, ask=fake)
    assert result["cards"] == []
    assert "999999" in result["rejected"][0]["reason"]


def test_unknown_source_id_rejected():
    page = make_render_page()
    fake = fake_items(card_draft(source_id="dom-99"))
    result = extract_evidence_cards(page, CLASSIFICATION, CTX, ask=fake)
    assert result["cards"] == []
    assert "dom-99" in result["rejected"][0]["reason"]


def test_qualifier_not_in_quote_rejected():
    page = make_render_page()
    fake = fake_items(card_draft(qualifiers=["없는 조건"]))
    result = extract_evidence_cards(page, CLASSIFICATION, CTX, ask=fake)
    assert result["cards"] == []
    assert "없는 조건" in result["rejected"][0]["reason"]


def test_unknown_kind_rejected():
    page = make_render_page()
    fake = fake_items(card_draft(kind="추천"))
    result = extract_evidence_cards(page, CLASSIFICATION, CTX, ask=fake)
    assert result["cards"] == []
    assert "kind" in result["rejected"][0]["reason"]


def test_retry_once_then_salvage_keeps_only_valid():
    page = make_render_page()
    good = card_draft(source_id="dom-1", quote="커피 전문점에서 10% 할인", kind="benefit_claim")
    bad = card_draft(numbers=["777"])
    fake = fake_items(good, bad)
    result = extract_evidence_cards(page, CLASSIFICATION, CTX, ask=fake)
    assert result["model_calls"] == 2
    assert len(result["cards"]) == 1
    assert result["cards"][0]["quote"] == "커피 전문점에서 10% 할인"
    assert len(result["rejected"]) == 1
    assert result["status"] == "완료"


def test_dedup_by_quote_and_kind():
    page = make_render_page()
    fake = fake_items(card_draft(), card_draft())
    result = extract_evidence_cards(page, CLASSIFICATION, CTX, ask=fake)
    assert len(result["cards"]) == 1


def test_deterministic_ids_follow_source_order():
    page = make_render_page()
    later = card_draft(source_id="dom-3")
    earlier = card_draft(source_id="dom-1", quote="커피 전문점에서 10% 할인", kind="benefit_claim")
    fake = fake_items(later, earlier)  # model answers dom-3 first, dom-1 second
    result = extract_evidence_cards(page, CLASSIFICATION, CTX, ask=fake)
    ids_by_source = {c["source_id"]: c["id"] for c in result["cards"]}
    assert ids_by_source["dom-1"] == "c1"  # earlier source wins c1 regardless of answer order
    assert ids_by_source["dom-3"] == "c2"


def test_no_html_is_unjudged_with_zero_calls():
    fake = fake_items(card_draft())
    result = extract_evidence_cards({"html": ""}, CLASSIFICATION, CTX, ask=fake)
    assert result["status"] == "판정 불가"
    assert result["model_calls"] == 0
    assert fake.calls == []
    assert result["sources"] == []
    assert result["cards"] == []


def test_missing_product_type_is_unjudged_with_zero_calls():
    page = make_render_page()
    fake = fake_items(card_draft())
    result = extract_evidence_cards(page, {"page_type": "상품광고"}, CTX, ask=fake)
    assert result["status"] == "판정 불가"
    assert result["model_calls"] == 0
    assert fake.calls == []


def test_coverage_gap_attachment():
    page = make_render_page()
    page = {
        **page,
        "coverage": {
            "gaps": [
                {"kind": "hidden_text", "status": "open"},
                {"kind": "benefit_without_condition", "status": "unresolved"},
                {"kind": "hidden_text", "status": "closed"},  # closed: dropped
            ]
        },
    }
    fake = fake_items(card_draft(kind="benefit_claim", quote="테스트 신용카드", source_id="dom-0"))
    result = extract_evidence_cards(page, CLASSIFICATION, CTX, ask=fake)
    card_id = result["cards"][0]["id"]
    gaps_by_kind = {g["kind"]: g for g in result["coverage_gaps"]}
    assert set(gaps_by_kind) == {
        "hidden_text",
        "benefit_without_condition",
        "claim_without_visible_condition",
    }
    # TITLE is default-visible in make_render_page, so it is not a hidden_text-relevant card.
    assert gaps_by_kind["hidden_text"]["card_ids"] == []
    assert gaps_by_kind["benefit_without_condition"]["card_ids"] == [card_id]
    assert gaps_by_kind["claim_without_visible_condition"]["card_ids"] == [card_id]
    assert gaps_by_kind["claim_without_visible_condition"]["status"] == "open"


def test_coverage_gap_hidden_text_matches_unresolved_card():
    # No snapshots at all -> display_blocks finds nothing -> every source is "unresolved".
    page = {
        "html": f"<p>{FEE}</p>",
        "snapshots": [],
        "coverage": {"gaps": [{"kind": "hidden_text", "status": "open"}]},
    }
    fake = fake_items(card_draft(source_id="dom-0"))
    result = extract_evidence_cards(page, CLASSIFICATION, CTX, ask=fake)
    assert result["cards"][0]["visibility"] == "unresolved"
    gap = next(g for g in result["coverage_gaps"] if g["kind"] == "hidden_text")
    assert gap["card_ids"] == [result["cards"][0]["id"]]
