"""`extract_evidence_cards` and `retrieve_reference_cases` write only their own keys, and the
graph reaches them right after a reviewable classification, before the display check."""

import shutil
from types import SimpleNamespace
from typing import cast

import yaml
from langgraph.runtime import Runtime

from financial_disclosure_review.core.context import Context
from financial_disclosure_review.core.state import empty_state
from financial_disclosure_review.graph import nodes
from financial_disclosure_review.graph.nodes import (
    card_ids_for,
    extract_evidence_cards,
    retrieve_reference_cases,
)
from tests.helpers import FIXTURE_DIR, state_with

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


def test_retrieve_without_cards_is_skipped_and_touches_nothing(tmp_path):
    update = retrieve_reference_cases(empty_state(), runtime(db_path=str(tmp_path / "x.sqlite")))
    assert set(update) == {"reference_cases"}
    assert update["reference_cases"]["status"] == "건너뜀"
    assert not (tmp_path / "x.sqlite").exists()


def test_retrieve_reads_the_corpus_yaml_when_the_db_has_no_cases(tmp_path, monkeypatch):
    """로컬 DB에 사례 테이블이 없어도(빌드는 임베딩 비용) 저장소 코퍼스로 BM25를 돌립니다.
    연결 agent는 스크립트 chat으로 검색 한 번 후 종료합니다."""
    from financial_disclosure_review.knowledge import linking
    from tests.domain.product_page.fake_chat import ScriptedChat

    script = [
        [{"name": "search_cases", "args": {"query": "최소 이자율만 강조", "card_ids": ["c1"]}}],
        [{"name": "finish", "args": {"reason": "맞는 사례 없음"}}],
        [{"name": "finish", "args": {"reason": "맞는 사례 없음"}}],
    ]
    real = linking.link_reference_cases
    monkeypatch.setattr(
        nodes,
        "link_reference_cases",
        lambda *a, **k: real(*a, **k, chat=ScriptedChat(script)),
    )
    rubric_dir = tmp_path / "assets"
    rubric_dir.mkdir()
    shutil.copy(FIXTURE_DIR / "cases" / "case_corpus.yaml", rubric_dir / "case_corpus.yaml")
    ids = [
        c["case_id"] for c in yaml.safe_load((rubric_dir / "case_corpus.yaml").read_text())["items"]
    ]
    (rubric_dir / "case_risk_kinds.yaml").write_text(
        yaml.safe_dump(
            {"cases": {cid: {"risk_kinds": ["rate_fee"], "text_verified": True} for cid in ids}},
            allow_unicode=True,
        )
    )
    state = state_with(
        classification={"product_type": "리볼빙", "page_type": "업무광고"},
        evidence_cards={"cards": [CARD]},
    )
    update = retrieve_reference_cases(
        state, runtime(db_path=str(tmp_path / "absent.sqlite"), rubric_dir=str(rubric_dir))
    )
    refs = update["reference_cases"]
    assert refs["method"]["cases_from"] == "corpus:case_corpus.yaml"
    assert refs["status"] in ("완료", "해당 사례 없음")
    assert refs["candidates"], "the revolving card must at least be scored against the corpus"
    assert refs["stop_reason"] == "finished"
    assert [t["tool"] for t in refs["agent_trace"]] == ["search_cases", "finish", "finish"]


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
