"""Computed CSS colors and WCAG contrast. Used by product_page capture and display_check."""

import math
import re


def oklab_to_srgb(lightness: float, a: float, b: float) -> tuple[float, float, float]:
    l_ = (lightness + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (lightness - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (lightness - 0.0894841775 * a - 1.2914855480 * b) ** 3
    linear = (
        4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
        -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
        -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_,
    )
    red, green, blue = (
        255 * (12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055)
        for c in (min(1.0, max(0.0, c)) for c in linear)
    )
    return red, green, blue


def parse_color(value: str | None) -> tuple[float, float, float, float] | None:
    """Computed CSS color -> (r, g, b, alpha) with r, g, b in 0-255. None for unknown formats."""
    if not value:
        return None
    match = re.fullmatch(r"\s*(rgba?|oklch|oklab|color)\(([^)]*)\)\s*", value.lower())
    if not match:
        return None
    kind, body = match.groups()
    parts = [p for p in re.split(r"[\s,/]+", body.strip()) if p]
    if kind == "color":
        if not parts or parts[0] != "srgb":
            return None
        parts = parts[1:]

    def number(text: str, percent_scale: float = 1.0) -> float:
        return float(text[:-1]) / 100 * percent_scale if text.endswith("%") else float(text)

    try:
        if kind in ("rgb", "rgba"):
            rgb = [number(p, 255) for p in parts[:3]]
            alpha = number(parts[3]) if len(parts) > 3 else 1.0
        elif kind == "color":
            rgb = [number(p) * 255 for p in parts[:3]]
            alpha = number(parts[3]) if len(parts) > 3 else 1.0
        else:
            lightness = number(parts[0])
            alpha = number(parts[3]) if len(parts) > 3 else 1.0
            if kind == "oklch":
                chroma = number(parts[1], 0.4)
                hue = math.radians(float(parts[2].removesuffix("deg")))
                a, b = chroma * math.cos(hue), chroma * math.sin(hue)
            else:
                a, b = number(parts[1], 0.4), number(parts[2], 0.4)
            rgb = list(oklab_to_srgb(lightness, a, b))
    except (ValueError, IndexError):
        return None
    red, green, blue = rgb
    return red, green, blue, alpha


def relative_luminance(rgb: tuple[float, float, float]) -> float:
    def linear(channel: float) -> float:
        c = channel / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(text_color: str | None, background: str | None) -> float | None:
    """WCAG 2.x contrast ratio. Translucent colors are composited over white, the page canvas."""
    fg, bg = parse_color(text_color), parse_color(background)
    if fg is None or bg is None:
        return None
    bg_red, bg_green, bg_blue = (bg[i] * bg[3] + 255 * (1 - bg[3]) for i in range(3))
    bg_rgb = (bg_red, bg_green, bg_blue)
    fg_red, fg_green, fg_blue = (fg[i] * fg[3] + bg_rgb[i] * (1 - fg[3]) for i in range(3))
    fg_rgb = (fg_red, fg_green, fg_blue)
    light, dark = sorted((relative_luminance(fg_rgb), relative_luminance(bg_rgb)), reverse=True)
    return round((light + 0.05) / (dark + 0.05), 2)
