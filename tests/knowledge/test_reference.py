"""Deterministic reference-case retrieval: `knowledge.reference.retrieve_reference_cases`.

Everything here is offline: the case DB is built with `FakeEmbed` (as `test_cases.py` does),
and the scoring itself never calls a model or an embedding endpoint unless `rerank=True`, in
which case a `FakeEmbed` is injected too. `RATE_CARD`/`LEGIBILITY_CARD`/etc. are cards shaped
like the input contract's evidence cards; `_custom_case_db` builds a tiny hand-written corpus
(hashes computed inline) for the tests that need exact control over case content — the boost
and text-verification tests would be too fragile to write against the real corpus's actual
text.
"""

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from financial_disclosure_review.evaluation.reference_metrics import compute_reference_metrics
from financial_disclosure_review.knowledge.build_cases import build_case_db
from financial_disclosure_review.knowledge.reference import (
    DEFAULT_THRESHOLD,
    retrieve_reference_cases,
)
from tests.helpers import EMBED_VOCAB, FIXTURE_DIR, FakeEmbed

CORPUS = FIXTURE_DIR / "cases"
GOLD_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "reference_links.synthetic.json"
# The synthetic set paraphrases each case's own wording, so it separates at a far lower score
# than real page cards do; it checks ranking self-consistency, not the production threshold.
SYNTHETIC_THRESHOLD = 1.5

TEST_RISK_KINDS = {
    "ai_drafted": True,
    "human_review": False,
    "cases": {
        "case.test_revolving_min_rate": {"risk_kinds": ["rate_fee"], "text_verified": True},
        "case.test_revolving_legibility": {
            "risk_kinds": ["warning_penalty"],
            "text_verified": True,
        },
        "case.test_card_benefit_condition": {
            "risk_kinds": ["benefit_condition"],
            "text_verified": True,
        },
        "case.test_loan_eligibility": {"risk_kinds": ["benefit_condition"], "text_verified": True},
    },
}

RATE_CARD = {
    "id": "p1",
    "kind": "rate_claim",
    "subject": "리볼빙 이자율",
    "claim": "리볼빙 이자율은 최소 이자율만 첫 화면에 표기하고 평균 이자율은 안내하지 않습니다",
    "qualifiers": ["평균 이자율 언급 없음"],
    "exceptions": [],
    "numbers": ["5.4%"],
    "quote": "리볼빙 이자율은 최소 5.4%부터 적용됩니다",
    "source_id": "dom-1",
    "visibility": "visible",
}

LEGIBILITY_CARD = {
    "id": "p2",
    "kind": "warning",
    "subject": "리볼빙 가입 안내문",
    "claim": "가입화면 안내문의 글자 크기가 작고 모두 검은색으로 기재되어 중요사항을 구별하기"
    " 어렵습니다",
    "qualifiers": [],
    "exceptions": [],
    "numbers": [],
    "quote": "가입화면 안내문의 글자 크기가 작고 검은색으로만 표기됩니다",
    "source_id": "dom-2",
    "visibility": "visible",
}

BENEFIT_CARD = {
    "id": "p3",
    "kind": "benefit_claim",
    "subject": "무이자할부 포인트 적립",
    "claim": "무이자할부를 이용해도 포인트 적립과 할인 혜택을 그대로 받을 수 있습니다",
    "qualifiers": ["실적 산정 및 포인트 적립 제외 조건 미기재"],
    "exceptions": [],
    "numbers": [],
    "quote": "무이자할부 이용 시 포인트가 적립됩니다",
    "source_id": "dom-3",
    "visibility": "visible",
}


@pytest.fixture(scope="module")
def db_path(tmp_path_factory) -> str:
    path = tmp_path_factory.mktemp("reference-cases") / "reference.sqlite"
    build_case_db(CORPUS, path, embed=FakeEmbed(), dimensions=len(EMBED_VOCAB))
    return str(path)


@pytest.fixture(scope="module")
def risk_kinds_path(tmp_path_factory) -> str:
    path = tmp_path_factory.mktemp("reference-risk-kinds") / "case_risk_kinds.yaml"
    path.write_text(yaml.safe_dump(TEST_RISK_KINDS, allow_unicode=True))
    return str(path)


def _case_item(case_id, product_types, text, issue, mvp_signal, risk_kinds, **overrides):
    text = text.strip() + "\n"
    text_verified = overrides.pop("_text_verified", True)
    item = {
        "case_id": case_id,
        "record_type": "지적사례",
        "institution": "금융감독원",
        "firm": "not_disclosed",
        "official_date": "2024-01-01",
        "official_primary_url": f"https://example.test/{case_id}",
        "source_tier": 1,
        "product_types": list(product_types),
        "product_basis": "직접",
        "product_subtype": "테스트 상품",
        "legal_basis": "금융소비자보호법 제22조",
        "issue": issue,
        "outcome": "테스트 조치",
        "mvp_signal": mvp_signal,
        "page_only_detectability": "full",
        "related_checklist": ["A01"],
        "text": text,
        "text_sha256": hashlib.sha256(text.strip().encode("utf-8")).hexdigest(),
        "retrieved_at": "2026-09-27",
    }
    item.update(overrides)
    return item, {"risk_kinds": risk_kinds, "text_verified": text_verified}


# Two cases with byte-identical scoring content but different risk kinds: isolates the boost's
# effect on ordering from any BM25 difference.
_TWIN_TEXT = (
    "금리 안내가 미흡하여 소비자가 금리를 오인할 수 있습니다. 이자율 표기가 명확하지 않습니다."
)
_TWIN_ISSUE = "금리 안내가 미흡합니다"
_TWIN_SIGNAL = "금리 표기 위치와 명확성"

_custom_a, _risk_a = _case_item(
    "case.custom_twin_a", ["테스트유형"], _TWIN_TEXT, _TWIN_ISSUE, _TWIN_SIGNAL, ["rate_fee"]
)
_custom_b, _risk_b = _case_item(
    "case.custom_twin_b", ["테스트유형"], _TWIN_TEXT, _TWIN_ISSUE, _TWIN_SIGNAL, ["warning_penalty"]
)
_custom_c, _risk_c = _case_item(
    "case.custom_partial",
    ["테스트유형2"],
    "부분적으로만 확인 가능한 안내 문구입니다. 화면 일부 텍스트가 이미지로 되어 있어"
    " 코드로 전부 판정하기 어렵습니다.",
    "이미지 안내문 판정이 어렵습니다",
    "이미지 안내문 텍스트 존재 여부",
    ["benefit_condition"],
    page_only_detectability="partial",
)
_custom_d, _risk_d = _case_item(
    "case.custom_unverified",
    ["테스트유형3"],
    "확인되지 않은 원문입니다. 축자 대조가 되지 않은 게시물 인용입니다.",
    "원문 미확인 게시물입니다",
    "게시물 제목과 URL만 확인됨",
    ["warning_penalty"],
    _text_verified=False,
)

TWIN_A_CARD = {
    "id": "c1",
    "kind": "rate_claim",
    "subject": "x",
    "claim": "금리 안내가 부족합니다",
    "qualifiers": [],
    "exceptions": [],
    "numbers": [],
    "quote": "금리 안내가 부족합니다",
    "source_id": "dom-c1",
    "visibility": "visible",
}
TWIN_B_CARD = {**TWIN_A_CARD, "id": "c2", "kind": "warning"}

PARTIAL_CARD = {
    "id": "cc",
    "kind": "condition",
    "subject": "이미지 안내문",
    "claim": "이미지 안내문 판정이 어렵습니다",
    "qualifiers": ["화면 일부 텍스트가 이미지로 되어 있음"],
    "exceptions": [],
    "numbers": [],
    "quote": "이미지 안내문",
    "source_id": "dom-cc",
    "visibility": "visible",
}

UNVERIFIED_CARD = {
    "id": "cd",
    "kind": "warning",
    "subject": "원문 미확인 게시물",
    "claim": "원문 미확인 게시물입니다",
    "qualifiers": ["축자 대조가 되지 않음"],
    "exceptions": [],
    "numbers": [],
    "quote": "원문 미확인",
    "source_id": "dom-cd",
    "visibility": "visible",
}


@pytest.fixture(scope="module")
def custom_db(tmp_path_factory) -> str:
    corpus_dir = tmp_path_factory.mktemp("custom-corpus")
    items = [_custom_a, _custom_b, _custom_c, _custom_d]
    (corpus_dir / "case_corpus.yaml").write_text(
        yaml.safe_dump({"items": items}, allow_unicode=True)
    )
    db = tmp_path_factory.mktemp("custom-db") / "reference.sqlite"
    build_case_db(corpus_dir, db, embed=FakeEmbed(), dimensions=len(EMBED_VOCAB))
    return str(db)


@pytest.fixture(scope="module")
def custom_risk_kinds_path(tmp_path_factory) -> str:
    cases = {
        "case.custom_twin_a": _risk_a,
        "case.custom_twin_b": _risk_b,
        "case.custom_partial": _risk_c,
        "case.custom_unverified": _risk_d,
    }
    path = tmp_path_factory.mktemp("custom-risk-kinds") / "case_risk_kinds.yaml"
    path.write_text(
        yaml.safe_dump(
            {"ai_drafted": True, "human_review": False, "cases": cases}, allow_unicode=True
        )
    )
    return str(path)


# ---------------------------------------------------------------------------------------------
# status: 건너뜀 / 판정 불가 / 해당 사례 없음 / 완료
# ---------------------------------------------------------------------------------------------


def test_no_cards_skips_and_never_touches_the_db(tmp_path):
    absent = tmp_path / "absent.sqlite"
    result = retrieve_reference_cases([], {"product_type": "리볼빙"}, absent)
    assert result["status"] == "건너뜀"
    assert result["candidates"] == [] and result["links"] == []
    assert not absent.exists()


def test_a_missing_db_is_unjudgeable(tmp_path, risk_kinds_path):
    result = retrieve_reference_cases(
        [RATE_CARD],
        {"product_type": "리볼빙"},
        tmp_path / "absent.sqlite",
        risk_kinds_path=risk_kinds_path,
    )
    assert result["status"] == "판정 불가"
    assert "build-cases" in result["reason"]
    assert result["candidates"] == [] and result["links"] == []


def test_a_missing_risk_kinds_file_is_unjudgeable(db_path, tmp_path):
    result = retrieve_reference_cases(
        [RATE_CARD],
        {"product_type": "리볼빙"},
        db_path,
        risk_kinds_path=tmp_path / "absent_risk_kinds.yaml",
    )
    assert result["status"] == "판정 불가"
    assert "case_risk_kinds" in result["reason"]


def test_a_product_type_with_no_cases_reports_none(db_path, risk_kinds_path):
    result = retrieve_reference_cases(
        [RATE_CARD], {"product_type": "할부금융·리스"}, db_path, risk_kinds_path=risk_kinds_path
    )
    assert result["status"] == "해당 사례 없음"
    assert "할부금융·리스" in result["reason"]
    assert result["candidates"] == [] and result["links"] == []


def test_a_completed_search_finds_the_matching_case(db_path, risk_kinds_path):
    result = retrieve_reference_cases(
        [RATE_CARD],
        {"product_type": "리볼빙"},
        db_path,
        risk_kinds_path=risk_kinds_path,
        threshold=SYNTHETIC_THRESHOLD,
    )
    assert result["status"] == "완료"
    assert [link["case_id"] for link in result["links"]] == ["case.test_revolving_min_rate"]


# ---------------------------------------------------------------------------------------------
# product-type hard filter
# ---------------------------------------------------------------------------------------------


def test_product_type_is_a_hard_filter_not_a_ranking_signal(db_path, risk_kinds_path):
    # RATE_CARD is all about revolving interest rates, but the product type only has one case
    # (case.test_loan_eligibility) with completely unrelated content — the revolving cases must
    # never appear, however strong their textual match would have been.
    result = retrieve_reference_cases(
        [RATE_CARD],
        {"product_type": "장기카드대출"},
        db_path,
        risk_kinds_path=risk_kinds_path,
        threshold=0.0,
    )
    ids = {c["case_id"] for c in result["candidates"]}
    assert ids <= {"case.test_loan_eligibility"}
    assert "case.test_revolving_min_rate" not in ids


# ---------------------------------------------------------------------------------------------
# risk-kind boost: reorders, never excludes
# ---------------------------------------------------------------------------------------------


def test_risk_kind_boost_changes_order_without_excluding_either_case(
    custom_db, custom_risk_kinds_path
):
    by_rate = retrieve_reference_cases(
        [TWIN_A_CARD],
        {"product_type": "테스트유형"},
        custom_db,
        risk_kinds_path=custom_risk_kinds_path,
        threshold=0.0,
    )
    by_warning = retrieve_reference_cases(
        [TWIN_B_CARD],
        {"product_type": "테스트유형"},
        custom_db,
        risk_kinds_path=custom_risk_kinds_path,
        threshold=0.0,
    )
    ids_by_rate = {c["case_id"] for c in by_rate["candidates"]}
    ids_by_warning = {c["case_id"] for c in by_warning["candidates"]}
    assert ids_by_rate == {"case.custom_twin_a", "case.custom_twin_b"}
    assert ids_by_warning == {"case.custom_twin_a", "case.custom_twin_b"}
    assert by_rate["candidates"][0]["case_id"] == "case.custom_twin_a"  # rate_fee wins the boost
    assert by_warning["candidates"][0]["case_id"] == "case.custom_twin_b"  # warning_penalty does
    # the bm25 component is identical either way — only the boost moved the ranking
    bm25_by_rate = {c["case_id"]: c["bm25"] for c in by_rate["candidates"]}
    bm25_by_warning = {c["case_id"]: c["bm25"] for c in by_warning["candidates"]}
    assert bm25_by_rate == bm25_by_warning


# ---------------------------------------------------------------------------------------------
# threshold filters weak links
# ---------------------------------------------------------------------------------------------


def test_threshold_filters_a_weak_link(db_path, risk_kinds_path):
    weak_card = {
        "id": "p9",
        "kind": "footnote",
        "subject": "고객센터 운영시간",
        "claim": "고객센터는 평일 오전 9시부터 오후 6시까지 운영합니다",
        "qualifiers": [],
        "exceptions": [],
        "numbers": ["9", "6"],
        "quote": "고객센터는 평일 오전 9시부터 오후 6시까지 운영합니다",
        "source_id": "dom-9",
        "visibility": "visible",
    }
    lenient = retrieve_reference_cases(
        [weak_card],
        {"product_type": "신용카드"},
        db_path,
        risk_kinds_path=risk_kinds_path,
        threshold=0.0,
    )
    strict = retrieve_reference_cases(
        [weak_card],
        {"product_type": "신용카드"},
        db_path,
        risk_kinds_path=risk_kinds_path,
        threshold=DEFAULT_THRESHOLD,
    )
    assert lenient["candidates"]  # some weak overlap was scored
    assert strict["links"] == []
    assert strict["status"] == "해당 사례 없음"


# ---------------------------------------------------------------------------------------------
# link fields
# ---------------------------------------------------------------------------------------------


def test_link_fields_are_present_and_case_quote_is_locatable(db_path, risk_kinds_path):
    result = retrieve_reference_cases(
        [LEGIBILITY_CARD], {"product_type": "리볼빙"}, db_path, risk_kinds_path=risk_kinds_path
    )
    assert result["links"]
    link = result["links"][0]
    for key in (
        "case_id",
        "card_ids",
        "page_quote",
        "case_quote",
        "case_quote_note",
        "same_pattern",
        "material_difference",
        "page_only_detectability",
        "page_only_note",
        "official_url",
    ):
        assert key in link
    assert link["case_id"] == "case.test_revolving_legibility"
    assert link["card_ids"] == ["p2"]
    assert link["page_quote"] == LEGIBILITY_CARD["quote"]
    assert link["case_quote"]
    assert (
        link["case_quote"]
        in yaml.safe_load((CORPUS / "case_corpus.yaml").read_text())["items"][1]["text"]
    )
    assert link["official_url"] == "https://example.test/revolving-legibility"
    assert link["page_only_note"] == ""  # this case is `full`


def test_partial_detectability_carries_the_page_only_note(custom_db, custom_risk_kinds_path):
    result = retrieve_reference_cases(
        [PARTIAL_CARD],
        {"product_type": "테스트유형2"},
        custom_db,
        risk_kinds_path=custom_risk_kinds_path,
        threshold=SYNTHETIC_THRESHOLD,
    )
    assert result["links"]
    link = next(link for link in result["links"] if link["case_id"] == "case.custom_partial")
    assert link["page_only_detectability"] == "partial"
    assert link["page_only_note"] == "페이지 단독 판단 불가"


def test_an_unverified_case_never_yields_a_case_quote(custom_db, custom_risk_kinds_path):
    result = retrieve_reference_cases(
        [UNVERIFIED_CARD],
        {"product_type": "테스트유형3"},
        custom_db,
        risk_kinds_path=custom_risk_kinds_path,
        threshold=SYNTHETIC_THRESHOLD,
    )
    assert result["links"]
    link = next(link for link in result["links"] if link["case_id"] == "case.custom_unverified")
    assert link["case_quote"] == ""
    assert link["case_quote_note"] == "원문 재확인 필요"


# ---------------------------------------------------------------------------------------------
# rerank: reorders, never adds
# ---------------------------------------------------------------------------------------------


def test_rerank_only_reorders_and_never_adds_a_candidate(db_path, risk_kinds_path):
    without = retrieve_reference_cases(
        [RATE_CARD, BENEFIT_CARD],
        {"product_type": "신용카드"},
        db_path,
        risk_kinds_path=risk_kinds_path,
        threshold=0.0,
        rerank=False,
    )
    with_rerank = retrieve_reference_cases(
        [RATE_CARD, BENEFIT_CARD],
        {"product_type": "신용카드"},
        db_path,
        risk_kinds_path=risk_kinds_path,
        threshold=0.0,
        rerank=True,
        embed=FakeEmbed(),
    )
    ids_without = {link["case_id"] for link in without["links"]}
    ids_with = {link["case_id"] for link in with_rerank["links"]}
    assert ids_with == ids_without  # same set: rerank never adds or drops a candidate
    assert all(c["embedding"] is None for c in without["candidates"])
    reranked_ids = {c["case_id"] for c in with_rerank["candidates"] if c["case_id"] in ids_with}
    assert all(
        c["embedding"] is not None
        for c in with_rerank["candidates"]
        if c["case_id"] in reranked_ids
    )


# ---------------------------------------------------------------------------------------------
# determinism
# ---------------------------------------------------------------------------------------------


def test_output_is_deterministic(db_path, risk_kinds_path):
    first = retrieve_reference_cases(
        [RATE_CARD, LEGIBILITY_CARD],
        {"product_type": "리볼빙"},
        db_path,
        risk_kinds_path=risk_kinds_path,
    )
    second = retrieve_reference_cases(
        [RATE_CARD, LEGIBILITY_CARD],
        {"product_type": "리볼빙"},
        db_path,
        risk_kinds_path=risk_kinds_path,
    )
    assert first == second


# ---------------------------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------------------------


def test_compute_reference_metrics_scores_recall_false_links_and_partial_accuracy():
    gold = [
        {"expected_case_ids": ["case.a"], "expected_page_only_partial": False},
        {"expected_case_ids": ["case.b", "case.c"], "expected_page_only_partial": True},
        {"expected_case_ids": [], "expected_page_only_partial": False},
        {"expected_case_ids": ["case.d"], "expected_page_only_partial": True},
    ]
    results = [
        {"links": [{"case_id": "case.a", "page_only_detectability": "full"}]},
        {"links": [{"case_id": "case.b", "page_only_detectability": "partial"}]},  # misses case.c
        {"links": [{"case_id": "case.x", "page_only_detectability": "full"}]},  # a false link
        {
            "links": [{"case_id": "case.d", "page_only_detectability": "full"}]
        },  # wrong detectability
    ]
    metrics = compute_reference_metrics(gold, results)
    assert metrics["n"] == 4
    assert metrics["recall"] == round(3 / 4, 4)  # hit case.a, case.b, case.d of 4 expected
    assert metrics["false_link_rate"] == round(1 / 4, 4)  # 1 of 4 total links was wrong
    assert metrics["partial_accuracy"] == round(3 / 4, 4)  # entry 4's detectability disagrees


def test_compute_reference_metrics_handles_the_empty_case():
    metrics = compute_reference_metrics([], [])
    assert metrics == {"recall": 1.0, "false_link_rate": 0.0, "partial_accuracy": 1.0, "n": 0}


def test_compute_reference_metrics_requires_matching_lengths():
    with pytest.raises(ValueError, match="gold has"):
        compute_reference_metrics([{}], [])


# ---------------------------------------------------------------------------------------------
# synthetic set: a case paraphrase finds its own case, at SYNTHETIC_THRESHOLD
# ---------------------------------------------------------------------------------------------


def test_the_synthetic_set_reproduces_its_expected_links(db_path, risk_kinds_path):
    gold = json.loads(GOLD_PATH.read_text())
    entries = gold["entries"]
    results = [
        retrieve_reference_cases(
            [entry["card"]],
            entry["classification"],
            db_path,
            risk_kinds_path=risk_kinds_path,
            threshold=SYNTHETIC_THRESHOLD,
        )
        for entry in entries
    ]
    metrics = compute_reference_metrics(entries, results)
    assert metrics["recall"] == 1.0
    assert metrics["false_link_rate"] == 0.0


def test_a_db_without_case_tables_falls_back_to_the_checked_in_corpus(tmp_path, risk_kinds_path):
    """사례 테이블 빌드는 임베딩(유료)을 동반합니다. BM25는 원문만 있으면 되므로 DB가 비어 있어도
    검증된 코퍼스 yaml에서 바로 읽어 연결을 만듭니다."""
    result = retrieve_reference_cases(
        [RATE_CARD],
        {"product_type": "리볼빙"},
        tmp_path / "absent.sqlite",
        risk_kinds_path=risk_kinds_path,
        corpus_path=CORPUS / "case_corpus.yaml",
        threshold=SYNTHETIC_THRESHOLD,
    )
    assert result["method"]["cases_from"] == "corpus:case_corpus.yaml"
    assert [link["case_id"] for link in result["links"]] == ["case.test_revolving_min_rate"]
