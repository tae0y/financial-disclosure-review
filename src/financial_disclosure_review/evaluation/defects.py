"""Builds variants by deleting a disclosure sentence the review quoted, so the label is correct."""

from bs4 import BeautifulSoup
from bs4.element import NavigableString

from ..core.text import locate_quote, norm, visible_text

MIN_NODE_CHARS = 4


def remove_quote(html: str, quote: str) -> tuple[str, bool]:
    """Delete the text carrying `quote` from `html`; returns (html, whether it's really gone)."""
    soup = BeautifulSoup(html, "html.parser")
    target = norm(quote)
    if not target:
        return html, False
    removed = False
    for node in list(soup.find_all(string=True)):
        text = norm(str(node))
        if len(text) < MIN_NODE_CHARS:
            continue
        if target in text:
            node.replace_with(NavigableString(""))
            removed = True
        elif text in target:
            node.replace_with(NavigableString(""))
            removed = True
    result = str(soup)
    gone = removed and locate_quote(visible_text(result), quote) is None
    return result, gone


def longest_unused_sentence(html: str, used_quotes: list[str], min_chars: int = 30) -> str:
    """A long sentence no judgment cited, the control edit — deleting it must not flip any item."""
    text = visible_text(html)
    used = [norm(q) for q in used_quotes if q]
    candidates = []
    for raw in text.replace("!", ".").replace("?", ".").split("."):
        sentence = raw.strip()
        if len(sentence) < min_chars:
            continue
        low = norm(sentence)
        if any(low in u or u in low for u in used):
            continue
        candidates.append(sentence)
    return max(candidates, key=len) if candidates else ""
