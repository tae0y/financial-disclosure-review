"""The failure paths of fetch_product_page, with the browser and the agent faked out."""

import pytest

from financial_disclosure_review.core.context import Context
from financial_disclosure_review.domain.product_page import fetch as fetch_module
from financial_disclosure_review.domain.product_page.fetch import fetch_product_page, visit

URL = "https://www.example-card.co.kr/card/credit/info"


class FakeSession:
    """The part of PageSession `visit` touches."""

    def __init__(self) -> None:
        self.phase = ""
        self.last_html = "<html><body><h1>카드</h1></body></html>"
        self.visits = 0
        self.model_calls = 0
        self.snapshots: list = []
        self.logged: list[tuple[str, dict]] = []
        self.opened: list[str] = []

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
    with pytest.raises(ValueError, match="non-public address"):
        fetch_product_page(
            "http://169.254.169.254/latest/meta-data/", Context(data_dir=str(tmp_path))
        )


def test_an_allow_list_is_refused_before_a_browser_starts(monkeypatch, tmp_path):
    def no_browser():
        raise AssertionError("the browser must not start for a refused URL")

    monkeypatch.setattr(fetch_module, "sync_playwright", no_browser)
    with pytest.raises(ValueError, match="not in the allowed list"):
        fetch_product_page(
            "https://8.8.8.8/card",
            Context(data_dir=str(tmp_path), allowed_hosts=("lottecard.co.kr",)),
        )


def test_a_discovered_rule_that_fails_its_own_replay_raises_and_saves_nothing(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(fetch_module, "discover", lambda sess, ctx: {"include": ["main"]})
    monkeypatch.setattr(
        fetch_module,
        "finalize_rule",
        lambda sess, proposal: ({"include": ["main"]}, {"pieces": [], "states": 1, "html": ""}),
    )
    monkeypatch.setattr(fetch_module, "validate_output", lambda rule, content: ["html is empty"])
    saved: list = []
    monkeypatch.setattr(fetch_module, "save_rule", lambda path, rule: saved.append(path))
    sess = FakeSession()

    with pytest.raises(RuntimeError, match="failed validation"):
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

    def fake_discover(sess, ctx):
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

    with pytest.raises(RuntimeError):
        visit(sess, URL, Context(data_dir=str(tmp_path)), tmp_path / "rules")  # type: ignore[arg-type]

    assert discovered == ["discover"], "the stale rule is dropped and the page rediscovered once"
    assert sess.opened == [URL, URL], "the page is reloaded before rediscovery"
    assert any(kind == "drift" and fields["stage"] == "structure" for kind, fields in sess.logged)
