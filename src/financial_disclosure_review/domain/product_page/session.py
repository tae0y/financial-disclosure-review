"""One live browser session: navigation guards, safe clicks, and whole-page snapshots."""

import base64
import re
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError

from ...core.color import contrast_ratio
from ...core.context import Context
from ...core.text import digest
from ...core.urls import url_problem
from .html import extract_pieces

SNAPSHOT_STYLES = [
    "font-size",
    "font-weight",
    "color",
    "display",
    "visibility",
    "opacity",
    "background-color",
    "background-image",
]
SKIP_TAGS = {"script", "style", "noscript", "template", "head", "title", "meta", "link"}


def bounds_overlap(a: list[float], b: list[float]) -> bool:
    return min(a[0] + a[2], b[0] + b[2]) > max(a[0], b[0]) and min(a[1] + a[3], b[1] + b[3]) > max(
        a[1], b[1]
    )


class SnapshotIndex:
    """Reads a whole-page CDP DOMSnapshot: own text, computed style and bounds per element."""

    def __init__(self, snap: dict):
        self.strings = snap["strings"]
        doc = snap["documents"][0]
        nodes, layout = doc["nodes"], doc["layout"]
        self.size = {"width": doc.get("contentWidth"), "height": doc.get("contentHeight")}
        self.names = [self.text(i).lower() for i in nodes["nodeName"]]
        self.kinds, self.parents = nodes["nodeType"], nodes["parentIndex"]
        self.values, self.backend = nodes["nodeValue"], nodes["backendNodeId"]
        self.by_backend = {b: i for i, b in enumerate(self.backend)}
        self.children = defaultdict(list)
        for i, parent in enumerate(self.parents):
            self.children[parent].append(i)
        self.layout = {
            n: (box, style)
            for n, box, style in zip(layout["nodeIndex"], layout["bounds"], layout["styles"])
        }
        # Blended background per layout node (colors of overlapping elements composited).
        self.blended = {
            n: self.text(b)
            for n, b in zip(layout["nodeIndex"], layout.get("blendedBackgroundColors", []))
            if b >= 0
        }
        self.skipped = []
        for i, name in enumerate(self.names):
            parent = self.parents[i]
            self.skipped.append(name in SKIP_TAGS or (parent >= 0 and self.skipped[parent]))

    def text(self, index: int) -> str:
        return self.strings[index] if index >= 0 else ""

    def own_text(self, i: int) -> str:
        parts = [self.text(self.values[c]) for c in self.children[i] if self.kinds[c] == 3]
        return " ".join(" ".join(parts).split())

    def text_elements(self, root: int | None = None) -> list[int]:
        """Elements that hold text nodes of their own, in the subtree of root (or the page)."""
        stack, found = [root if root is not None else 0], []
        order = []
        while stack:
            i = stack.pop()
            order.append(i)
            stack.extend(reversed(self.children[i]))
        for i in order:
            if self.kinds[i] == 1 and not self.skipped[i] and self.own_text(i):
                found.append(i)
        return found

    def row(self, i: int, text_limit: int = 120) -> dict:
        box, style = self.layout.get(i, (None, None))
        values = [self.text(s) for s in style] if style else [None] * len(SNAPSHOT_STYLES)
        size, weight, color, display, visibility, opacity, _background, _background_image = values
        visible = bool(
            box
            and box[2] > 0
            and box[3] > 0
            and display != "none"
            and visibility != "hidden"
            and opacity != "0"
        )
        return {
            "tag": self.names[i],
            "text": self.own_text(i)[:text_limit],
            "font_size": size,
            "font_weight": weight,
            "color": color,
            "visible": visible,
            "bounds": [round(v, 1) for v in box] if box else None,
            "path": self.css_path(i),
            "background": self.background(i),
            "background_source": "blended" if self.blended_of(i) else "ancestor",
            "background_image": self.background_image(i),
        }

    def blended_of(self, i: int) -> str | None:
        """Blended background of the element, when the capture provides it."""
        return self.blended.get(i)

    def background_image(self, i: int) -> bool:
        """A CSS image or gradient here or on an ancestor invalidates flat-color contrast."""
        while i >= 0:
            _, style = self.layout.get(i, (None, None))
            value = self.text(style[7]) if style and len(style) > 7 else ""
            if value and value != "none":
                return True
            i = self.parents[i]
        return False

    def background(self, i: int) -> str | None:
        """Blended background if captured; otherwise the nearest non-transparent ancestor color."""
        if self.blended_of(i):
            return self.blended_of(i)
        while i >= 0:
            _, style = self.layout.get(i, (None, None))
            color = self.text(style[6]) if style else ""
            if color and color != "rgba(0, 0, 0, 0)":
                return color
            i = self.parents[i]
        return None

    def image_bounds(self) -> list[dict]:
        """Visible img geometry in the same page coordinates as text layout bounds."""
        return [
            {"bounds": [round(v, 1) for v in self.layout[i][0]]}
            for i, name in enumerate(self.names)
            if name == "img"
            and i in self.layout
            and self.layout[i][0][2] > 0
            and self.layout[i][0][3] > 0
        ]

    def rows(self) -> list[dict]:
        return [self.row(i) for i in self.text_elements()]

    def css_path(self, i: int) -> str:
        parts = []
        while i > 0 and self.kinds[i] == 1 and self.names[i] not in ("html",):
            siblings = self.children[self.parents[i]]
            same = [c for c in siblings if self.kinds[c] == 1 and self.names[c] == self.names[i]]
            parts.append(f"{self.names[i]}:nth-of-type({same.index(i) + 1})")
            i = self.parents[i]
        return " > ".join(["html"] + list(reversed(parts)))


class PageBlocked(RuntimeError):  # noqa: N818 - moved from the notebook unrenamed
    """The site refused or did not render the page. Never bypassed."""


class PageUnavailable(PageBlocked):  # noqa: N818 - named like its parent
    """The page turned into a browser error page after arrival; no agent turn can collect
    anything from it."""


def error_page(url: str) -> str:
    """Why this address is Chromium's error page, or "" otherwise. (`about:blank` is not
    treated as an error: offline pages are rendered there with set_content.)"""
    if url.startswith("chrome-error://"):
        return f"the page became a browser error page ({url})"
    return ""


class VisitCapReached(RuntimeError):  # noqa: N818 - moved from the notebook unrenamed
    pass


# An action word followed by one of these nouns names information, not the action itself:
# "결제일 할인", "신청 방법", "발급 대상" open an explanation; "결제하기", "카드 신청" do not.
INFO_SUFFIX = (
    r"(?!\s*(?:일|금액|대금|계좌|방법|방식|수단|예정|내역|조건|대상|자격|기준|안내|절차|서류"
    r"|시|전|후))"
)
RISKY_TEXT = re.compile(
    rf"(?:신청|발급|가입|결제|주문){INFO_SUFFIX}|로그인|제출|다운로드"
    r"|찜|좋아요|담기|비교|공유|상담|알림|전화|쿠폰|응모|참여|동의"
    r"|apply|log ?in|sign ?(in|up)|submit|download|order|pay",
    re.I,
)
EXPANDER_CLASS = re.compile(r"tab|acc|toggle|collaps|fold|more|open|drop", re.I)
DOWNLOAD_EXT = (
    ".pdf",
    ".zip",
    ".xls",
    ".xlsx",
    ".doc",
    ".docx",
    ".hwp",
    ".hwpx",
    ".ppt",
    ".pptx",
    ".csv",
)
MAX_CLICKS = 30
GUARD_JS = r"""(e) => {
  const tokens = (el) => String((el && el.className) || '').split(/\s+/);
  const type = (e.getAttribute('type') || '').toLowerCase();
  const parent = e.parentElement;
  // A DaisyUI-style accordion toggle: a checkbox/radio that is a direct child of a `.collapse`
  // container and outside any form. Checking it only toggles CSS; nothing is submitted.
  const collapseToggle = e.tagName === 'INPUT' && (type === 'checkbox' || type === 'radio')
    && tokens(parent).includes('collapse') && !e.closest('form');
  const title = collapseToggle
    && parent.querySelector(':scope > .collapse-title, :scope > [class*=collapse-title]');
  // Wording is checked on the control's own label: for an accordion toggle that is its title,
  // never the panel it opens (a panel may mention 결제 or 신청 without being an action).
  const label = collapseToggle ? (title ? title.innerText : (e.getAttribute('aria-label') || ''))
    : (e.innerText || e.getAttribute('aria-label') || '');
  return {
    tag: e.tagName.toLowerCase(), type: type,
    href: e.getAttribute('href') || '', cls: String(e.className || ''),
    expandable: e.hasAttribute('aria-expanded') || e.hasAttribute('aria-controls')
      || e.tagName === 'SUMMARY' || e.getAttribute('role') === 'tab',
    collapse_toggle: collapseToggle,
    checked: collapseToggle ? !!e.checked : false,
    in_form: !!e.closest('form'),
    text: label.trim().slice(0, 60),
    visible: !!(e.offsetWidth || e.offsetHeight)
  };
}"""
# `.collapse-title` and a `.collapse` container are clicked through their toggle input: the input
# is layered over the title, so a real click on the title lands on it anyway.
CLICK_TARGET_JS = r"""(e) => {
  const tokens = (el) => String((el && el.className) || '').split(/\s+/);
  const box = tokens(e).includes('collapse') ? e
    : (tokens(e).some(t => t.includes('collapse-title')) ? e.parentElement : null);
  const toggle = box && tokens(box).includes('collapse')
    && box.querySelector(':scope > input[type=checkbox], :scope > input[type=radio]');
  return toggle || e;
}"""
MARK_CLICKED_JS = """(e) => {
  window.__fdrClicked = window.__fdrClicked || new WeakSet();
  window.__fdrClicked.add(e);
}"""


def reject_reason(info: dict) -> str:
    """Why an element may not be clicked; empty when it is a safe tab/accordion expander."""
    href = info["href"].strip().lower()
    in_page_link = href in ("", "#") or href.startswith(("#", "javascript:"))
    if info["in_form"]:
        return "form control"
    if info["tag"] in ("input", "select", "textarea") and not info.get("collapse_toggle"):
        return "form control"
    if info["type"] in ("submit", "reset", "file", "password"):
        return "form control"
    if RISKY_TEXT.search(info["text"]):
        return "apply/login/submit/download wording"
    if info["tag"] == "a" and not in_page_link:
        return "navigation link (use open_link)"
    # aria-expanded/aria-controls/role=tab/<summary> are already covered by `expandable`
    # (see GUARD_JS below). A plain <button> or <div> with none of those markers is not an
    # expander: clicking it could trigger an unrelated action (wishlist, compare, share, ...).
    if not (
        info["expandable"]
        or info.get("collapse_toggle")
        or (info["tag"] == "a" and in_page_link)
        or EXPANDER_CLASS.search(info["cls"])
    ):
        return "not an expander"
    return "" if info["visible"] else "not visible"


class PageSession:
    """One Playwright browser, page and CDP session. Lives in a single worker thread."""

    def __init__(self, playwright, url: str, ctx: Context):
        self.ctx, self.url = ctx, url
        self.browser = playwright.chromium.launch()
        self.context = self.browser.new_context(
            viewport={"width": ctx.viewport_width, "height": ctx.viewport_height},
            locale="ko-KR",
            accept_downloads=False,
        )
        self.context.on("page", lambda popup: popup.close() if popup.opener() else None)
        self.page = self.context.new_page()
        self.page.on("dialog", lambda dialog: dialog.dismiss())
        self.page.on("download", lambda download: download.cancel())
        self.page.route("**/*", self.guard_navigation)
        self.cdp = self.context.new_cdp_session(self.page)
        self.allow_nav = False
        self.blocked: list[str] = []
        self.actions: list[dict] = []
        self.snapshots: list[dict] = []
        self.states: list[list[dict]] = []
        self.view: tuple[list[str], list[str]] | None = None
        self.last_sig, self.last_html = None, ""
        self.visits, self.model_calls = 0, 0
        self.on_linked, self.phase = False, "discover"
        self.pending: dict | None = None
        self.probed: set[str] = set()
        self.controls_seen, self.expand_tried, self.nudged = 0, False, False
        self.outside_reviewed = False
        self.run_id = datetime.now().strftime("%y%m%d-%H%M%S")
        # Coverage-gap bookkeeping (Stage 1): gaps persist for the life of one visit.
        self.gaps: list[dict] = []
        self.exploration_closed = ""
        self.interactions_count = 0
        self.no_progress_count = 0
        self.tried_actions: set[tuple[str, str]] = set()
        self.tried_expand: set[str] = set()
        # submit_rule sent back once for untried controls inside the submitted regions.
        self.region_nudged = False
        self.agent_trace: list[dict] = []
        self.last_action_note = ""
        self.coverage_before: dict = {}
        self.coverage_after: dict = {}
        self.final_coverage: dict | None = None
        self.interacting = False

    def close(self):
        self.browser.close()

    def log(self, kind: str, **fields):
        self.actions.append({"type": kind, **fields})

    def guard_navigation(self, route):
        request = route.request
        try:
            main_frame = request.is_navigation_request() and request.frame == self.page.main_frame
        except PlaywrightError:
            main_frame = False
        if not main_frame:
            # While a click or open_link/go_back is in progress, only GET/HEAD sub-requests may
            # leave the browser -- a click must never fire a POST (wishlist, like, apply, ...).
            # The initial page render is unaffected because `interacting` starts False.
            if self.interacting and request.method not in ("GET", "HEAD"):
                self.blocked.append(request.url)
                self.log("blocked_request", url=request.url, method=request.method)
                route.abort()
                return
            # fallback() (not continue_()) so a route registered on the browser context by a
            # test can still fulfil the request with local content.
            route.fallback()
            return

        # A redirect is another main-frame request. Validate it before it leaves the browser,
        # not just after page.goto() returns, so a public URL cannot pivot the worker to a
        # loopback, private, link-local or allow-list-excluded destination.
        problem = url_problem(request.url, self.ctx.allowed_hosts)
        if problem:
            self.blocked.append(request.url)
            self.log("blocked_navigation", url=request.url, reason=problem)
            route.abort()
            return
        if not self.allow_nav:
            self.blocked.append(request.url)
            self.log("blocked_navigation", url=request.url, reason="not requested by the reviewer")
            route.abort()
            return
        route.fallback()

    @contextmanager
    def interacting_window(self):
        """Non-GET/HEAD sub-requests are aborted while a guarded click or navigation runs."""
        self.interacting = True
        try:
            yield
        finally:
            self.interacting = False

    def viewport(self) -> dict:
        return dict(self.page.viewport_size)

    def viewport_key(self) -> str:
        return f"{self.ctx.viewport_width}x{self.ctx.viewport_height}"

    def goto(self, url: str, count: bool = True):
        if count:
            if self.visits >= self.ctx.max_visits:
                raise VisitCapReached(f"page visit cap of {self.ctx.max_visits} reached")
            self.visits += 1
        self.allow_nav = True
        try:
            response = self.page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        except PlaywrightError as error:
            raise PageBlocked(
                f"navigation failed for {url}: {str(error).splitlines()[0]}"
            ) from error
        finally:
            self.allow_nav = False
        problem = url_problem(self.page.url, self.ctx.allowed_hosts)
        if problem:
            raise PageBlocked(f"navigation landed on refused URL {self.page.url}: {problem}")
        if response is not None and response.status >= 400:
            raise PageBlocked(f"HTTP {response.status} {response.status_text} for {url}")
        try:
            self.page.wait_for_function(
                "document.body && document.body.innerText.trim().length > 200", timeout=15_000
            )
        except PlaywrightError as error:
            head = self.page.inner_text("body")[:200] if self.page.query_selector("body") else ""
            raise PageBlocked(
                f"no rendered text within 15s for {url}; title={self.page.title()!r}; body={head!r}"
            ) from error
        self.scroll_through()
        self.last_sig = None
        self.snapshot("default", f"arrived {self.page.url}")

    def scroll_through(self):
        """Scroll to the bottom and back so lazy content renders. A page that reloads itself
        right after arriving destroys the script context; wait for it to settle and retry once."""
        try:
            self._scroll_through()
        except PlaywrightError as error:
            if "context was destroyed" not in str(error):
                raise
            self.log("self_navigation", url=self.page.url)
            self.page.wait_for_load_state("load", timeout=15_000)
            self._scroll_through()

    def _scroll_through(self):
        step = self.ctx.viewport_height * 0.8
        for _ in range(60):
            bottom, total = self.page.evaluate(
                "[window.scrollY + window.innerHeight, document.documentElement.scrollHeight]"
            )
            if bottom >= total - 2:
                break
            self.page.mouse.wheel(0, step)
            self.page.wait_for_timeout(200)
        self.page.evaluate("window.scrollTo(0, 0)")
        self.page.wait_for_timeout(200)

    def scroll_step(self) -> dict:
        self.page.mouse.wheel(0, self.ctx.viewport_height * 0.8)
        self.page.wait_for_timeout(250)
        y, total = self.page.evaluate("[window.scrollY, document.documentElement.scrollHeight]")
        return {"scroll_y": round(y), "page_height": total}

    def dom_snapshot(self) -> SnapshotIndex:
        snap = self.cdp.send(
            "DOMSnapshot.captureSnapshot",
            {"computedStyles": SNAPSHOT_STYLES, "includeBlendedBackgroundColors": True},
        )
        return SnapshotIndex(snap)

    def signature(self) -> str:
        return digest(self.page.inner_text("body"))

    def capture_visual_samples(self, rows: list[dict]) -> dict[str, str]:
        """Save rendered PNGs in State so judgment can replay from a checkpoint."""
        samples = {}
        candidates = [r for r in rows if r["visible"] and r["visual_risk"]]
        candidates.sort(key=lambda r: contrast_ratio(r["color"], r["background"]) or 99)
        for row in candidates[: self.ctx.display_max_visual_crops]:
            try:
                locator = self.page.locator(row["path"])
                if locator.count() != 1:
                    continue
                locator.scroll_into_view_if_needed(timeout=3_000)
                unobscured = locator.evaluate("""e => {
                    const r = e.getBoundingClientRect();
                    const x = Math.min(innerWidth - 1, Math.max(0, r.left + r.width / 2));
                    const y = Math.min(innerHeight - 1, Math.max(0, r.top + r.height / 2));
                    const top = document.elementFromPoint(x, y);
                    return r.width > 0 && r.height > 0 && r.top >= 0 && r.bottom <= innerHeight
                        && !!top && e.contains(top);
                }""")
                if unobscured:
                    png = locator.screenshot(timeout=5_000)
                    samples[row["path"]] = base64.b64encode(png).decode()
            except PlaywrightError:
                continue
        return samples

    def snapshot(self, kind: str, note: str) -> dict:
        """Whole-page snapshot: rendered style rows for every text element plus the page HTML."""
        index = self.dom_snapshot()
        self.last_sig, self.last_html = self.signature(), self.page.content()
        number = len(self.snapshots) + 1
        path = Path(self.ctx.data_dir) / "snapshots" / f"{self.run_id}-{number:02d}.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.last_html)
        rows = index.rows()
        images = index.image_bounds()
        for row in rows:
            row["visual_risk"] = [
                *(["background_image"] if row["background_image"] else []),
                *(
                    ["image_overlap"]
                    if row["bounds"]
                    and any(bounds_overlap(row["bounds"], image["bounds"]) for image in images)
                    else []
                ),
            ]
        samples = self.capture_visual_samples(rows) if self.phase == "render" else {}
        entry = {
            "id": number,
            "phase": self.phase,
            "kind": kind,
            "note": note,
            "url": self.page.url,
            "viewport": self.viewport(),
            "document": index.size,
            "html_path": str(path),
            "styles": rows,
            "images": images,
            "visual_samples": samples,
        }
        self.snapshots.append(entry)
        if self.view:
            self.states.append(extract_pieces(self.last_html, *self.view))
        return entry

    def snapshot_if_changed(self, kind: str, note: str) -> dict | None:
        return None if self.signature() == self.last_sig else self.snapshot(kind, note)

    def match_count(self, selector: str) -> tuple[int, str]:
        try:
            return self.page.locator("css=" + selector).count(), ""
        except PlaywrightError as error:
            return 0, str(error).splitlines()[0][:120]

    def click_matches(self, selector: str, kind: str) -> dict:
        """Click every safe expander that matches; snapshot each content-changing click."""
        locator = self.page.locator("css=" + selector)
        total, _ = self.match_count(selector)
        report = {"matched": total, "clicked": 0, "new_states": 0, "skipped": []}
        with self.interacting_window():
            for i in range(min(total, MAX_CLICKS)):
                try:
                    element = locator.nth(i).evaluate_handle(CLICK_TARGET_JS).as_element()
                    assert element is not None
                    info = element.evaluate(GUARD_JS)
                except (PlaywrightError, AssertionError) as error:
                    report["skipped"].append(
                        {"index": i, "reason": str(error).splitlines()[0][:60] or "no element"}
                    )
                    continue
                reason = reject_reason(info) or ("already open" if info.get("checked") else "")
                if reason:
                    report["skipped"].append(
                        {"index": i, "reason": reason, "text": info["text"][:30]}
                    )
                    continue
                try:
                    element.scroll_into_view_if_needed(timeout=2_000)
                    element.click(timeout=3_000)
                    self.page.wait_for_timeout(300)
                except PlaywrightError as error:
                    report["skipped"].append(
                        {"index": i, "reason": "click failed: " + str(error).splitlines()[0][:60]}
                    )
                    continue
                report["clicked"] += 1
                element.evaluate(MARK_CLICKED_JS)
                if self.snapshot_if_changed(kind, f"expand {selector}[{i}] {info['text'][:20]!r}"):
                    report["new_states"] += 1
        report["skipped"] = report["skipped"][:6]
        if self.blocked:
            report["blocked_navigation"] = self.blocked[-3:]
        return report
