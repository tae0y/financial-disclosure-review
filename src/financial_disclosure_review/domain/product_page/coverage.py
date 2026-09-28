"""Coverage gaps: lexical signals that steer exploration. They never become a verdict.

`observe()` measures the live page once; `derive_gaps()` folds that measurement into the
session's running gap list (stable ids, open/closed/unresolved status). Both are called by
`tools.call_tool` around every tool call, so the agent always sees the current gap set and a
`new_evidence` flag it cannot fake.
"""

import re

from bs4 import BeautifulSoup
from playwright.sync_api import Error as PlaywrightError

from ...core.text import digest
from .html import CONTROL_QUERY, LAYER_WORDS, in_chrome, selector_for
from .session import GUARD_JS, reject_reason

BENEFIT_SIGNAL = re.compile(r"할인|적립|캐시백|무이자|면제|금리|이자율|%")
CONDITION_SIGNAL = re.compile(r"전월|실적|이상|한도|제외|조건|단,|※")
WARNING_SIGNAL = re.compile(r"유의|경고|주의|위험|불이익|연체")
FOOTNOTE_SIGNAL = re.compile(r"^\s*[*※]")
DISCLOSURE_ALT = re.compile(r"할인|적립|금리|이자율|수수료|조건|유의|한도|혜택|안내|%|연회비")
MIN_BLOCK_CHARS = 8
DEFAULT_MAX_INTERACTIONS = 8
DEFAULT_MAX_NO_PROGRESS = 2

ACTIONABLE_KINDS = ("unexpanded_control", "hidden_text")


def max_interactions(ctx) -> int:
    """`Context.max_interactions` when the field exists, else the Stage 1 default of 8."""
    return getattr(ctx, "max_interactions", DEFAULT_MAX_INTERACTIONS)


def max_no_progress(ctx) -> int:
    """`Context.max_no_progress` when the field exists, else the Stage 1 default of 2."""
    return getattr(ctx, "max_no_progress", DEFAULT_MAX_NO_PROGRESS)


def in_layer(el) -> bool:
    """Inside a popup/modal/dialog layer, by wording on an ancestor's id/class or its role."""
    for a in [el, *el.parents]:
        attrs = getattr(a, "attrs", None)
        if attrs is None:
            continue
        marks = f"{attrs.get('id') or ''} {' '.join(attrs.get('class') or [])}"
        if LAYER_WORDS.search(marks) or attrs.get("role") in ("dialog", "alertdialog"):
            return True
    return False


def _is_hidden(el) -> bool:
    for a in [el, *el.parents]:
        if not hasattr(a, "attrs"):
            continue
        if a.has_attr("hidden") or a.get("aria-hidden") == "true":
            return True
        style = str(a.get("style", "")).replace(" ", "")
        if "display:none" in style:
            return True
    return False


# Rendered visibility of every text element, keyed by its own text. The static html cannot tell
# a stylesheet-collapsed accordion (visibility:hidden, display:none, a zero-height clip) from open
# text; the 2026-09-29 live run on a Tailwind/DaisyUI page reported 0 hidden blocks this way.
RENDERED_VISIBILITY_JS = r"""() => {
  const seen = {};
  const clipped = (el) => {
    for (let a = el.parentElement; a && a !== document.body; a = a.parentElement) {
      const s = getComputedStyle(a);
      if ((s.overflow + s.overflowY).includes('hidden') && a.getBoundingClientRect().height < 2)
        return true;
    }
    return false;
  };
  for (const el of document.body.querySelectorAll('*')) {
    if (['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE'].includes(el.tagName)) continue;
    let own = '';
    for (const n of el.childNodes) if (n.nodeType === 3) own += n.textContent;
    own = own.split(/\s+/).join(' ').trim();
    if (own.length < 2) continue;
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    const shown = r.width > 0 && r.height > 0 && s.visibility !== 'hidden'
      && s.display !== 'none' && parseFloat(s.opacity || '1') > 0
      && (!el.checkVisibility || el.checkVisibility({visibilityProperty: true}))
      && !clipped(el);
    seen[own] = Boolean(seen[own]) || shown;
  }
  return seen;
}"""


def rendered_visibility(sess) -> dict[str, bool]:
    """Own text -> whether any element carrying it is actually rendered visible."""
    try:
        return dict(sess.page.evaluate(RENDERED_VISIBILITY_JS))
    except PlaywrightError:
        return {}


def _own_text(el) -> str:
    return " ".join("".join(s for s in el.find_all(string=True, recursive=False)).split())


def _delegates_to_toggle(el) -> bool:
    """A `.collapse-title` whose accordion has its own toggle input: the input is the control
    (the title is clicked through it), so the title must not become a second gap."""
    parent = el.parent
    if not any("collapse-title" in c for c in el.get("class") or []) or parent is None:
        return False
    return "collapse" in (parent.get("class") or []) and any(
        child.name == "input" and child.get("type") in ("checkbox", "radio")
        for child in parent.find_all(recursive=False)
    )


def _was_clicked(sess, selector: str) -> bool:
    """Whether a real expand click landed on this control (marked in the page by click_matches),
    so one expand over many accordions closes each accordion's gap."""
    try:
        return bool(
            sess.page.evaluate(
                "s => { const e = document.querySelector(s);"
                " return !!(e && window.__fdrClicked && window.__fdrClicked.has(e)); }",
                selector,
            )
        )
    except PlaywrightError:
        return False


def observe(sess) -> dict:
    """Measure the live page: visible/hidden text blocks, candidate controls, samples."""
    html = sess.page.content()
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "template", "svg"]):
        tag.decompose()
    body = soup.body or soup

    rendered = rendered_visibility(sess)
    blocks = []
    for el in body.find_all(True):
        own = _own_text(el)
        if len(own) < MIN_BLOCK_CHARS or in_chrome(el) or in_layer(el):
            continue
        hidden = _is_hidden(el) or rendered.get(own) is False
        blocks.append({"selector": selector_for(el, soup), "text": own, "hidden": hidden})
    visible_blocks = [b for b in blocks if not b["hidden"]]
    hidden_blocks = [b for b in blocks if b["hidden"]]

    controls, seen = [], set()
    for el in body.select(CONTROL_QUERY):
        if in_chrome(el) or in_layer(el) or id(el) in seen or _delegates_to_toggle(el):
            continue
        seen.add(id(el))
        controls.append(
            {"selector": selector_for(el, soup), "text": el.get_text(" ", strip=True)[:40]}
        )

    actionable_controls = []
    for control in controls:
        try:
            locator = sess.page.locator("css=" + control["selector"])
            if locator.count() < 1:
                continue
            info = locator.first.evaluate(GUARD_JS)
        except PlaywrightError:
            continue
        if reject_reason(info) == "":
            actionable_controls.append(control)

    images = [
        {"selector": selector_for(el, soup)}
        for el in body.find_all("img")
        if not in_chrome(el)
        and not in_layer(el)
        and DISCLOSURE_ALT.search(str(el.get("alt") or ""))
    ]

    benefit_blocks = [b for b in visible_blocks if BENEFIT_SIGNAL.search(b["text"])]
    condition_blocks = [b for b in visible_blocks if CONDITION_SIGNAL.search(b["text"])]
    warning_blocks = [b for b in visible_blocks if WARNING_SIGNAL.search(b["text"])]
    footnote_blocks = [b for b in visible_blocks if FOOTNOTE_SIGNAL.search(b["text"])]

    signature = digest(" ".join(b["text"] for b in visible_blocks))

    return {
        "hidden_text_blocks": len(hidden_blocks),
        "visible_text_blocks": len(visible_blocks),
        "candidate_controls": actionable_controls,
        "benefit_samples": [b["text"][:80] for b in benefit_blocks[:5]],
        "warning_samples": [b["text"][:80] for b in warning_blocks[:5]],
        "footnote_samples": [b["text"][:80] for b in footnote_blocks[:5]],
        "signature": signature,
        "hidden_blocks": hidden_blocks,
        "benefit_blocks": benefit_blocks,
        "condition_blocks": condition_blocks,
        "images": images,
    }


def _find(gaps: list[dict], kind: str, target: str) -> dict | None:
    return next((g for g in gaps if g["kind"] == kind and g["target"] == target), None)


def _find_hidden(gaps: list[dict], target: str, text: str) -> dict | None:
    return next(
        (
            g
            for g in gaps
            if g["kind"] == "hidden_text" and g["target"] == target and g.get("text") == text
        ),
        None,
    )


def _new_gap(sess, kind: str, detail: str, target: str, status: str = "open") -> dict:
    gap = {
        "id": f"gap-{len(sess.gaps) + 1}",
        "kind": kind,
        "detail": detail,
        "target": target,
        "status": status,
        "closed_by": "",
    }
    sess.gaps.append(gap)
    return gap


def derive_gaps(sess, obs: dict) -> list[dict]:
    """Update `sess.gaps` in place from one `observe()` call and return it."""
    note = getattr(sess, "last_action_note", "")

    # unexpanded_control: one gap per actionable control not yet targeted by a real expand.
    seen_control_targets = set()
    for control in obs["candidate_controls"]:
        seen_control_targets.add(control["selector"])
        if control["selector"] in sess.tried_expand or _was_clicked(sess, control["selector"]):
            gap = _find(sess.gaps, "unexpanded_control", control["selector"])
            if gap and gap["status"] == "open":
                gap["status"] = "closed"
                gap["closed_by"] = note
            continue
        if _find(sess.gaps, "unexpanded_control", control["selector"]) is None:
            _new_gap(
                sess,
                "unexpanded_control",
                f"{control['text'] or control['selector']} not yet expanded",
                control["selector"],
            )
    # A control that dropped out of the candidate list (already tried) but never got a gap
    # object needs no action; one that is still open and no longer a candidate stays as-is.

    # hidden_text: one gap per hidden block, keyed by selector AND text (a structural selector
    # can match several accordions' panels); closes once that block is no longer hidden.
    hidden_now = {(b["selector"], b["text"]) for b in obs["hidden_blocks"]}
    for block in obs["hidden_blocks"]:
        if _find_hidden(sess.gaps, block["selector"], block["text"]) is None:
            status = "open" if obs["candidate_controls"] else "unresolved"
            detail = f"hidden text: {block['text'][:60]!r}"
            gap = _new_gap(sess, "hidden_text", detail, block["selector"], status)
            gap["text"] = block["text"]
    for gap in sess.gaps:
        if (
            gap["kind"] == "hidden_text"
            and gap["status"] != "closed"
            and (gap["target"], gap.get("text", "")) not in hidden_now
        ):
            gap["status"] = "closed"
            gap["closed_by"] = note

    # benefit_without_condition: reported only, never gates status.
    if obs["benefit_blocks"] and not obs["condition_blocks"]:
        target = obs["benefit_blocks"][0]["selector"]
        if _find(sess.gaps, "benefit_without_condition", target) is None:
            _new_gap(
                sess,
                "benefit_without_condition",
                f"benefit without a visible condition: {obs['benefit_blocks'][0]['text'][:60]!r}",
                target,
            )
    elif obs["condition_blocks"]:
        for gap in sess.gaps:
            if gap["kind"] == "benefit_without_condition" and gap["status"] == "open":
                gap["status"] = "closed"
                gap["closed_by"] = note

    # image_only: always unresolved, text cannot be measured from an image.
    for image in obs["images"]:
        if _find(sess.gaps, "image_only", image["selector"]) is None:
            _new_gap(
                sess,
                "image_only",
                "disclosure wording only found in an image",
                image["selector"],
                "unresolved",
            )

    return sess.gaps


def summarize(obs: dict, sess) -> dict:
    """The `{before, after}` shape reported in `product_page.coverage`."""
    return {
        "hidden_text_blocks": obs["hidden_text_blocks"],
        "visible_text_blocks": obs["visible_text_blocks"],
        "candidate_controls": len(obs["candidate_controls"]),
        "open_gaps": sum(1 for g in sess.gaps if g["status"] != "closed"),
    }


def public_gaps(sess) -> list[dict]:
    """The gap list with internal bookkeeping fields removed, in stable id order."""
    keys = ("id", "kind", "detail", "target", "status", "closed_by")
    return [{k: g[k] for k in keys} for g in sess.gaps]


def _in_region(
    html: str, selector: str, include: list[str], exclude: list[str], text: str = ""
) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    inside, excluded = set(), set()
    for sel in include:
        try:
            inside |= {id(el) for el in soup.select(sel)}
        except Exception:
            continue
    for sel in exclude:
        try:
            excluded |= {id(el) for el in soup.select(sel)}
        except Exception:
            continue
    try:
        found = soup.select(selector)
    except Exception:
        return False
    for el in found:
        if text and _own_text(el) != text:
            continue
        chain = {id(a) for a in [el, *el.parents]}
        if chain & inside and not (chain & excluded):
            return True
    return False


def unreachable_hidden(sess) -> list[dict]:
    """Hidden-text gaps no remaining control could reveal: reported as a limitation only."""
    return [g for g in sess.gaps if g["kind"] == "hidden_text" and g["status"] == "unresolved"]


def finalize_coverage(sess, include: list[str], exclude: list[str]) -> dict:
    """Gaps evaluated against the SUBMITTED regions: the `product_page.status` decision.

    Hidden text lowers the status only while an untried control could still reveal it. Text that
    stays hidden after every reachable control was tried (or when there is none) is excluded:
    its gap becomes `unresolved` and the report lists it as a limitation (user decision,
    2026-09-29)."""
    html = sess.page.content()
    in_scope = [
        gap
        for gap in sess.gaps
        if gap["kind"] in ACTIONABLE_KINDS
        and gap["status"] != "closed"
        and _in_region(html, gap["target"], include, exclude, gap.get("text", ""))
    ]
    untried = [
        gap for gap in sess.gaps if gap["kind"] == "unexpanded_control" and gap["status"] == "open"
    ]
    remaining = [gap for gap in in_scope if gap["kind"] == "unexpanded_control"]
    if untried:
        remaining += [gap for gap in in_scope if gap["kind"] == "hidden_text"]
    unreachable = [] if untried else [gap for gap in in_scope if gap["kind"] == "hidden_text"]
    for gap in unreachable:
        gap["status"] = "unresolved"
    if remaining:
        status = "조사 불충분"
        if sess.exploration_closed:
            stop_reason = sess.exploration_closed
        elif not any(gap["kind"] == "unexpanded_control" for gap in remaining):
            stop_reason = "no_viable_control"
        else:
            stop_reason = "submitted_with_gaps"
    else:
        status = "완료"
        stop_reason = "reachable_coverage" if unreachable else "full_coverage"
    return {"status": status, "stop_reason": stop_reason}
