"""Building a reference DB from the fixture rubric, then reading it back."""

import pytest

from financial_disclosure_review.knowledge.build import build_rubric_db, rubric_schema_problems
from financial_disclosure_review.knowledge.rubrics import item_scope, load_rubric
from tests.helpers import FIXTURE_DIR


@pytest.fixture(scope="module")
def db_path(tmp_path_factory) -> str:
    path = tmp_path_factory.mktemp("reference") / "reference.sqlite"
    counts = build_rubric_db(FIXTURE_DIR / "rubric", path)
    assert counts == {"card_guardrail_rubric": 3, "plain_service_rubric": 1}
    return str(path)


def test_items_come_back_in_yaml_order_with_their_lists(db_path):
    items = load_rubric(db_path, "card_guardrail_rubric")
    assert [i["code"] for i in items] == ["A01", "E02", "E04"]
    assert items[0]["applies_to"] == ["신용카드", "리볼빙"]
    assert items[0]["page_types"] == ["상품광고", "업무광고"]
    assert items[0]["sources"][0]["doc"] == "kfcpa"
    assert items[0]["binding"] == "법령"


def test_the_screen_field_keeps_the_name_the_yaml_used(db_path):
    plain = load_rubric(db_path, "plain_service_rubric")
    assert plain[0]["targets"] == ["설명화면"]
    assert "page_types" not in plain[0]


def test_a_group_prefix_narrows_the_items(db_path):
    display = load_rubric(db_path, "card_guardrail_rubric", ("E.",))
    assert [i["code"] for i in display] == ["E02", "E04"]


def test_item_scope_is_empty_only_when_both_types_match(db_path):
    items = {i["code"]: i for i in load_rubric(db_path, "card_guardrail_rubric")}
    revolving = {"product_type": "리볼빙", "page_type": "업무광고"}
    assert item_scope(items["E02"], revolving) == ""
    assert "applies_to" in item_scope(items["E04"], revolving)
    assert "page_types" in item_scope(
        items["A01"], {"product_type": "리볼빙", "page_type": "설명화면"}
    )


def test_a_missing_db_names_the_build_command(tmp_path):
    with pytest.raises(FileNotFoundError, match="build-db"):
        load_rubric(tmp_path / "absent.sqlite", "card_guardrail_rubric")


def test_the_schema_check_reports_a_missing_field():
    item = {"code": "X01", "group": "E. 표시방법"}
    problems = rubric_schema_problems([item], "page_types")
    assert problems and "missing" in problems[0]
