"""HTML of one page state: page chrome, selected regions, CSS selectors, page outline."""

import re
from html import escape

from bs4 import BeautifulSoup

from ...core.text import digest

CHROME_TAGS = {"header", "nav", "footer", "aside"}
CHROME_ROLES = {"banner", "navigation", "contentinfo", "complementary"}
LAYER_WORDS = re.compile(r"popup|modal|layer|dialog|toast|cookie", re.I)


def in_chrome(el) -> bool:
    return any(
        getattr(a, "name", None) in CHROME_TAGS
        or (getattr(a, "attrs", {}).get("role") in CHROME_ROLES)
        for a in [el, *el.parents]
    )


def clean_html(el) -> str:
    """Body markup of one region without scripts, styling attributes, or empty nodes."""
    soup = BeautifulSoup(str(el), "html.parser")
    for tag in soup(["script", "style", "noscript", "template", "iframe", "svg"]):
        tag.extract()
    keep = ("role", "alt", "title", "colspan", "rowspan")
    for node in soup.find_all(True):
        node.attrs = {k: v for k, v in node.attrs.items() if k in keep or k.startswith("aria-")}
    return re.sub(r"\s+", " ", str(soup)).strip()


def extract_pieces(html: str, include: list[str], exclude: list[str]) -> list[dict]:
    """Selected regions of one page state: include matches minus exclude matches inside them."""
    soup = BeautifulSoup(html, "html.parser")
    matches, seen = [], set()
    for selector in include:
        try:
            found = soup.select(selector)
        except Exception:
            continue
        for el in found:
            if id(el) not in seen:
                seen.add(id(el))
                matches.append((selector, el))
    pieces = []
    for selector, el in matches:
        if any(id(parent) in seen for parent in el.parents):
            continue
        clone = BeautifulSoup(str(el), "html.parser")
        for rule in exclude:
            try:
                for node in clone.select(rule):
                    node.decompose()
            except Exception:
                continue
        text = clone.get_text(" ", strip=True)
        if text:
            pieces.append({"selector": selector, "text": text, "html": clean_html(clone)})
    return pieces


def merge_pieces(states: list[list[dict]]) -> tuple[list[dict], str]:
    """Union of the regions seen in every captured state, first appearance kept."""
    seen, kept = set(), []
    for number, pieces in enumerate(states):
        for piece in pieces:
            key = digest(piece["text"])
            if key not in seen:
                seen.add(key)
                kept.append({**piece, "state": number})
    html = "\n".join(
        f'<section data-selector="{escape(p["selector"])}" data-state="{p["state"]}">'
        f"{p['html']}</section>"
        for p in kept
    )
    return kept, html


def path_key(el) -> str:
    """Structural path of an element without indices or text: tag#id / tag.class per ancestor."""
    names = []
    for node in [el, *el.parents][:6]:
        if not getattr(node, "name", None) or node.name in ("[document]", "html", "body"):
            continue
        el_id = node.get("id") or ""
        classes = [c for c in node.get("class") or [] if not re.search(r"\d{3,}", c)]
        usable_id = el_id and not re.search(r"\d{3,}", el_id)
        mark = f"#{el_id}" if usable_id else (f".{classes[0]}" if classes else "")
        names.append(node.name + mark)
    return ">".join(reversed(names))


def outside_blocks(html: str, include: list[str], exclude: list[str]) -> list[tuple[str, str]]:
    """(structural path, text) of text blocks outside the selected regions, ignoring page chrome
    and popup layers."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "template", "svg"]):
        tag.decompose()
    inside = set()
    for selector in include + exclude:
        try:
            inside |= {id(el) for el in soup.select(selector)}
        except Exception:
            continue
    blocks = []
    for el in (soup.body or soup).find_all(True):
        own = " ".join("".join(s for s in el.find_all(string=True, recursive=False)).split())
        if len(own) < 20:
            continue
        chain = [el, *el.parents]
        if any(id(a) in inside for a in chain) or in_chrome(el):
            continue
        tagged = [a for a in chain if getattr(a, "attrs", None) is not None]
        marks = [f"{a.get('id') or ''} {' '.join(a.get('class') or [])}" for a in tagged]
        if any(LAYER_WORDS.search(m) for m in marks) or any(
            a.get("role") in ("dialog", "alertdialog") for a in tagged
        ):
            continue
        blocks.append((path_key(el), own))
    return blocks


def outside_signature(html: str, include: list[str], exclude: list[str]) -> list[str]:
    """Structural paths of the text blocks outside the selected regions. New paths later mean
    content this rule does not cover."""
    return sorted({path for path, _ in outside_blocks(html, include, exclude)})[:400]


def valid_ident(name: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_][\w-]*", name))


def selector_for(el, soup, depth: int = 0) -> str:
    """CSS selector that matches el: id, then tag+classes, then an nth-of-type path."""
    tried = []
    if el.get("id"):
        tried.append(f"#{el['id']}" if valid_ident(el["id"]) else f'{el.name}[id="{el["id"]}"]')
    classes = [c for c in el.get("class") or [] if valid_ident(c)]
    if classes:
        tried += [el.name + "".join(f".{c}" for c in classes[:2]), f"{el.name}.{classes[0]}"]
    for selector in tried:
        try:
            if any(m is el for m in soup.select(selector)):
                return selector
        except Exception:
            continue
    index = 1 + sum(1 for s in el.previous_siblings if getattr(s, "name", None) == el.name)
    own = f"{el.name}:nth-of-type({index})"
    parent = el.parent
    if parent is None or parent.name in ("[document]", "html", "body") or depth >= 4:
        return own
    return f"{selector_for(parent, soup, depth + 1)} > {own}"


CONTROL_QUERY = (
    "[role=tab], summary, [aria-expanded], [aria-controls], [class*=tab] a, [class*=tab] button, "
    "[class*=acc] button, [class*=toggle], a[href^='#'], a[href^='javascript:']"
)


def outline_page(html: str, regions: int = 70, links: int = 30, controls: int = 40) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "template", "svg"]):
        tag.decompose()
    body = soup.body or soup
    hooks = {"main", "article", "section", "details", "table", "aside", "form"}
    rows = []
    for el in body.find_all(True):
        text = el.get_text(" ", strip=True)
        if len(text) < 80 or not (
            el.get("id") or el.get("class") or el.get("role") or el.name in hooks
        ):
            continue
        containers = hooks | {"div", "ul", "ol", "dl", "header", "footer", "nav"}
        if el.name not in containers and el.get("role") not in ("tabpanel", "main", "region"):
            continue
        kids = [c for c in el.find_all(True, recursive=False) if c.get_text(strip=True)]
        if len(kids) == 1 and len(kids[0].get_text(" ", strip=True)) >= 0.95 * len(text):
            continue
        selector = selector_for(el, soup)
        rows.append(
            {
                "selector": selector,
                "matches": len(soup.select(selector)),
                "tag": el.name,
                "role": el.get("role") or "",
                "depth": len(list(el.parents)),
                "text_chars": len(text),
                "head": text[:60],
                "hidden": bool(
                    el.has_attr("hidden")
                    or el.get("aria-hidden") == "true"
                    or "display:none" in str(el.get("style", "")).replace(" ", "")
                ),
                "chrome": in_chrome(el),
            }
        )
    if len(rows) > regions:
        floor = sorted(r["text_chars"] for r in rows)[len(rows) - regions]
        rows = [r for r in rows if r["text_chars"] >= floor][:regions]
    headings = [
        {"selector": selector_for(h, soup), "text": h.get_text(" ", strip=True)[:80]}
        for h in body.find_all(["h1", "h2", "h3", "h4", "h5"])
        if h.get_text(strip=True)
    ][:30]
    anchors = [
        {
            "selector": selector_for(a, soup),
            "text": a.get_text(" ", strip=True)[:50],
            "href": a["href"][:120],
            "chrome": in_chrome(a),
        }
        for a in body.select("a[href]")
        if a.get_text(strip=True) and not str(a["href"]).startswith(("#", "javascript:"))
    ]
    anchors.sort(key=lambda a: a["chrome"])
    found, seen = [], set()
    for el in body.select(CONTROL_QUERY):
        if id(el) in seen:
            continue
        seen.add(id(el))
        found.append(
            {
                "selector": selector_for(el, soup),
                "tag": el.name,
                "text": el.get_text(" ", strip=True)[:40],
                "expanded": el.get("aria-expanded"),
                "controls": el.get("aria-controls"),
                "chrome": in_chrome(el),
            }
        )
    return {
        "title": soup.title.get_text(strip=True) if soup.title else "",
        "headings": headings,
        "regions": rows,
        "links": anchors[:links],
        "controls": found[:controls],
    }
