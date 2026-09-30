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


def unused_sentences(html: str, used_quotes: list[str], n: int, min_chars: int = 30) -> list[str]:
    """The `n` longest sentences no judgment cited, longest first — control edits."""
    text = visible_text(html)
    used = [norm(q) for q in used_quotes if q]
    candidates: list[str] = []
    for raw in text.replace("!", ".").replace("?", ".").split("."):
        sentence = raw.strip()
        if len(sentence) < min_chars or sentence in candidates:
            continue
        low = norm(sentence)
        if any(low in u or u in low for u in used):
            continue
        candidates.append(sentence)
    return sorted(candidates, key=len, reverse=True)[:n]


def longest_unused_sentence(html: str, used_quotes: list[str], min_chars: int = 30) -> str:
    """A long sentence no judgment cited, the control edit — deleting it must not flip any item."""
    found = unused_sentences(html, used_quotes, 1, min_chars)
    return found[0] if found else ""
