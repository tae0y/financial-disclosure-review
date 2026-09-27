"""The four tools the discovery agent may call, and their argument schemas."""

from typing import Literal
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import Error as PlaywrightError
from pydantic import BaseModel

from ..core.text import norm, short
from ..llm.client import tool_spec
from .html import CHROME_TAGS, extract_pieces, outline_page, outside_blocks
from .session import (
    DOWNLOAD_EXT,
    GUARD_JS,
    RISKY_TEXT,
    PageSession,
    VisitCapReached,
)


class InspectPage(BaseModel):
    """Capped outline of the live page: headings, content regions, links, tabs and expandable
    controls, each with a candidate CSS selector and its match count."""


class ProbeSelector(BaseModel):
    """For each CSS selector: match count, visibility, and text samples with rendered font size,
    color and bounds of the text-bearing descendants, plus the viewport size."""

    selectors: list[str]


class Interact(BaseModel):
    """Act on the live page. scroll: one incremental step (selector ignored). expand: click every
    tab/accordion/expander matching the selector. open_link: open one informational GET link that
    continues the same product's explanation. go_back: reload the product page."""

    action: Literal["scroll", "expand", "open_link", "go_back"]
    selector: str = ""


class Step(BaseModel):
    action: Literal["scroll", "expand"]
    selector: str = ""


class Landmark(BaseModel):
    selector: str
    tag: str
    role: str = ""


class SubmitRule(BaseModel):
    """Propose the reusable rule. Code validates it on the live page before saving it."""

    product_name: str
    summary: str
    name_selector: str
    include: list[str]
    exclude: list[str] = []
    steps: list[Step] = []
    landmarks: list[Landmark]
    evidence: list[str] = []


def tool_inspect(sess: PageSession) -> dict:
    out = outline_page(sess.page.content())
    y, total = sess.page.evaluate("[window.scrollY, document.documentElement.scrollHeight]")
    sess.controls_seen = sum(not c["chrome"] for c in out["controls"])
    return {
        "url": sess.page.url,
        "on_linked_page": sess.on_linked,
        "scroll_y": round(y),
        "page_height": total,
        "visits_used": sess.visits,
        "states_captured": len(sess.snapshots),
        **out,
    }


def tool_probe(sess: PageSession, selectors: list[str]) -> dict:
    index = sess.dom_snapshot()
    root = sess.cdp.send("DOM.getDocument", {"depth": 0})["root"]["nodeId"]
    results = []
    for selector in selectors[:8]:
        sess.probed.add(selector)
        try:
            ids = sess.cdp.send("DOM.querySelectorAll", {"nodeId": root, "selector": selector})[
                "nodeIds"
            ]
        except PlaywrightError as error:
            results.append({"selector": selector, "error": str(error).splitlines()[0][:120]})
            continue
        total = visible = 0
        samples = []
        for node_id in ids[:12]:
            backend = sess.cdp.send("DOM.describeNode", {"nodeId": node_id})["node"][
                "backendNodeId"
            ]
            start = index.by_backend.get(backend)
            for i in index.text_elements(start) if start is not None else []:
                row = index.row(i, text_limit=80)
                total += 1
                visible += row["visible"]
                if len(samples) < 6:
                    samples.append(row)
        results.append(
            {
                "selector": selector,
                "matches": len(ids),
                "text_elements": total,
                "visible_text_elements": visible,
                "samples": samples,
            }
        )
    return {"viewport": sess.viewport(), "document": index.size, "results": results}


def tool_interact(sess: PageSession, action: str, selector: str) -> dict:
    if action == "scroll":
        out = sess.scroll_step()
        changed = sess.snapshot_if_changed("explore", "scroll")
        return {**out, "new_state": bool(changed)}
    if action == "expand":
        sess.expand_tried = True
        return sess.click_matches(selector, "explore")
    if action == "open_link":
        return open_link(sess, selector)
    if action == "go_back":
        sess.goto(sess.url)
        sess.on_linked = False
        return {"url": sess.page.url, "visits_used": sess.visits}
    return {"error": f"unknown action {action!r}"}


def open_link(sess: PageSession, selector: str) -> dict:
    """Open one same-site informational GET link. The current state is snapshotted first."""
    locator = sess.page.locator("css=" + selector)
    if sess.match_count(selector)[0] == 0:
        return {"error": "no match"}
    element = locator.first
    info = element.evaluate(GUARD_JS)
    href = urljoin(sess.page.url, info["href"])
    target = urlparse(href)
    if info["tag"] != "a" or info["in_form"]:
        return {"error": "only plain a[href] links outside forms may be opened"}
    if target.scheme not in ("http", "https") or target.hostname != urlparse(sess.url).hostname:
        return {"error": f"rejected: {href} is not an http(s) link on the same site"}
    if target.path.lower().endswith(DOWNLOAD_EXT) or RISKY_TEXT.search(info["text"]):
        return {"error": f"rejected: {href} looks like a download or an apply/login action"}
    sess.snapshot_if_changed("explore", f"before leaving for {href}")
    sess.goto(href)
    sess.on_linked = True
    return {
        "url": sess.page.url,
        "title": sess.page.title(),
        "text_head": sess.page.inner_text("body")[:600],
    }


def tool_submit(sess: PageSession, args: dict) -> dict:
    """Validate a proposed rule against the live page; the model never writes the rule file."""
    if sess.on_linked:
        return {"accepted": False, "errors": ["go_back to the product page before submitting"]}
    try:
        proposal = SubmitRule.model_validate(args)
    except Exception as error:
        return {"accepted": False, "errors": [f"invalid arguments: {short(str(error), 300)}"]}
    errors = []
    if not proposal.include:
        errors.append("include is empty")
    for selector in proposal.include:
        count, problem = sess.match_count(selector)
        if problem or count == 0:
            errors.append(f"include {selector!r}: {problem or 'matches 0 elements'}")
    for selector in proposal.exclude:
        _, problem = sess.match_count(selector)
        if problem:
            errors.append(f"exclude {selector!r}: {problem}")
    for step in proposal.steps:
        if step.action == "expand" and sess.match_count(step.selector)[0] == 0:
            errors.append(f"step expand {step.selector!r} matches 0 elements")
    html = sess.page.content()
    soup = BeautifulSoup(html, "html.parser")
    for mark in proposal.landmarks:
        try:
            found = soup.select(mark.selector)
        except Exception:
            found = []
        if not any(
            el.name == mark.tag.lower() and (not mark.role or el.get("role") == mark.role)
            for el in found
        ):
            errors.append(
                f"landmark {mark.selector!r} not found as <{mark.tag}> role={mark.role!r}"
            )
    if len(proposal.landmarks) < 2:
        errors.append("give at least 2 landmarks")
    try:
        named = soup.select_one(proposal.name_selector)
    except Exception:
        named = None
    if named is None or norm(proposal.product_name) not in norm(named.get_text(" ")):
        errors.append("name_selector must match an element whose text contains product_name")
    pieces = extract_pieces(html, proposal.include, proposal.exclude)
    chars = sum(len(p["text"]) for p in pieces)
    if chars < 300:
        errors.append(f"selected content is only {chars} characters")
    for piece in pieces:
        head = BeautifulSoup(piece["html"], "html.parser").find(True)
        if head is not None and head.name in CHROME_TAGS:
            errors.append(f"include {piece['selector']!r} selects page chrome <{head.name}>")
    unprobed = [s for s in proposal.include if s not in sess.probed]
    if unprobed:
        errors.append(
            f"probe_selector these include selectors first to see what they select: {unprobed}"
        )
    if sess.controls_seen and not sess.expand_tried and not sess.nudged:
        sess.nudged = True
        errors.append(
            f"inspect_page showed {sess.controls_seen} tab/expandable controls outside page"
            " chrome and none was tried. Expand them and check for hidden product content,"
            " or resubmit if none holds any."
        )
    if not errors and not sess.outside_reviewed:
        left = list(
            dict.fromkeys(
                text[:70] for _, text in outside_blocks(html, proposal.include, proposal.exclude)
            )
        )
        if left:
            sess.outside_reviewed = True
            errors.append(
                f"{len(left)} text blocks outside page chrome are not selected,"
                f" e.g. {left[:10]}. If any is product content (terms, conditions, warnings,"
                " notes, disclosures), include its region or give the reason; then submit"
                " again. Resubmit unchanged if none is product content."
            )
    if errors:
        return {"accepted": False, "errors": errors}
    sess.pending = {"version": 1, **proposal.model_dump()}
    return {"accepted": True, "regions": len(pieces), "chars": chars}


def call_tool(sess: PageSession, name: str, args: dict) -> dict:
    try:
        if name == "inspect_page":
            return tool_inspect(sess)
        if name == "probe_selector":
            return tool_probe(sess, list(args.get("selectors", [])))
        if name == "interact":
            return tool_interact(sess, args.get("action", ""), args.get("selector", ""))
        if name == "submit_rule":
            return tool_submit(sess, args)
        return {"error": f"unknown tool {name!r}"}
    except VisitCapReached as error:
        return {"error": str(error)}
    except PlaywrightError as error:
        return {"error": str(error).splitlines()[0][:200]}


TOOLS = [
    tool_spec("inspect_page", InspectPage),
    tool_spec("probe_selector", ProbeSelector),
    tool_spec("interact", Interact),
    tool_spec("submit_rule", SubmitRule),
]
