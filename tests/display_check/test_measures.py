"""The numbers the model is given but never computes itself."""

from financial_disclosure_review.display_check.blocks import display_blocks
from financial_disclosure_review.display_check.measures import (
    baseline_style,
    display_measures,
    group_measures,
    item_blocks,
)
from tests.helpers import BENEFIT, FEE, NOTICE, TITLE, make_render_page


def measured(notice_px: float = 16.0):
    blocks, mapping = display_blocks(make_render_page(notice_px))
    by_text = {block["text"]: block["id"] for block in blocks}
    labels = {
        "mandatory": [by_text[NOTICE]],
        "warnings": [by_text[NOTICE]],
        "rates": [],
        "benefits": [by_text[BENEFIT]],
        "penalties": [by_text[FEE]],
        "image_disclosure": [],
        "note": "",
    }
    return blocks, mapping, labels, by_text


def test_the_baseline_is_the_commonest_style_by_characters_of_visible_text():
    blocks, _, _, _ = measured()
    assert baseline_style(blocks) == {
        "weight": 400,
        "color": "rgb(17, 17, 17)",
        "background": "rgb(255, 255, 255)",
    }


def test_group_measures_reports_the_smallest_size_and_nothing_below_the_threshold():
    blocks, _, labels, by_text = measured()
    stats = group_measures(blocks, labels["mandatory"], 9.0)
    assert stats["blocks"] == 1 and stats["measured"] == 1
    assert stats["min_pt"] == 12.0 and stats["max_pt"] == 12.0
    assert stats["min_pt_block"] == by_text[NOTICE]
    assert stats["below_min_pt"] == []
    assert stats["below_contrast_min"] == []
    assert stats["visual_unresolved"] == []


def test_group_measures_names_the_blocks_under_the_size_threshold():
    blocks, _, labels, by_text = measured(notice_px=10.0)
    stats = group_measures(blocks, labels["mandatory"], 9.0)
    assert stats["min_pt"] == 7.5
    assert stats["below_min_pt"] == [by_text[NOTICE]]


def test_group_measures_names_the_blocks_under_the_contrast_threshold():
    page = make_render_page()
    for snapshot in page["snapshots"]:
        for row in snapshot["styles"]:
            if row["text"] == NOTICE:
                row["color"] = "rgb(200, 200, 200)"
    blocks, _ = display_blocks(page)
    notice = next(block for block in blocks if block["text"] == NOTICE)
    stats = group_measures(blocks, [notice["id"]], 9.0)
    assert stats["below_contrast_min"] == [notice["id"]]
    assert stats["min_contrast"] is not None and stats["min_contrast"] < 4.5


def test_an_image_backed_block_is_unresolved_rather_than_a_contrast_failure():
    page = make_render_page()
    for snapshot in page["snapshots"]:
        for row in snapshot["styles"]:
            if row["text"] == NOTICE:
                row["color"], row["visual_risk"] = "rgb(200, 200, 200)", ["background_image"]
    blocks, _ = display_blocks(page)
    notice = next(block for block in blocks if block["text"] == NOTICE)
    stats = group_measures(blocks, [notice["id"]], 9.0)
    assert stats["below_contrast_min"] == []
    assert stats["visual_unresolved"] == [notice["id"]]
    assert stats["dom_below_contrast_min"] == [notice["id"]]
    assert notice["id"] in stats["contrast_unmeasured"]


def test_display_measures_fills_one_entry_per_rubric_item():
    blocks, mapping, labels, by_text = measured()
    measures = display_measures(blocks, labels, 9.0, [by_text[FEE]], mapping, [{"type": "reuse"}])
    assert set(measures) >= {"baseline", "E01", "E02", "E03", "E04", "E05", "E06", "E07", "E08"}
    assert measures["E01"]["benefits"]["min_pt"] == 13.5
    assert measures["E06"]["with_marker"] == 1
    assert measures["E06"]["alone_on_line"] == 1
    assert measures["E06"]["unseparated"] == []
    assert measures["E07"]["hidden_total"] == 1
    assert measures["E07"]["action_log"] == {"reuse": 1}
    assert measures["E07"]["revealed_by_action"][0]["id"] == by_text[FEE]


def test_e03_reports_whether_warnings_stand_out_from_the_baseline():
    blocks, mapping, labels, _ = measured()
    measures = display_measures(blocks, labels, 9.0, [], mapping, [])
    set_off = measures["E03"]["set_off"]
    assert [row["bolder"] for row in set_off] == [False]
    assert [row["other_background"] for row in set_off] == [False]


def test_item_blocks_shows_only_the_groups_an_item_needs():
    blocks, _, labels, by_text = measured()
    e01 = [block["id"] for block in item_blocks("E01", blocks, labels, [])]
    assert e01 == [by_text[BENEFIT], by_text[FEE]]
    e04 = [block["id"] for block in item_blocks("E04", blocks, labels, [])]
    assert e04 == [by_text[NOTICE]]


def test_item_blocks_for_e07_leads_with_the_labeled_hidden_blocks():
    blocks, _, labels, by_text = measured()
    hidden = [by_text[FEE]]
    labels = {**labels, "penalties": hidden}
    ids = [block["id"] for block in item_blocks("E07", blocks, labels, hidden)]
    assert ids[0] == by_text[FEE]
    assert TITLE not in ids
