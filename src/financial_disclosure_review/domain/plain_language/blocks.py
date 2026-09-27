"""Splitting the original page into the blocks the model rewrites one by one."""

from ...core.text import html_lines, locate_quote, visible_text


def plain_blocks(html: str) -> list[dict]:
    """원문을 시각적 줄 단위로 나눈 뒤, 원문에서 위치를 다시 확인할 수 있는 줄만 블록으로 남긴다.
    같은 문장이 반복되면 하나의 블록으로 합친다. id는 blocks 순서로 매겨 같은 html에는 항상 같다."""
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
