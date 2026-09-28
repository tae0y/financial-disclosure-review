"""Joining snapshot rows to the LLM-facing html, and the compact line the model reads."""

from financial_disclosure_review.domain.display_check.blocks import (
    BLOCK_COLUMNS,
    compact_block,
    display_blocks,
    html_text_runs,
    page_images,
)
from tests.helpers import BENEFIT, FEE, NOTICE, TITLE, make_render_page


def test_html_text_runs_includes_single_nodes_and_short_runs():
    runs = html_text_runs("<p>가</p><p>나</p>")
    assert "가" in runs and "나" in runs and "가 나" in runs


def test_page_images_numbers_the_images_and_keeps_their_alt():
    images = page_images('<img alt="연체이자율 안내"><img>')
    assert images == [{"id": "img1", "alt": "연체이자율 안내"}, {"id": "img2", "alt": ""}]
    assert page_images(None) == []


def test_display_blocks_measures_every_matched_row():
    blocks, stats = display_blocks(make_render_page())
    texts = [block["text"] for block in blocks]
    assert texts == [TITLE, BENEFIT, NOTICE, FEE]
    assert [block["id"] for block in blocks] == ["b1", "b2", "b3", "b4"]
    title = blocks[0]
    assert title["px"] == 24.0 and title["pt"] == 18.0
    assert title["large_text"] is True
    assert title["contrast"] is not None and title["contrast"] > 4.5
    assert stats["states"] == 2 and stats["matched"] == 4


def test_a_row_revealed_later_is_marked_as_not_visible_by_default():
    blocks, _ = display_blocks(make_render_page())
    fee = next(block for block in blocks if block["text"] == FEE)
    assert fee["default_visible"] is False
    assert fee["ever_visible"] is True
    assert fee["revealed_by"] == "expand button.tab-toggle"


def test_a_marker_at_the_start_of_the_line_is_detected():
    blocks, _ = display_blocks(make_render_page())
    notice = next(block for block in blocks if block["text"] == NOTICE)
    assert notice["marker"] is True
    assert notice["own_line"] is True
    assert notice["line_sentences"] == 1


def test_rows_whose_text_is_not_in_the_html_are_dropped():
    page = make_render_page()
    page["snapshots"][0]["styles"].append(
        {
            **page["snapshots"][0]["styles"][0],
            "text": "이 글은 html에 없습니다",
            "path": "html > p:nth-of-type(9)",
        }
    )
    blocks, _ = display_blocks(page)
    assert all("html에 없습니다" not in block["text"] for block in blocks)


def test_compact_block_follows_the_column_order_the_prompt_states():
    blocks, _ = display_blocks(make_render_page())
    row = compact_block(blocks[2]).split("|")
    assert len(row) == len(BLOCK_COLUMNS.split("|"))
    assert row[0] == "b3" and row[1].startswith("※")
    assert row[2] == "12.0pt" and row[3] == "w400"
    assert row[7].startswith("MO") or "M" in row[7]


def test_a_block_that_was_never_visible_is_flagged_h():
    page = make_render_page()
    for snapshot in page["snapshots"]:
        for row in snapshot["styles"]:
            if row["text"] == FEE:
                row["visible"] = False
    blocks, _ = display_blocks(page)
    fee = next(block for block in blocks if block["text"] == FEE)
    assert fee["ever_visible"] is False
    assert "H" in compact_block(fee).split("|")[7]


def test_an_image_backed_block_reports_its_contrast_as_unknown():
    page = make_render_page()
    for snapshot in page["snapshots"]:
        for row in snapshot["styles"]:
            if row["text"] == NOTICE:
                row["visual_risk"] = ["background_image"]
    blocks, _ = display_blocks(page)
    notice = next(block for block in blocks if block["text"] == NOTICE)
    assert notice["visual_risk"] == ["background_image"]
    columns = compact_block(notice).split("|")
    assert columns[5] == "image-backed" and columns[6] == "crvision-unknown"


def test_text_set_below_one_pixel_is_unmeasured_not_zero_points():
    """An image-replaced heading keeps its words in the DOM at font-size 0; the reader sees the
    picture. Measuring it as 0pt would turn a technique into a size failure."""
    blocks, _ = display_blocks(make_render_page(notice_px=0.0))
    notice = next(block for block in blocks if block["text"] == NOTICE)
    assert notice["pt"] is None and notice["size_unmeasured"] is True
    assert "undrawn_text" in notice["visual_risk"]
    columns = compact_block(notice).split("|")
    assert columns[2] == "-" and columns[5] == "image-backed"
