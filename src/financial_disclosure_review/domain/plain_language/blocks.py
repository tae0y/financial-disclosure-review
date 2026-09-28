"""Splitting the original page into the blocks the model rewrites one by one."""

from ...core.text import html_lines, locate_quote, visible_text


def plain_blocks(html: str) -> list[dict]:
    """원문을 시각적 줄 단위로 나눈 뒤, 위치를 재확인할 수 있는 줄만 블록으로 남긴다."""
    text = visible_text(html)
    seen: set[str] = set()
    blocks: list[dict] = []
    for line in html_lines(html):
        if line in seen:
            continue
        seen.add(line)
        if locate_quote(text, line) is None:
            continue
        blocks.append({"id": f"b{len(blocks)}", "quote": line})
    return blocks
