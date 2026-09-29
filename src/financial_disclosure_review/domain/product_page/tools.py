"""The four tools the discovery agent may call, and their argument schemas."""

from typing import Literal
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import Error as PlaywrightError
from pydantic import BaseModel

from ...core.text import norm, short
from ...llm.client import tool_spec
from . import coverage
from .html import CHROME_TAGS, extract_pieces, outline_page, outside_blocks
from .session import (
    DOWNLOAD_EXT,
    GUARD_JS,
    RISKY_TEXT,
    PageSession,
    VisitCapReached,
)


class InspectPage(BaseModel):
    """Capped outline of the page: headings, regions, links, tabs, controls, CSS selectors,
    hidden/visible text counts, candidate controls, benefit/warning/footnote samples and open
    coverage gaps."""


class ProbeSelector(BaseModel):
    """For each selector: match count, visibility, text samples with style, and viewport size."""

    selectors: list[str]


class Interact(BaseModel):
    """Act on the live page: scroll, expand (click tabs/accordions), open_link, or go_back.
    scroll/expand/open_link require gap_id and expected_evidence naming the coverage gap this
    action investigates; go_back needs neither."""

    action: Literal["scroll", "expand", "open_link", "go_back"]
    selector: str = ""
    gap_id: str = ""
    expected_evidence: str = ""


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
    obs = coverage.observe(sess)
    coverage.derive_gaps(sess, obs)
    return {
        "url": sess.page.url,
        "on_linked_page": sess.on_linked,
        "scroll_y": round(y),
        "page_height": total,
        "visits_used": sess.visits,
        "states_captured": len(sess.snapshots),
        "hidden_text_blocks": obs["hidden_text_blocks"],
        "visible_text_blocks": obs["visible_text_blocks"],
        "candidate_controls": obs["candidate_controls"],
        "benefit_samples": obs["benefit_samples"],
        "warning_samples": obs["warning_samples"],
        "footnote_samples": obs["footnote_samples"],
        "open_gaps": coverage.public_gaps(sess),
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


def _origin(url: str) -> tuple[str, str | None, int | None]:
    parts = urlparse(url)
    default_port = 443 if parts.scheme == "https" else 80 if parts.scheme == "http" else None
    return parts.scheme, parts.hostname, parts.port or default_port


def expand_action(sess: PageSession, selector: str) -> dict:
    """Click every safe match; blocked only when nothing could be clicked for a safety reason."""
    total, problem = sess.match_count(selector)
    if problem:
        return {"blocked": True, "blocked_reason": problem}
    if total == 0:
        return {"blocked": True, "blocked_reason": "no match"}
    report = sess.click_matches(selector, "explore")
    if report["clicked"] == 0 and report["matched"] > 0:
        reasons = {
            s["reason"] for s in report["skipped"] if not s["reason"].startswith("click failed")
        }
        if reasons:
            return {"blocked": True, "blocked_reason": "; ".join(sorted(reasons)), **report}
    return report


def open_link(sess: PageSession, selector: str) -> dict:
    """Open one same-origin informational GET link. The current state is snapshotted first."""
    if sess.match_count(selector)[0] == 0:
        return {"blocked": True, "blocked_reason": "no match"}
    locator = sess.page.locator("css=" + selector)
    element = locator.first
    info = element.evaluate(GUARD_JS)
    href = urljoin(sess.page.url, info["href"])
    target = urlparse(href)
    if info["tag"] != "a" or info["in_form"]:
        return {
            "blocked": True,
            "blocked_reason": "only plain a[href] links outside forms may be opened",
        }
    if target.scheme not in ("http", "https") or _origin(href) != _origin(sess.url):
        return {"blocked": True, "blocked_reason": f"rejected: {href} is not the same origin"}
    if target.path.lower().endswith(DOWNLOAD_EXT) or RISKY_TEXT.search(info["text"]):
        return {
            "blocked": True,
            "blocked_reason": f"rejected: {href} looks like a download or an apply/login action",
        }
    sess.snapshot_if_changed("explore", f"before leaving for {href}")
    with sess.interacting_window():
        sess.goto(href)
    sess.on_linked = True
    return {
        "url": sess.page.url,
        "title": sess.page.title(),
        "text_head": sess.page.inner_text("body")[:600],
    }


def tool_interact(sess: PageSession, args: dict) -> dict:
    action = args.get("action", "")
    selector = args.get("selector", "")
    gap_id = args.get("gap_id", "")
    expected_evidence = args.get("expected_evidence", "")

    # go_back stays open after exploration closes: submit_rule needs the product page, so an
    # agent left on a linked page must still be able to return and submit.
    if sess.exploration_closed and action != "go_back":
        return {
            "blocked": True,
            "blocked_reason": f"exploration closed: {sess.exploration_closed}; submit_rule now",
        }
    if action != "go_back" and not (gap_id and expected_evidence):
        return {
            "blocked": True,
            "blocked_reason": (
                "gap_id and expected_evidence are required for scroll/expand/open_link"
            ),
        }
    if action in ("expand", "open_link") and (action, selector) in sess.tried_actions:
        sess.exploration_closed = "repeated_action"
        return {
            "blocked": True,
            "blocked_reason": f"repeated {action} {selector!r} gives no new information; "
            "exploration is closed",
        }

    if action == "scroll":
        out = sess.scroll_step()
        changed = sess.snapshot_if_changed("explore", "scroll")
        sess.last_action_note = "scroll"
        return {**out, "new_state": bool(changed)}
    if action == "expand":
        result = expand_action(sess, selector)
        if not result.get("blocked"):
            sess.tried_actions.add((action, selector))
            sess.tried_expand.add(selector)
            sess.expand_tried = True
            sess.last_action_note = f"interact expand {selector} (gap {gap_id})"
        return result
    if action == "open_link":
        result = open_link(sess, selector)
        if not result.get("blocked"):
            sess.tried_actions.add((action, selector))
            sess.last_action_note = f"interact open_link {selector} (gap {gap_id})"
        return result
    if action == "go_back":
        sess.goto(sess.url)
        sess.on_linked = False
        sess.last_action_note = "go_back"
        return {"url": sess.page.url, "visits_used": sess.visits}
    return {"error": f"unknown action {action!r}"}


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
    # An include the agent never looked at is still refused, but the tool probes it now and
    # returns what it selects, so the next submit needs no separate probe turn (2026-09-29 F1:
    # a page spent all 20 turns alternating submit -> "probe first" -> probe -> submit).
    unprobed = [s for s in proposal.include if s not in sess.probed]
    probed_now = None
    if unprobed:
        probed_now = tool_probe(sess, unprobed)
        errors.append(
            f"these include selectors had not been probed: {unprobed}. Their probe results are"
            " in `probe` below; check what they select and resubmit (no separate probe needed)."
        )
    open_controls = [
        g for g in sess.gaps if g["kind"] == "unexpanded_control" and g["status"] != "closed"
    ]
    if open_controls and not sess.tried_expand and not sess.nudged:
        sess.nudged = True
        ids = [g["id"] for g in open_controls]
        errors.append(
            f"open gaps {ids} name expandable controls that were never tried. Expand them and"
            " check for hidden product content, or resubmit if none holds any."
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
        return {
            "accepted": False,
            "errors": errors,
            **({"probe": probed_now} if probed_now else {}),
        }
    sess.pending = {"version": 1, **proposal.model_dump()}
    sess.final_coverage = coverage.finalize_coverage(sess, proposal.include, proposal.exclude)
    sess.last_action_note = "submit_rule accepted"
    return {"accepted": True, "regions": len(pieces), "chars": chars}


def call_tool(sess: PageSession, name: str, args: dict) -> dict:
    if name == "interact" and sess.exploration_closed and args.get("action") != "go_back":
        return {
            "blocked": True,
            "blocked_reason": f"exploration closed: {sess.exploration_closed}; submit_rule now",
            "new_evidence": False,
            "coverage_before": {},
            "coverage_after": {},
        }
    obs_before = coverage.observe(sess)
    coverage.derive_gaps(sess, obs_before)
    before = coverage.summarize(obs_before, sess)
    result: dict
    try:
        if name == "inspect_page":
            result = tool_inspect(sess)
        elif name == "probe_selector":
            result = tool_probe(sess, list(args.get("selectors", [])))
        elif name == "interact":
            result = tool_interact(sess, args)
        elif name == "submit_rule":
            result = tool_submit(sess, args)
        else:
            result = {"error": f"unknown tool {name!r}"}
    except VisitCapReached as error:
        result = {"error": str(error)}
    except PlaywrightError as error:
        result = {"error": str(error).splitlines()[0][:200]}
    obs_after = coverage.observe(sess)
    coverage.derive_gaps(sess, obs_after)
    after = coverage.summarize(obs_after, sess)
    new_evidence = obs_before["signature"] != obs_after["signature"]

    if name == "interact" and args.get("action") != "go_back" and not result.get("blocked"):
        sess.interactions_count += 1
        if new_evidence:
            sess.no_progress_count = 0
        else:
            sess.no_progress_count += 1
    _maybe_close_exploration(sess)

    result.setdefault("blocked", False)
    result["new_evidence"] = new_evidence
    result["coverage_before"] = before
    result["coverage_after"] = after
    return result


def _maybe_close_exploration(sess: PageSession) -> None:
    if sess.exploration_closed:
        return
    if sess.interactions_count >= coverage.max_interactions(sess.ctx):
        sess.exploration_closed = "interaction_budget"
    elif sess.no_progress_count >= coverage.max_no_progress(sess.ctx):
        sess.exploration_closed = "no_new_evidence"
    elif not any(
        g["kind"] in coverage.ACTIONABLE_KINDS and g["status"] != "closed" for g in sess.gaps
    ):
        sess.exploration_closed = "full_coverage"


TOOLS = [
    tool_spec("inspect_page", InspectPage),
    tool_spec("probe_selector", ProbeSelector),
    tool_spec("interact", Interact),
    tool_spec("submit_rule", SubmitRule),
]
