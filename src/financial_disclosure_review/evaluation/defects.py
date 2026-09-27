"""Building evaluation variants by removing a known sentence from a real page.

Gold labels for "did the review notice a missing disclosure?" are hard to buy and easy to argue
with. They are cheap to make correct by construction: take a real page, take a disclosure the
review itself located and quoted, delete exactly that sentence, and the label follows — that
disclosure is now absent. A check that still calls the item 적합 is measurably wrong.

Nothing here judges anything. It edits html and reports whether the edit really landed.
"""

from bs4 import BeautifulSoup
from bs4.element import NavigableString

from ..core.text import locate_quote, norm, visible_text

MIN_NODE_CHARS = 4


def remove_quote(html: str, quote: str) -> tuple[str, bool]:
    """Delete the text carrying `quote` from `html`. Returns (html, whether it is really gone).

    A quote can sit in one text node or span several, so every node whose normalized text is
    inside the normalized quote (or holds it) is emptied. The second return value is checked
    against the rendered text, never assumed: a variant whose defect did not land is not a
    valid test case.
    """
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
    """A long sentence no judgment cited, used as the neutral control edit.

    Deleting it must not turn any item from 적합 into 부적합; if it does, the check is reacting to
    the page changing rather than to the disclosure that left.
    """
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
