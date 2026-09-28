from financial_disclosure_review.evaluation.evidence_metrics import card_metrics


def test_card_metrics_quote_resolution_and_recall():
    sources = [{"source_id": "dom-0", "text": "연회비는 연 1만원입니다."}]
    cards = [{"id": "c1", "source_id": "dom-0", "quote": "연회비는 연 1만원입니다."}]
    gold = [
        {"quote": "연회비는 연 1만원입니다.", "kind": "fee_claim", "risk": False},
        {"quote": "원문에 없는 문구", "kind": "warning", "risk": True},
    ]
    metrics = card_metrics(cards, sources, gold)
    assert metrics["cards"] == 1
    assert metrics["quote_resolution"] == 1.0
    assert metrics["gold_entries"] == 2
    assert metrics["gold_recall"] == 0.5
    assert metrics["risk_gold_entries"] == 1
    assert metrics["risk_gold_recall"] == 0.0
    assert metrics["missed_gold_quotes"] == ["원문에 없는 문구"]


def test_card_metrics_unresolved_quote_is_excluded_from_resolution():
    sources = [{"source_id": "dom-0", "text": "연회비는 연 1만원입니다."}]
    cards = [
        {"id": "c1", "source_id": "dom-0", "quote": "연회비는 연 1만원입니다."},
        {"id": "c2", "source_id": "dom-0", "quote": "원문에 없는 문장"},
        {"id": "c3", "source_id": "dom-missing", "quote": "연회비는 연 1만원입니다."},
    ]
    metrics = card_metrics(cards, sources, gold=[])
    assert metrics["quote_resolution"] == round(1 / 3, 3)
    assert set(metrics["unresolved_card_ids"]) == {"c2", "c3"}


def test_card_metrics_empty_inputs_do_not_divide_by_zero():
    metrics = card_metrics([], [], [])
    assert metrics["quote_resolution"] is None
    assert metrics["gold_recall"] is None
    assert metrics["risk_gold_recall"] is None
