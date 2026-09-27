"""The live session against a locally rendered page. Opens a browser, reaches no network."""

import pytest
from playwright.sync_api import sync_playwright

from financial_disclosure_review.core.context import Context
from financial_disclosure_review.product_page.session import (
    PageSession,
    bounds_overlap,
    reject_reason,
)
from tests.helpers import FIXTURE_DIR

HTML = (FIXTURE_DIR / "html" / "product_page.html").read_text()


@pytest.fixture
def session(tmp_path):
    ctx = Context(data_dir=str(tmp_path))
    with sync_playwright() as playwright:
        sess = PageSession(playwright, "https://example.test/product", ctx)
        try:
            sess.page.set_content(HTML)
            sess.phase = "render"
            yield sess
        finally:
            sess.close()


def test_bounds_overlap_only_when_both_axes_overlap():
    assert bounds_overlap([0, 0, 10, 10], [5, 5, 10, 10])
    assert not bounds_overlap([0, 0, 10, 10], [5, 20, 10, 10])
    assert not bounds_overlap([0, 0, 10, 10], [10, 0, 10, 10])


@pytest.mark.parametrize(
    "info, expected",
    [
        (
            {
                "href": "",
                "tag": "button",
                "type": "",
                "cls": "",
                "expandable": True,
                "in_form": False,
                "text": "열기",
                "visible": True,
            },
            "",
        ),
        (
            {
                "href": "",
                "tag": "input",
                "type": "",
                "cls": "",
                "expandable": False,
                "in_form": False,
                "text": "",
                "visible": True,
            },
            "form control",
        ),
        (
            {
                "href": "",
                "tag": "button",
                "type": "submit",
                "cls": "",
                "expandable": True,
                "in_form": False,
                "text": "",
                "visible": True,
            },
            "form control",
        ),
        (
            {
                "href": "",
                "tag": "button",
                "type": "",
                "cls": "",
                "expandable": True,
                "in_form": False,
                "text": "카드 신청하기",
                "visible": True,
            },
            "apply/login/submit/download wording",
        ),
        (
            {
                "href": "/other",
                "tag": "a",
                "type": "",
                "cls": "",
                "expandable": False,
                "in_form": False,
                "text": "다음",
                "visible": True,
            },
            "navigation link (use open_link)",
        ),
        (
            {
                "href": "",
                "tag": "span",
                "type": "",
                "cls": "plain",
                "expandable": False,
                "in_form": False,
                "text": "",
                "visible": True,
            },
            "not an expander",
        ),
        (
            {
                "href": "#",
                "tag": "a",
                "type": "",
                "cls": "",
                "expandable": False,
                "in_form": False,
                "text": "열기",
                "visible": False,
            },
            "not visible",
        ),
    ],
)
def test_reject_reason_allows_only_safe_expanders(info, expected):
    assert reject_reason(info) == expected


def test_match_count_reports_matches_and_selector_errors(session):
    assert session.match_count("article#product")[0] == 1
    count, problem = session.match_count("article#(")
    assert count == 0 and problem


def test_the_snapshot_reads_styles_bounds_and_the_page_html(session, tmp_path):
    entry = session.snapshot("default", "test")
    assert entry["id"] == 1 and entry["phase"] == "render"
    assert entry["viewport"] == {"width": 1280, "height": 800}
    rows = {row["text"]: row for row in entry["styles"] if row["text"]}
    title = next(row for text, row in rows.items() if "테스트 신용카드" in text)
    assert title["font_size"].endswith("px")
    assert title["visible"] is True
    assert title["path"].startswith("html >")
    assert title["background"] is not None
    assert title["visual_risk"] == []
    assert (tmp_path / "snapshots").is_dir()
    assert "테스트 신용카드" in entry["html_path"] or entry["html_path"].endswith(".html")


def test_a_hidden_panel_is_not_visible_until_the_tab_is_clicked(session):
    before = session.snapshot("default", "before")
    hidden = [r for r in before["styles"] if "연회비는 국내 전용" in r["text"]]
    assert hidden and not hidden[0]["visible"]

    report = session.click_matches("button.tab-toggle", "explore")
    assert report["matched"] == 1 and report["clicked"] == 1
    session.page.evaluate("document.getElementById('panel-fee').removeAttribute('hidden')")
    after = session.snapshot("expanded", "after")
    revealed = [r for r in after["styles"] if "연회비는 국내 전용" in r["text"]]
    assert revealed and revealed[0]["visible"]


def test_click_matches_skips_an_apply_button(session):
    session.page.evaluate(
        "document.querySelector('.tab-wrap').insertAdjacentHTML('beforeend',"
        " '<button class=\"toggle\">카드 신청하기</button>')"
    )
    report = session.click_matches("button.toggle", "explore")
    assert report["clicked"] == 0
    assert report["skipped"][0]["reason"] == "apply/login/submit/download wording"


def test_snapshot_if_changed_returns_none_when_the_text_did_not_change(session):
    session.snapshot("default", "first")
    assert session.snapshot_if_changed("explore", "same") is None


def test_the_selected_view_is_captured_as_a_state(session):
    session.view = (["article#product"], ["aside.recommend"])
    session.snapshot("default", "with a view")
    assert len(session.states) == 1
    assert "커피 전문점" in session.states[0][0]["text"]
