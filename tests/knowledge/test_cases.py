"""Building the case tables from the fixture corpus, reading them back, and searching them.

Every test here is free: the embedding call is a FakeEmbed, the way the rubric tests use a fake
ask. The real embedding model is only exercised by the `use_llm` test at the bottom.
"""

import pytest
import yaml

from financial_disclosure_review.knowledge.build_cases import (
    build_case_db,
    case_db_counts,
    case_schema_problems,
    embed_text_of,
)
from financial_disclosure_review.knowledge.cases import case_summary, load_cases
from financial_disclosure_review.knowledge.search import case_queries, search, search_cases_for
from tests.helpers import EMBED_VOCAB, FIXTURE_DIR, FakeEmbed

CORPUS = FIXTURE_DIR / "cases"


@pytest.fixture(scope="module")
def db_path(tmp_path_factory) -> str:
    path = tmp_path_factory.mktemp("cases") / "reference.sqlite"
    counts = build_case_db(CORPUS, path, embed=FakeEmbed(), dimensions=len(EMBED_VOCAB))
    assert counts == {
        "cases": 4,
        "product_types": 5,
        "checklist_codes": 9,
        "dimensions": len(EMBED_VOCAB),
    }
    return str(path)


def test_the_build_fills_every_case_table(db_path):
    assert case_db_counts(db_path) == {
        "cases": 4,
        "case_product_types": 5,
        "case_checklist": 9,
        "case_vectors": 4,
    }


def test_cases_come_back_in_yaml_order_with_their_lists(db_path):
    cases = load_cases(db_path)
    assert [c["case_id"] for c in cases] == [
        "case.test_revolving_min_rate",
        "case.test_revolving_legibility",
        "case.test_card_benefit_condition",
        "case.test_loan_eligibility",
    ]
    assert cases[1]["product_types"] == ["리볼빙", "신용카드"]
    assert cases[2]["related_checklist"] == ["A10", "D06", "쉬운말07"]
    assert cases[0]["source_tier"] == 1
    assert cases[3]["product_basis"] == "유추"


def test_a_product_type_narrows_the_cases(db_path):
    revolving = load_cases(db_path, product_types=("리볼빙",))
    assert [c["case_id"] for c in revolving] == [
        "case.test_revolving_min_rate",
        "case.test_revolving_legibility",
    ]
    assert load_cases(db_path, product_types=("할부금융·리스",)) == []


def test_a_checklist_code_narrows_the_cases(db_path):
    assert [c["case_id"] for c in load_cases(db_path, codes=("표시04",))] == [
        "case.test_revolving_legibility"
    ]
    both = load_cases(db_path, product_types=("신용카드",), codes=("A10",))
    assert [c["case_id"] for c in both] == ["case.test_card_benefit_condition"]


def test_search_puts_the_case_about_the_query_first(db_path):
    hits = search(db_path, "글자 크기와 색상 표시", k=4, embed=FakeEmbed())
    assert hits[0]["case_id"] == "case.test_revolving_legibility"
    assert hits[0]["similarity"] > hits[-1]["similarity"]
    assert hits[0]["official_primary_url"] == "https://example.test/revolving-legibility"
    assert hits[0]["related_checklist"] == ["표시04", "표시06"]
    assert hits[0]["issue"] and hits[0]["outcome"]


def test_search_keeps_only_the_given_product_type(db_path):
    hits = search(db_path, "대출 자격 누구나", kind="장기카드대출", k=4, embed=FakeEmbed())
    assert [h["case_id"] for h in hits] == ["case.test_loan_eligibility"]


def test_search_returns_at_most_k(db_path):
    assert len(search(db_path, "이자율", k=2, embed=FakeEmbed())) == 2


def test_an_empty_query_costs_nothing(db_path):
    fake = FakeEmbed()
    assert search(db_path, "   ", embed=fake) == []
    assert search(db_path, "이자율", k=0, embed=fake) == []
    assert fake.batches == []


def test_a_missing_db_names_the_build_command(tmp_path):
    with pytest.raises(FileNotFoundError, match="build-cases"):
        search(tmp_path / "absent.sqlite", "이자율", embed=FakeEmbed())
    with pytest.raises(FileNotFoundError, match="build-cases"):
        load_cases(tmp_path / "absent.sqlite")


def test_a_db_without_case_tables_names_the_build_command(tmp_path):
    from financial_disclosure_review.knowledge.build import build_rubric_db

    path = tmp_path / "rubric-only.sqlite"
    build_rubric_db(FIXTURE_DIR / "rubric", path)
    with pytest.raises(RuntimeError, match="build-cases"):
        load_cases(path)


def test_case_queries_name_the_product_and_one_area_each():
    queries = case_queries({"product_type": "리볼빙"}, {"product_name": "테스트 리볼빙 서비스"})
    assert [q["area"] for q in queries] == ["의무표시", "표시방법", "금지행위", "설명의무"]
    assert all(q["text"].startswith("리볼빙 테스트 리볼빙 서비스") for q in queries)


def test_search_cases_for_merges_the_areas_and_embeds_once(db_path):
    fake = FakeEmbed()
    result = search_cases_for(
        {"product_name": "테스트 리볼빙"}, {"product_type": "리볼빙"}, db_path, k=2, embed=fake
    )
    assert result["status"] == "완료"
    assert len(fake.batches) == 1 and len(fake.batches[0]) == 4
    ids = [h["case_id"] for h in result["hits"]]
    assert set(ids) == {"case.test_revolving_min_rate", "case.test_revolving_legibility"}
    assert all(h["product_types"] and "리볼빙" in h["product_types"] for h in result["hits"])
    by_id = {h["case_id"]: h for h in result["hits"]}
    assert "표시방법" in by_id["case.test_revolving_legibility"]["areas"]
    distances = [h["distance"] for h in result["hits"]]
    assert distances == sorted(distances)


def test_search_cases_for_reports_a_product_type_with_no_cases(db_path):
    result = search_cases_for(
        {"product_name": "테스트 리스"},
        {"product_type": "할부금융·리스"},
        db_path,
        embed=FakeEmbed(),
    )
    assert result["hits"] == []
    assert result["status"] == "해당 사례 없음"
    assert "할부금융·리스" in result["reason"]


def test_search_cases_for_survives_a_missing_db(tmp_path):
    result = search_cases_for(
        {"product_name": "x"},
        {"product_type": "리볼빙"},
        tmp_path / "absent.sqlite",
        embed=FakeEmbed(),
    )
    assert result["hits"] == [] and result["status"] == "판정 불가"
    assert "build-cases" in result["reason"]


def test_the_schema_check_reports_a_missing_field():
    problems = case_schema_problems([{"case_id": "case.x", "record_type": "지적사례"}])
    assert problems and any("missing" in p for p in problems)


@pytest.mark.parametrize(
    "change, expected",
    [
        ({"record_type": "참고"}, "record_type"),
        ({"product_basis": "추정"}, "product_basis"),
        ({"page_only_detectability": "maybe"}, "page_only_detectability"),
        ({"official_primary_url": "http://example.test/x"}, "official_primary_url"),
        ({"official_primary_url": None}, "official_primary_url"),
        ({"text": "   "}, "text is empty"),
        ({"text_sha256": "not-a-sha"}, "text_sha256"),
        ({"product_types": []}, "product_types"),
        ({"source_tier": "1"}, "source_tier"),
    ],
)
def test_the_schema_check_rejects_a_bad_value(change, expected):
    item = {**yaml.safe_load((CORPUS / "case_corpus.yaml").read_text())["items"][0], **change}
    problems = case_schema_problems([item])
    assert any(expected in p for p in problems), problems


def test_a_good_corpus_has_no_problems():
    items = yaml.safe_load((CORPUS / "case_corpus.yaml").read_text())["items"]
    assert case_schema_problems(items) == []


def test_a_duplicate_case_id_is_reported():
    items = yaml.safe_load((CORPUS / "case_corpus.yaml").read_text())["items"]
    problems = case_schema_problems([items[0], dict(items[0])])
    assert any("appears 2 times" in p for p in problems)


def test_a_bad_corpus_leaves_the_previous_db_untouched(tmp_path):
    path = tmp_path / "reference.sqlite"
    build_case_db(CORPUS, path, embed=FakeEmbed(), dimensions=len(EMBED_VOCAB))
    before = case_db_counts(path)
    bad = tmp_path / "bad"
    bad.mkdir()
    items = yaml.safe_load((CORPUS / "case_corpus.yaml").read_text())["items"]
    items[0]["record_type"] = "참고"
    (bad / "case_corpus.yaml").write_text(yaml.safe_dump({"items": items}, allow_unicode=True))
    with pytest.raises(ValueError, match="record_type"):
        build_case_db(bad, path, embed=FakeEmbed(), dimensions=len(EMBED_VOCAB))
    assert case_db_counts(path) == before


def test_a_wrong_width_vector_is_refused(tmp_path):
    with pytest.raises(RuntimeError, match="numbers wide"):
        build_case_db(
            CORPUS,
            tmp_path / "reference.sqlite",
            embed=lambda texts: [[0.1, 0.2] for _ in texts],
            dimensions=len(EMBED_VOCAB),
        )


def test_the_build_is_safe_to_re_run(tmp_path):
    path = tmp_path / "reference.sqlite"
    first = build_case_db(CORPUS, path, embed=FakeEmbed(), dimensions=len(EMBED_VOCAB))
    second = build_case_db(CORPUS, path, embed=FakeEmbed(), dimensions=len(EMBED_VOCAB))
    assert first == second
    assert case_db_counts(path)["cases"] == 4


def test_the_embedded_text_carries_the_fields_a_query_is_about():
    item = yaml.safe_load((CORPUS / "case_corpus.yaml").read_text())["items"][0]
    text = embed_text_of(item)
    assert "리볼빙" in text and "C03" in text
    assert item["issue"] in text and item["mvp_signal"] in text
    assert item["case_id"] not in text  # bookkeeping fields stay out of the vector


def test_a_case_text_hash_is_preserved_and_must_match_the_embedded_excerpt(db_path):
    case = load_cases(db_path)[0]
    assert len(case["text_sha256"]) == 64
    assert (
        case["text_sha256"]
        == yaml.safe_load((CORPUS / "case_corpus.yaml").read_text())["items"][0]["text_sha256"]
    )


def test_case_summary_names_the_institution_and_the_issue():
    case = {
        "case_id": "case.x",
        "institution": "금융감독원",
        "official_date": "2024-02-26",
        "record_type": "지적사례",
        "issue": "무엇이 문제였는지",
    }
    line = case_summary(case)
    assert "case.x" in line and "금융감독원" in line and "무엇이 문제였는지" in line


@pytest.mark.use_llm
def test_the_real_corpus_builds_and_searches_with_the_real_model(tmp_path):
    """Costs money. Builds the project's own case corpus and checks a query lands sensibly."""
    from financial_disclosure_review.core.context import default_rubric_dir

    path = tmp_path / "reference.sqlite"
    counts = build_case_db(default_rubric_dir(), path)
    assert counts["cases"] >= 19
    assert counts["dimensions"] == 1536
    hits = search(path, "리볼빙 최소이자율만 표기하고 평균이자율을 알리지 않음", kind="리볼빙", k=3)
    assert hits and hits[0]["similarity"] > 0.3
    assert all(h["official_primary_url"].startswith("https://") for h in hits)
