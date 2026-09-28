"""Stage 1: the bounded page-evidence acquisition loop (coverage gaps, guarded interact, stop
rules). Offline: a real Playwright page loaded from a local fixture, a scripted chat in place
of the model.
"""

import pytest
from playwright.sync_api import sync_playwright

from financial_disclosure_review.core.context import Context
from financial_disclosure_review.domain.product_page import coverage
from financial_disclosure_review.domain.product_page.discover import TurnsExhaustedError, discover
from financial_disclosure_review.domain.product_page.session import PageSession
from financial_disclosure_review.domain.product_page.tools import call_tool
from tests.domain.product_page.fake_chat import ScriptedChat
from tests.helpers import FIXTURE_DIR

SINGLE_GAP_HTML = (FIXTURE_DIR / "html" / "coverage_single_gap.html").read_text()
FORBIDDEN_HTML = (FIXTURE_DIR / "html" / "coverage_page.html").read_text()
NO_CONTROL_HTML = (FIXTURE_DIR / "html" / "coverage_no_control.html").read_text()

SUBMIT_BASE = {
    "product_name": "테스트 신용카드",
    "summary": "테스트 카드 요약",
    "name_selector": "h1.product-title",
    "include": ["article#product"],
    "exclude": [],
    "landmarks": [
        {"selector": "article#product", "tag": "article", "role": ""},
        {"selector": "h1.product-title", "tag": "h1", "role": ""},
    ],
    "evidence": [],
}


def _session(html: str, tmp_path, playwright):
    ctx = Context(data_dir=str(tmp_path))
    sess = PageSession(playwright, "https://example.test/product", ctx)
    sess.page.set_content(html)
    sess.snapshot("default", "arrived")
    return sess


def _single_gap_script(gap_id: str) -> list[list[dict]]:
    return [
        [{"name": "inspect_page", "args": {}}],
        [{"name": "probe_selector", "args": {"selectors": ["article#product"]}}],
        [{"name": "submit_rule", "args": dict(SUBMIT_BASE)}],
        [
            {
                "name": "interact",
                "args": {
                    "action": "expand",
                    "selector": "button.tab-toggle",
                    "gap_id": gap_id,
                    "expected_evidence": "전월 이용금액 30만원 이상 조건 문구",
                },
            }
        ],
        [
            {
                "name": "submit_rule",
                "args": {
                    **SUBMIT_BASE,
                    "steps": [{"action": "expand", "selector": "button.tab-toggle"}],
                },
            }
        ],
    ]


def test_a_hidden_benefit_condition_is_closed_by_the_scripted_expand(tmp_path):
    with sync_playwright() as playwright:
        sess = _session(SINGLE_GAP_HTML, tmp_path, playwright)
        try:
            first = call_tool(sess, "inspect_page", {})
            control_gap = next(g for g in first["open_gaps"] if g["kind"] == "unexpanded_control")
            condition_gap = next(g for g in first["open_gaps"] if g["kind"] == "hidden_text")
            assert control_gap["target"] == "button.tab-toggle"
            assert control_gap["status"] == "open"
            assert condition_gap["status"] == "open"

            # Reset gap bookkeeping so discover() starts from the same clean state as inspect
            # did above (inspect_page here was only used to read the gap ids for the script).
            sess.gaps = []
            script = ScriptedChat(_single_gap_script(control_gap["id"]))
            ctx = Context(data_dir=str(tmp_path), max_turns=12)
            proposal = discover(sess, ctx, chat=script)

            assert proposal["include"] == ["article#product"]
            assert sess.final_coverage == {"status": "완료", "stop_reason": "full_coverage"}
            closed_ids = {control_gap["id"], condition_gap["id"]}
            assert all(g["status"] == "closed" for g in sess.gaps if g["id"] in closed_ids)
            expand_entry = next(e for e in sess.agent_trace if e["tool"] == "interact")
            assert expand_entry["blocked"] is False
            assert expand_entry["new_evidence"] is True
            assert expand_entry["rationale"] == {
                "gap_id": control_gap["id"],
                "expected_evidence": "전월 이용금액 30만원 이상 조건 문구",
            }
            first_submit = next(e for e in sess.agent_trace if e["tool"] == "submit_rule")
            assert "gap" in first_submit["result"]
        finally:
            sess.close()


def test_b_hidden_text_with_no_control_is_submitted_with_gaps(tmp_path):
    with sync_playwright() as playwright:
        sess = _session(NO_CONTROL_HTML, tmp_path, playwright)
        try:
            inspected = call_tool(sess, "inspect_page", {})
            assert not inspected["candidate_controls"]
            hidden_gap = next(g for g in inspected["open_gaps"] if g["kind"] == "hidden_text")
            assert hidden_gap["status"] == "unresolved"

            call_tool(sess, "probe_selector", {"selectors": ["article#product"]})
            result = call_tool(sess, "submit_rule", dict(SUBMIT_BASE))

            assert result["accepted"] is True
            assert sess.final_coverage == {
                "status": "조사 불충분",
                "stop_reason": "no_viable_control",
            }
        finally:
            sess.close()


def test_c_a_repeated_expand_is_refused_and_closes_exploration(tmp_path):
    with sync_playwright() as playwright:
        sess = _session(FORBIDDEN_HTML, tmp_path, playwright)
        try:
            gaps = call_tool(sess, "inspect_page", {})["open_gaps"]
            gap_id = next(g["id"] for g in gaps if g["target"] == "button.tab-toggle")

            args = {
                "action": "expand",
                "selector": "button.tab-toggle",
                "gap_id": gap_id,
                "expected_evidence": "조건 문구",
            }
            first = call_tool(sess, "interact", args)
            assert first["blocked"] is False
            assert sess.exploration_closed == ""

            second = call_tool(sess, "interact", args)
            assert second["blocked"] is True
            assert sess.exploration_closed == "repeated_action"

            later = call_tool(
                sess,
                "interact",
                {"action": "scroll", "gap_id": gap_id, "expected_evidence": "아무거나"},
            )
            assert later["blocked"] is True
            assert later["blocked_reason"] == "exploration closed: repeated_action; submit_rule now"
        finally:
            sess.close()


@pytest.mark.parametrize(
    "args, expected_reason_part",
    [
        (
            {"action": "scroll", "selector": "", "gap_id": "", "expected_evidence": ""},
            "gap_id and expected_evidence",
        ),
        (
            {
                "action": "expand",
                "selector": ".apply-btn",
                "gap_id": "gap-x",
                "expected_evidence": "y",
            },
            "apply/login/submit/download wording",
        ),
        (
            {
                "action": "expand",
                "selector": ".like-btn",
                "gap_id": "gap-x",
                "expected_evidence": "y",
            },
            "apply/login/submit/download wording",
        ),
        (
            {
                "action": "expand",
                "selector": "form button",
                "gap_id": "gap-x",
                "expected_evidence": "y",
            },
            "form control",
        ),
        (
            {
                "action": "open_link",
                "selector": "a.other-site",
                "gap_id": "gap-x",
                "expected_evidence": "y",
            },
            "not the same origin",
        ),
    ],
)
def test_d_forbidden_actions_are_refused_and_logged_blocked(tmp_path, args, expected_reason_part):
    with sync_playwright() as playwright:
        sess = _session(FORBIDDEN_HTML, tmp_path, playwright)
        try:
            result = call_tool(sess, "interact", args)
            assert result["blocked"] is True
            assert expected_reason_part in result["blocked_reason"]
            assert sess.exploration_closed == ""  # a one-off refusal does not close exploration
        finally:
            sess.close()


def test_e_the_same_scripted_scenario_yields_an_identical_agent_trace(tmp_path):
    def run(root):
        with sync_playwright() as playwright:
            sess = _session(SINGLE_GAP_HTML, root, playwright)
            try:
                coverage.derive_gaps(sess, coverage.observe(sess))
                control_gap_id = next(
                    g["id"] for g in sess.gaps if g["kind"] == "unexpanded_control"
                )
                sess.gaps = []
                script = ScriptedChat(_single_gap_script(control_gap_id))
                ctx = Context(data_dir=str(root), max_turns=12)
                discover(sess, ctx, chat=script)
                return sess.agent_trace
            finally:
                sess.close()

    trace_a = run(tmp_path / "run-a")
    trace_b = run(tmp_path / "run-b")
    assert trace_a == trace_b


def test_f_invalid_url_and_blocked_fetch_never_raise(tmp_path, monkeypatch):
    from financial_disclosure_review.domain.product_page import fetch as fetch_module
    from financial_disclosure_review.domain.product_page.fetch import fetch_product_page
    from financial_disclosure_review.domain.product_page.session import PageBlocked

    page = fetch_product_page("http://169.254.169.254/x", Context(data_dir=str(tmp_path)))
    assert page["status"] == "수집 실패"
    assert page["stop_reason"] == "invalid_url"
    assert page["html"] == ""

    def raising_visit(sess, url, ctx, rules_dir, chat_factory=None):
        raise PageBlocked("HTTP 403 for " + url)

    monkeypatch.setattr(fetch_module, "url_problem", lambda url, allowed: "")
    monkeypatch.setattr(fetch_module, "visit", raising_visit)
    page = fetch_product_page("https://example.test/product", Context(data_dir=str(tmp_path)))
    assert page["status"] == "수집 실패"
    assert page["stop_reason"] == "fetch_error"
    assert page["html"] == ""


def test_f_max_turns_without_an_accepted_submit_is_incomplete(tmp_path):
    with sync_playwright() as playwright:
        sess = _session(SINGLE_GAP_HTML, tmp_path, playwright)
        try:
            script = ScriptedChat([[{"name": "inspect_page", "args": {}}]])
            ctx = Context(data_dir=str(tmp_path), max_turns=2)
            with pytest.raises(TurnsExhaustedError):
                discover(sess, ctx, chat=script)
        finally:
            sess.close()


CSS_COLLAPSE_HTML = (FIXTURE_DIR / "html" / "coverage_css_collapse.html").read_text()


def test_text_hidden_by_a_stylesheet_counts_as_hidden_and_opening_it_is_new_evidence(tmp_path):
    """2026-09-29 실측: 스타일시트로 접힌 아코디언(visibility:hidden)을 정적 html만 보고 '보임'으로
    세어, 펼칠 것이 없다고 판단하고 full_coverage로 끝났습니다. 렌더링 가시성으로 세야 합니다."""
    with sync_playwright() as playwright:
        sess = _session(CSS_COLLAPSE_HTML, tmp_path, playwright)
        try:
            inspected = call_tool(sess, "inspect_page", {})
            assert inspected["hidden_text_blocks"] >= 1
            gap = next(g for g in inspected["open_gaps"] if g["kind"] == "unexpanded_control")
            opened = call_tool(
                sess,
                "interact",
                {
                    "action": "expand",
                    "selector": "button.acc-toggle",
                    "gap_id": gap["id"],
                    "expected_evidence": "전월 이용금액 조건",
                },
            )
            assert opened["blocked"] is False
            assert opened["new_evidence"] is True
            assert coverage.observe(sess)["hidden_text_blocks"] == 0
        finally:
            sess.close()
