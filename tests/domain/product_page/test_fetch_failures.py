"""The failure paths of fetch_product_page, with the browser and the agent faked out.

fetch_product_page never raises for a page/agent failure: it returns a result whose `status`
and `stop_reason` name what went wrong (see docs/agent-node-specs/product_page.md).
"""

import pytest

from financial_disclosure_review.core.context import Context
from financial_disclosure_review.core.usage import BudgetError
from financial_disclosure_review.domain.product_page import fetch as fetch_module
from financial_disclosure_review.domain.product_page.discover import TurnsExhaustedError
from financial_disclosure_review.domain.product_page.fetch import (
    ReplayFailedError,
    fetch_product_page,
    visit,
)
from financial_disclosure_review.domain.product_page.session import (
    PageBlocked,
    PageUnavailable,
    VisitCapReached,
    error_page,
)

URL = "https://www.example-card.co.kr/card/credit/info"


class FakeSession:
    """The part of PageSession `visit` touches."""

    def __init__(self) -> None:
        self.phase = ""
        self.last_html = "<html><body><h1>카드</h1></body></html>"
        self.visits = 0
        self.model_calls = 0
        self.snapshots: list = []
        self.actions: list = []
        self.agent_trace: list = []
        self.logged: list[tuple[str, dict]] = []
        self.opened: list[str] = []
        self.coverage_before: dict = {}
        self.coverage_after: dict = {}
        self.final_coverage: dict | None = None
        self.gaps: list = []

    def viewport_key(self) -> str:
        return "1280x800"

    def goto(self, url: str) -> None:
        self.opened.append(url)

    def log(self, kind: str, **fields) -> None:
        self.logged.append((kind, fields))


def test_a_private_address_is_refused_before_a_browser_starts(monkeypatch, tmp_path):
    def no_browser():
        raise AssertionError("the browser must not start for a refused URL")

    monkeypatch.setattr(fetch_module, "sync_playwright", no_browser)
    page = fetch_product_page(
        "http://169.254.169.254/latest/meta-data/", Context(data_dir=str(tmp_path))
    )
    assert page["status"] == "수집 실패"
    assert page["stop_reason"] == "invalid_url"
    assert "non-public address" in page["error"]
    assert page["html"] == ""


def test_an_allow_list_is_refused_before_a_browser_starts(monkeypatch, tmp_path):
    def no_browser():
        raise AssertionError("the browser must not start for a refused URL")

    monkeypatch.setattr(fetch_module, "sync_playwright", no_browser)
    page = fetch_product_page(
        "https://8.8.8.8/card",
        Context(data_dir=str(tmp_path), allowed_hosts=("lottecard.co.kr",)),
    )
    assert page["status"] == "수집 실패"
    assert page["stop_reason"] == "invalid_url"
    assert "not in the allowed list" in page["error"]


def test_a_discovered_rule_that_fails_its_own_replay_raises_replay_failed(monkeypatch, tmp_path):
    monkeypatch.setattr(
        fetch_module, "discover", lambda sess, ctx, chat=None: {"include": ["main"]}
    )
    monkeypatch.setattr(
        fetch_module,
        "finalize_rule",
        lambda sess, proposal: ({"include": ["main"]}, {"pieces": [], "states": 1, "html": ""}),
    )
    monkeypatch.setattr(fetch_module, "validate_output", lambda rule, content: ["html is empty"])
    saved: list = []
    monkeypatch.setattr(fetch_module, "save_rule", lambda path, rule: saved.append(path))
    sess = FakeSession()

    with pytest.raises(ReplayFailedError, match="failed validation"):
        visit(sess, URL, Context(data_dir=str(tmp_path)), tmp_path / "rules")  # type: ignore[arg-type]

    assert saved == [], "a rule that failed validation must not be stored for reuse"
    assert (
        "uncertain",
        {
            "key": f"www.example-card.co.kr | {fetch_module.page_family(URL)} | 1280x800",
            "reasons": ["html is empty"],
        },
    ) in sess.logged


def test_a_saved_rule_that_no_longer_fits_the_page_falls_back_to_rediscovery(monkeypatch, tmp_path):
    monkeypatch.setattr(fetch_module, "load_rule", lambda path: {"include": ["#old"]})
    monkeypatch.setattr(fetch_module, "check_rule", lambda html, rule: ["#old matches nothing"])
    discovered: list = []

    def fake_discover(sess, ctx, chat=None):
        discovered.append(sess.phase)
        return {"include": ["main"]}

    monkeypatch.setattr(fetch_module, "discover", fake_discover)
    monkeypatch.setattr(
        fetch_module,
        "finalize_rule",
        lambda sess, proposal: ({"include": ["main"]}, {"pieces": [], "states": 1, "html": ""}),
    )
    monkeypatch.setattr(fetch_module, "validate_output", lambda rule, content: ["still empty"])
    sess = FakeSession()

    with pytest.raises(ReplayFailedError):
        visit(sess, URL, Context(data_dir=str(tmp_path)), tmp_path / "rules")  # type: ignore[arg-type]

    assert discovered == ["discover"], "the stale rule is dropped and the page rediscovered once"
    assert sess.opened == [URL, URL], "the page is reloaded before rediscovery"
    assert any(kind == "drift" and fields["stage"] == "structure" for kind, fields in sess.logged)


def test_a_blocked_page_comes_back_as_a_fetch_failure(monkeypatch, tmp_path):
    class BlockingSession:
        def __init__(self, playwright, url, ctx):
            self.actions, self.snapshots, self.agent_trace = [], [], []
            self.model_calls, self.visits = 0, 0
            self.coverage_before, self.gaps = {}, []

        def log(self, kind, **fields):
            self.actions.append({"type": kind, **fields})

        def close(self):
            pass

    monkeypatch.setattr(fetch_module, "url_problem", lambda url, allowed: "")
    monkeypatch.setattr(fetch_module, "PageSession", BlockingSession)

    def fake_visit(sess, url, ctx, rules_dir, chat_factory=None):
        raise PageBlocked("HTTP 403 for " + url)

    monkeypatch.setattr(fetch_module, "visit", fake_visit)

    page = fetch_product_page(URL, Context(data_dir=str(tmp_path)))
    assert page["status"] == "수집 실패"
    assert page["stop_reason"] == "fetch_error"
    assert "403" in page["error"]
    assert page["html"] == ""


def test_a_visit_cap_comes_back_as_a_fetch_failure(monkeypatch, tmp_path):
    class CappedSession:
        def __init__(self, playwright, url, ctx):
            self.actions, self.snapshots, self.agent_trace = [], [], []
            self.model_calls, self.visits = 0, 0
            self.coverage_before, self.gaps = {}, []

        def log(self, kind, **fields):
            self.actions.append({"type": kind, **fields})

        def close(self):
            pass

    monkeypatch.setattr(fetch_module, "url_problem", lambda url, allowed: "")
    monkeypatch.setattr(fetch_module, "PageSession", CappedSession)

    def fake_visit(sess, url, ctx, rules_dir, chat_factory=None):
        raise VisitCapReached("page visit cap of 3 reached")

    monkeypatch.setattr(fetch_module, "visit", fake_visit)

    page = fetch_product_page(URL, Context(data_dir=str(tmp_path)))
    assert page["status"] == "수집 실패"
    assert page["stop_reason"] == "visit_cap"


def test_turns_exhausted_comes_back_as_an_incomplete_review(monkeypatch, tmp_path):
    class ExhaustedSession:
        def __init__(self, playwright, url, ctx):
            self.actions, self.snapshots, self.agent_trace = [], [], []
            self.model_calls, self.visits = 0, 0
            self.coverage_before, self.gaps = {}, []

        def log(self, kind, **fields):
            self.actions.append({"type": kind, **fields})

        def close(self):
            pass

    monkeypatch.setattr(fetch_module, "url_problem", lambda url, allowed: "")
    monkeypatch.setattr(fetch_module, "PageSession", ExhaustedSession)

    def fake_visit(sess, url, ctx, rules_dir, chat_factory=None):
        raise TurnsExhaustedError("agent used all 20 turns without an accepted rule")

    monkeypatch.setattr(fetch_module, "visit", fake_visit)

    page = fetch_product_page(URL, Context(data_dir=str(tmp_path)))
    assert page["status"] == "조사 불충분"
    assert page["stop_reason"] == "max_turns"
    assert page["html"] == ""


def test_budget_exhausted_comes_back_as_an_incomplete_review(monkeypatch, tmp_path):
    class BudgetedSession:
        def __init__(self, playwright, url, ctx):
            self.actions, self.snapshots, self.agent_trace = [], [], []
            self.model_calls, self.visits = 0, 0
            self.coverage_before, self.gaps = {}, []

        def log(self, kind, **fields):
            self.actions.append({"type": kind, **fields})

        def close(self):
            pass

    monkeypatch.setattr(fetch_module, "url_problem", lambda url, allowed: "")
    monkeypatch.setattr(fetch_module, "PageSession", BudgetedSession)

    def fake_visit(sess, url, ctx, rules_dir, chat_factory=None):
        raise BudgetError("run budget $1.0 reached")

    monkeypatch.setattr(fetch_module, "visit", fake_visit)

    page = fetch_product_page(URL, Context(data_dir=str(tmp_path)))
    assert page["status"] == "조사 불충분"
    assert page["stop_reason"] == "budget_exhausted"


def test_a_rule_that_cannot_be_written_does_not_fail_the_review(monkeypatch, tmp_path):
    """2026-09-29 실측: 긴 경로 때문에 규칙 파일 저장이 실패하자 수집한 본문까지 버리고 그래프가
    멈췄습니다. 규칙은 다음 방문의 재사용용일 뿐이므로 저장 실패는 기록만 남깁니다."""
    rule = {"include": ["main"], "product_name": "카드", "summary": "", "evidence": []}
    monkeypatch.setattr(fetch_module, "discover", lambda sess, ctx, chat=None: dict(rule))
    content = {"pieces": [{"text": "본문"}], "states": 1, "html": "<main>본문</main>"}
    monkeypatch.setattr(fetch_module, "finalize_rule", lambda sess, proposal: (proposal, content))
    monkeypatch.setattr(fetch_module, "validate_output", lambda rule, content: [])

    def unwritable(path, rule):
        raise FileNotFoundError(2, "No such file or directory", str(path))

    monkeypatch.setattr(fetch_module, "save_rule", unwritable)
    sess = FakeSession()
    result = visit(sess, URL, Context(data_dir=str(tmp_path)), tmp_path / "rules")  # type: ignore[arg-type]
    assert result["html"] == "<main>본문</main>"
    assert any(kind == "rule_not_saved" for kind, _ in sess.logged)


def test_a_page_that_turned_into_a_browser_error_comes_back_as_unavailable(monkeypatch, tmp_path):
    """2026-09-29 KB 카드론: the page became chrome-error:// and the agent guessed selectors
    for 20 turns. It is a collection failure, reported as such."""

    class Session:
        def __init__(self, playwright, url, ctx):
            self.actions, self.snapshots, self.agent_trace = [], [], []
            self.model_calls, self.visits = 0, 0
            self.coverage_before, self.gaps = {}, []

        def log(self, kind, **fields):
            self.actions.append({"type": kind, **fields})

        def close(self):
            pass

    monkeypatch.setattr(fetch_module, "url_problem", lambda url, allowed: "")
    monkeypatch.setattr(fetch_module, "PageSession", Session)

    def fake_visit(sess, url, ctx, rules_dir, chat_factory=None):
        raise PageUnavailable("the page became chrome-error://chromewebdata/")

    monkeypatch.setattr(fetch_module, "visit", fake_visit)
    page = fetch_product_page(URL, Context(data_dir=str(tmp_path)))
    assert page["status"] == "수집 실패"
    assert page["stop_reason"] == "page_unavailable"
    assert "chrome-error" in page["error"]


def test_discovery_stops_before_a_model_turn_on_a_browser_error_page(monkeypatch):
    from types import SimpleNamespace

    from financial_disclosure_review.domain.product_page import discover as discover_module
    from tests.domain.product_page.fake_chat import ScriptedChat

    monkeypatch.setattr(discover_module.coverage, "observe", lambda sess: {})
    monkeypatch.setattr(discover_module.coverage, "derive_gaps", lambda sess, obs: None)
    monkeypatch.setattr(discover_module.coverage, "summarize", lambda obs, sess: {})
    sess = SimpleNamespace(
        url=URL,
        page=SimpleNamespace(url="chrome-error://chromewebdata/"),
        visits=1,
        exploration_closed="",
        model_calls=0,
        agent_trace=[],
        coverage_before={},
    )
    chat = ScriptedChat([[{"name": "inspect_page", "args": {}}]])
    with pytest.raises(PageUnavailable, match="chrome-error"):
        discover_module.discover(sess, Context(), chat=chat)  # type: ignore[arg-type]
    assert chat.step == 0
    assert sess.model_calls == 0


@pytest.mark.parametrize(
    ("url", "unavailable"),
    [
        ("chrome-error://chromewebdata/", True),
        ("about:blank", False),
        ("https://card.kbcard.com/FNC/DVIEW/HFAMCXPRIFIC0038", False),
    ],
)
def test_error_page_urls_are_recognized(url, unavailable):
    assert bool(error_page(url)) is unavailable
