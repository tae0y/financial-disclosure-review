"""Page chrome detection, region extraction, selector building and the page outline."""

from bs4 import BeautifulSoup

from financial_disclosure_review.product_page.html import (
    clean_html,
    extract_pieces,
    in_chrome,
    merge_pieces,
    outline_page,
    outside_blocks,
    outside_signature,
    selector_for,
    valid_ident,
)
from tests.helpers import FIXTURE_DIR

HTML = (FIXTURE_DIR / "html" / "product_page.html").read_text()
INCLUDE = ["article#product"]
EXCLUDE = ["aside.recommend"]


def test_valid_ident_accepts_css_identifiers_only():
    assert valid_ident("panel-fee")
    assert not valid_ident("1panel")
    assert not valid_ident("panel fee")


def test_selector_for_prefers_an_id_then_classes():
    soup = BeautifulSoup(HTML, "html.parser")
    assert selector_for(soup.select_one("#panel-fee"), soup) == "#panel-fee"
    assert selector_for(soup.select_one("h1"), soup) == "h1.product-title"


def test_selector_for_falls_back_to_an_nth_of_type_path():
    soup = BeautifulSoup("<div><span>a</span><span>b</span></div>", "html.parser")
    selector = selector_for(soup.find_all("span")[1], soup)
    assert selector.endswith("span:nth-of-type(2)")


def test_in_chrome_marks_header_nav_and_footer_but_not_the_article():
    soup = BeautifulSoup(HTML, "html.parser")
    assert in_chrome(soup.select_one("header a"))
    assert in_chrome(soup.select_one("footer p"))
    assert not in_chrome(soup.select_one("section.benefit p"))


def test_clean_html_drops_scripts_and_styling_attributes():
    cleaned = clean_html(
        BeautifulSoup(
            '<div style="color:red" class="x" role="note"><script>a()</script><p>본문</p></div>',
            "html.parser",
        )
    )
    assert "script" not in cleaned
    assert "style=" not in cleaned and 'class="x"' not in cleaned
    assert 'role="note"' in cleaned and "본문" in cleaned


def test_extract_pieces_keeps_the_included_region_and_drops_the_excluded_one():
    pieces = extract_pieces(HTML, INCLUDE, EXCLUDE)
    assert len(pieces) == 1
    assert "커피 전문점" in pieces[0]["text"]
    assert "추천 상품" not in pieces[0]["text"]


def test_merge_pieces_keeps_the_first_appearance_of_each_text():
    states = [
        [{"selector": "a", "text": "같은 글", "html": "<p>같은 글</p>"}],
        [
            {"selector": "a", "text": "같은  글", "html": "<p>같은 글</p>"},
            {"selector": "b", "text": "새 글", "html": "<p>새 글</p>"},
        ],
    ]
    kept, html = merge_pieces(states)
    assert [piece["text"] for piece in kept] == ["같은 글", "새 글"]
    assert [piece["state"] for piece in kept] == [0, 1]
    assert html.count("<section") == 2


def test_outside_blocks_ignores_page_chrome_and_popup_layers():
    left = [text for _, text in outside_blocks(HTML, INCLUDE, EXCLUDE)]
    assert not any("전역 내비게이션" in text for text in left)
    assert not any("쿠키 사용" in text for text in left)
    assert not any("회사 정보" in text for text in left)


def test_the_outside_signature_is_a_sorted_list_of_structural_paths():
    signature = outside_signature(HTML, INCLUDE, EXCLUDE)
    assert signature == sorted(signature)
    assert all(">" in path or path for path in signature)


def test_outline_page_reports_the_title_headings_regions_links_and_controls():
    outline = outline_page(HTML)
    assert outline["title"] == "테스트카드 상품안내"
    assert "테스트 신용카드" in [h["text"] for h in outline["headings"]]
    selectors = [region["selector"] for region in outline["regions"]]
    assert "#product" in selectors and "section.terms" in selectors
    assert any(link["href"] == "/home" for link in outline["links"])
    assert any(control["controls"] == "panel-fee" for control in outline["controls"])


def test_outline_page_marks_chrome_links_and_sorts_them_last():
    outline = outline_page(HTML)
    assert any(link["chrome"] for link in outline["links"])
    assert [link["chrome"] for link in outline["links"]] == sorted(
        link["chrome"] for link in outline["links"]
    )
