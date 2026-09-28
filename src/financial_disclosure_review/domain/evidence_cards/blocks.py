"""Splitting the page into quotable sources and giving each one a code-decided visibility."""

from collections.abc import Mapping
from typing import Any

from ...core.text import html_lines, locate_quote, norm, visible_text
from ..display_check.blocks import display_blocks


def _visibility(matched: list[dict]) -> str:
    """default_visible > revealed > image_only > hidden > unresolved, from measured blocks."""
    if not matched:
        return "unresolved"
    if any(b["default_visible"] for b in matched):
        return "default_visible"
    if any(b["ever_visible"] for b in matched):
        return "revealed"
    if all(b.get("visual_risk") for b in matched):
        return "image_only"
    return "hidden"


def page_sources(page: Mapping[str, Any]) -> list[dict]:
    """원문을 줄 단위로 나누고 dom-N id를 매긴다. visibility는 코드가 스냅숏과 대조해 정한다."""
    html = page.get("html") or ""
    text = visible_text(html)
    blocks, _stats = display_blocks(page)

    sources: list[dict] = []
    seen: set[str] = set()
    for line in html_lines(html):
        if line in seen:
            continue
        seen.add(line)
        if locate_quote(text, line) is None:
            continue
        line_norm = norm(line)
        matched = [b for b in blocks if norm(b["text"]) and norm(b["text"]) in line_norm]
        sources.append(
            {
                "source_id": f"dom-{len(sources)}",
                "text": line,
                "visibility": _visibility(matched),
            }
        )
    return sources
