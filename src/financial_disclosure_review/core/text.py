"""String handling shared by the domains: normalizing, hashing, quoting."""

import hashlib
import json
import re
from typing import Any

from bs4 import BeautifulSoup

BLOCK_TAGS = [
    "p",
    "li",
    "div",
    "tr",
    "td",
    "th",
    "dt",
    "dd",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "section",
    "article",
    "ul",
    "ol",
    "table",
    "main",
    "header",
    "footer",
    "br",
]


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def digest(text: str) -> str:
    return hashlib.sha1(norm(text).encode()).hexdigest()[:12]


def short(value: Any, limit: int = 240) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + "…"


def visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return " ".join(soup.get_text(" ").split())


def html_lines(html: str) -> list[str]:
    """Text of the LLM-facing html split at block elements and <br>: one entry per visual line."""
    soup = BeautifulSoup(html, "html.parser")
    for el in soup.find_all(BLOCK_TAGS):
        el.insert_before("\n")
        el.insert_after("\n")
    parts = (" ".join(part.split()) for part in soup.get_text().split("\n"))
    return [line for line in parts if line]


def locate_quote(text: str, quote: str) -> tuple[int, int] | None:
    """공백을 모두 무시하고 quote를 찾아 text 안의 (시작, 끝) 위치를 돌려준다."""
    kept = [i for i, ch in enumerate(text) if not ch.isspace()]
    compact = "".join(text[i] for i in kept)
    needle = "".join(quote.split())
    pos = compact.find(needle) if needle else -1
    if pos < 0:
        return None
    return kept[pos], kept[pos + len(needle) - 1] + 1


def quote_percent(text: str, quote: str) -> str:
    kept = [i for i, ch in enumerate(text) if not ch.isspace()]
    compact = "".join(text[i] for i in kept)
    needle = "".join(quote.split())
    pos = compact.find(needle) if needle else -1
    return f"{pos / len(compact) * 100:.0f}%" if pos >= 0 else "없음"
