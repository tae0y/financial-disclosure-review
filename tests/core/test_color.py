"""Computed CSS colour parsing and the WCAG contrast ratio."""

import pytest

from financial_disclosure_review.core.color import (
    contrast_ratio,
    parse_color,
    relative_luminance,
)


@pytest.mark.parametrize(
    "value, expected",
    [
        ("rgb(255, 255, 255)", (255, 255, 255, 1.0)),
        ("rgba(0, 0, 0, 0.5)", (0, 0, 0, 0.5)),
        ("color(srgb 1 0 0)", (255, 0, 0, 1.0)),
    ],
)
def test_parse_color_reads_the_formats_chromium_computes(value, expected):
    parsed = parse_color(value)
    assert parsed is not None
    assert tuple(round(c, 3) for c in parsed) == expected


def test_parse_color_returns_none_for_what_it_cannot_read():
    assert parse_color(None) is None
    assert parse_color("") is None
    assert parse_color("#ffffff") is None
    assert parse_color("color(display-p3 1 0 0)") is None


def test_oklch_lands_near_the_same_place_as_its_rgb_equivalent():
    white = parse_color("oklch(1 0 0)")
    assert white is not None
    assert all(c > 250 for c in white[:3])


def test_relative_luminance_runs_from_black_to_white():
    assert relative_luminance((0, 0, 0)) == 0
    assert relative_luminance((255, 255, 255)) == pytest.approx(1.0)


def test_contrast_ratio_of_black_on_white_is_the_wcag_maximum():
    assert contrast_ratio("rgb(0, 0, 0)", "rgb(255, 255, 255)") == 21.0


def test_contrast_ratio_is_symmetric_and_never_below_one():
    assert contrast_ratio("rgb(119, 119, 119)", "rgb(255, 255, 255)") == contrast_ratio(
        "rgb(255, 255, 255)", "rgb(119, 119, 119)"
    )
    assert contrast_ratio("rgb(10, 10, 10)", "rgb(10, 10, 10)") == 1.0


def test_a_translucent_background_is_composited_over_white():
    assert contrast_ratio("rgb(0, 0, 0)", "rgba(0, 0, 0, 0)") == 21.0


def test_contrast_ratio_is_none_when_either_colour_is_unreadable():
    assert contrast_ratio("#000", "rgb(255, 255, 255)") is None
    assert contrast_ratio("rgb(0, 0, 0)", None) is None
