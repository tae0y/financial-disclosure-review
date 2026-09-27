"""norm, digest, short, visible_text, html_lines and the whitespace-insensitive quote lookup."""

from financial_disclosure_review.core.text import (
    digest,
    html_lines,
    locate_quote,
    norm,
    quote_percent,
    short,
    visible_text,
)


def test_norm_collapses_whitespace_and_lowers_case():
    assert norm("  Hello   World \n") == "hello world"
    assert norm("") == ""


def test_digest_ignores_whitespace_and_case():
    assert digest("Hello World") == digest("  hello \n world ")
    assert digest("a") != digest("b")
    assert len(digest("a")) == 12


def test_short_cuts_long_values_and_json_encodes_others():
    assert short("abc", 10) == "abc"
    assert short("abcdef", 3) == "abc…"
    assert short({"ko": "가"}) == '{"ko": "가"}'


def test_visible_text_drops_script_and_style():
    html = "<p>보이는 글</p><script>hidden()</script><style>p{}</style>"
    assert visible_text(html) == "보이는 글"


def test_html_lines_splits_at_block_elements():
    assert html_lines("<p>첫 줄</p><p>둘째 줄<br>셋째 줄</p>") == ["첫 줄", "둘째 줄", "셋째 줄"]


def test_locate_quote_finds_a_quote_whose_whitespace_differs():
    text = "연체 시 신용평점이 하락할 수 있습니다"
    assert locate_quote(text, "신용평점이  하락할") is not None
    located = locate_quote(text, "신용평점이 하락할")
    assert located is not None
    start, end = located
    assert text[start:end] == "신용평점이 하락할"


def test_locate_quote_returns_none_for_text_that_is_not_there():
    assert locate_quote("가나다", "라마바") is None
    assert locate_quote("가나다", "") is None


def test_quote_percent_reports_where_the_quote_sits():
    assert quote_percent("abcdefghij", "a") == "0%"
    assert quote_percent("abcdefghij", "z") == "없음"
