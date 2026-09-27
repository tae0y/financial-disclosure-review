"""Where a rule is stored, whether a page still fits it, and what a replay must reach."""

from pathlib import Path

from financial_disclosure_review.domain.product_page.rules import (
    check_rule,
    load_rule,
    page_family,
    product_from,
    rule_path,
    save_rule,
    validate_output,
)
from tests.helpers import FIXTURE_DIR

HTML = (FIXTURE_DIR / "html" / "product_page.html").read_text()


def rule() -> dict:
    return {
        "version": 1,
        "product_name": "테스트 신용카드",
        "summary": "테스트용 신용카드입니다.",
        "name_selector": "h1.product-title",
        "include": ["article#product"],
        "exclude": ["aside.recommend"],
        "steps": [{"action": "expand", "selector": "button.tab-toggle"}],
        "landmarks": [
            {"selector": "article#product", "tag": "article", "role": ""},
            {"selector": "h1.product-title", "tag": "h1", "role": ""},
        ],
        "evidence": ["페이지 제목"],
        "counts": {"article#product": 1},
        "outside": [],
        "active_includes": ["article#product"],
        "content_chars": 240,
    }


def test_page_family_masks_the_product_slug_and_numeric_folders():
    assert page_family("https://a.test/card/1234/info/las-vegas") == "/card/#/info/*"
    assert page_family("https://a.test/card/view.html?id=7&brand=x") == "/card/*.html?brand,id"


def test_rule_path_names_the_file_after_host_family_and_viewport():
    path = rule_path(Path("/rules"), "https://a.test/card/las-vegas", "1280x800")
    assert path.name == "a.test__card__1280x800.json"
    assert path.parent == Path("/rules")


def test_saving_then_loading_a_rule_round_trips(tmp_path):
    path = tmp_path / "site_rules" / "a.json"
    assert load_rule(path) is None
    save_rule(path, rule())
    assert load_rule(path) == rule()


def test_check_rule_accepts_the_page_the_rule_was_built_on():
    assert check_rule(HTML, rule()) == []


def test_check_rule_rejects_an_include_that_no_longer_matches():
    broken = {**rule(), "include": ["article#gone"], "counts": {"article#gone": 1}}
    reasons = check_rule(HTML, broken)
    assert any("matches 0" in reason for reason in reasons)


def test_check_rule_rejects_a_missing_landmark_and_a_moved_product_name():
    broken = {
        **rule(),
        "landmarks": [{"selector": "article#product", "tag": "section", "role": ""}],
        "product_name": "다른 카드",
    }
    reasons = check_rule(HTML, broken)
    assert any("landmark" in reason for reason in reasons)
    assert any("product name" in reason for reason in reasons)
    assert any("at least" not in reason for reason in reasons)


def test_check_rule_refuses_a_rule_with_no_stored_outside_signature():
    without = {k: v for k, v in rule().items() if k != "outside"}
    assert any("outside-content signature" in reason for reason in check_rule(HTML, without))


def content(chars: int = 240) -> dict:
    return {
        "pieces": [{"selector": "article#product", "text": "테스트 신용카드 " + "가" * chars}],
        "html": "<section>x</section>",
        "steps": [
            {"action": "expand", "selector": "button.tab-toggle", "matched": 1, "clicked": 1}
        ],
        "name_text": "테스트 신용카드",
        "states": 2,
    }


def test_validate_output_accepts_a_replay_that_reached_the_stored_content():
    assert validate_output(rule(), content()) == []


def test_validate_output_rejects_content_that_shrank_by_half():
    assert any("shrank" in error for error in validate_output(rule(), content(chars=20)))


def test_validate_output_rejects_an_include_that_contributed_nothing():
    empty = {**content(), "pieces": []}
    errors = validate_output(rule(), empty)
    assert any("contributed no text" in error for error in errors)
    assert any("product name missing" not in error for error in errors)


def test_validate_output_rejects_an_expand_step_that_clicked_nothing():
    stuck = {**content()}
    stuck["steps"] = [
        {
            "action": "expand",
            "selector": "button.tab-toggle",
            "matched": 3,
            "clicked": 0,
            "skipped": [],
        }
    ]
    assert any("clicked nothing" in error for error in validate_output(rule(), stuck))


def test_product_from_carries_only_the_product_identity():
    assert product_from(rule(), content()) == {
        "product_name": "테스트 신용카드",
        "summary": "테스트용 신용카드입니다.",
        "evidence": ["페이지 제목"],
    }
