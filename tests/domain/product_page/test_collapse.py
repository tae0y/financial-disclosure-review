"""DaisyUI-style accordions: a checkbox layered over the title opens the panel with CSS only.

2026-09-29 실측(디지로카 Las Vegas): 이런 아코디언을 열 컨트롤이 없다고 보고
`조사 불충분`으로 끝났고, 컨테이너 문구의 "결제일"이 결제 행동 문구로 걸려 펼치기가 거부됐습니다.
"""

from playwright.sync_api import sync_playwright

from financial_disclosure_review.core.context import Context
from financial_disclosure_review.domain.product_page import coverage
from financial_disclosure_review.domain.product_page.discover import discover
from financial_disclosure_review.domain.product_page.session import PageSession
from financial_disclosure_review.domain.product_page.tools import call_tool
from tests.domain.product_page.fake_chat import ScriptedChat
from tests.helpers import FIXTURE_DIR

DAISY_HTML = (FIXTURE_DIR / "html" / "coverage_daisyui_collapse.html").read_text(encoding="utf-8")
NO_CONTROL_HTML = (FIXTURE_DIR / "html" / "coverage_no_control.html").read_text()

SUBMIT = {
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
    sess = PageSession(playwright, "https://example.test/product", Context(data_dir=str(tmp_path)))
    sess.page.set_content(html)
    sess.snapshot("default", "arrived")
    return sess


def _expand(sess, selector: str, gap_id: str = "gap-1") -> dict:
    return call_tool(
        sess,
        "interact",
        {
            "action": "expand",
            "selector": selector,
            "gap_id": gap_id,
            "expected_evidence": "접힌 조건 문구",
        },
    )


def test_the_accordion_checkboxes_outside_forms_are_the_candidate_controls(tmp_path):
    with sync_playwright() as playwright:
        sess = _session(DAISY_HTML, tmp_path, playwright)
        try:
            inspected = call_tool(sess, "inspect_page", {})
            targets = [
                g["target"] for g in inspected["open_gaps"] if g["kind"] == "unexpanded_control"
            ]
            assert len(targets) == 2
            assert all("> input" in t for t in targets)
            assert not any("form" in t or "options" in t for t in targets)
            hidden = [g for g in inspected["open_gaps"] if g["kind"] == "hidden_text"]
            assert hidden and all(g["status"] == "open" for g in hidden)
        finally:
            sess.close()


def test_a_title_with_payment_day_wording_is_not_refused(tmp_path):
    with sync_playwright() as playwright:
        sess = _session(DAISY_HTML, tmp_path, playwright)
        try:
            call_tool(sess, "inspect_page", {})
            opened = _expand(sess, "#acc-pay > input")
            assert opened["blocked"] is False
            assert opened["new_evidence"] is True
        finally:
            sess.close()


def test_clicking_the_title_toggles_its_accordion(tmp_path):
    with sync_playwright() as playwright:
        sess = _session(DAISY_HTML, tmp_path, playwright)
        try:
            call_tool(sess, "inspect_page", {})
            opened = _expand(sess, "#acc-note > .collapse-title")
            assert opened["blocked"] is False
            assert opened["new_evidence"] is True
        finally:
            sess.close()


def test_an_already_open_accordion_is_not_closed_again(tmp_path):
    with sync_playwright() as playwright:
        sess = _session(DAISY_HTML, tmp_path, playwright)
        try:
            call_tool(sess, "inspect_page", {})
            _expand(sess, "#acc-note > input", "gap-1")
            again = _expand(sess, "#acc-note > .collapse-title", "gap-2")
            assert again["blocked"] is True
            assert "already open" in again["blocked_reason"]
            assert sess.page.locator("#acc-note > input").is_checked()
        finally:
            sess.close()


def test_a_checkbox_inside_a_form_or_outside_an_accordion_is_still_refused(tmp_path):
    with sync_playwright() as playwright:
        sess = _session(DAISY_HTML, tmp_path, playwright)
        try:
            call_tool(sess, "inspect_page", {})
            in_form = _expand(sess, "form .collapse > input", "gap-1")
            loose = _expand(sess, "#loose", "gap-2")
            assert in_form["blocked"] is True
            assert "form control" in in_form["blocked_reason"]
            assert loose["blocked"] is True
            assert "form control" in loose["blocked_reason"]
        finally:
            sess.close()


def test_one_expand_over_every_accordion_closes_each_gap_and_completes(tmp_path):
    with sync_playwright() as playwright:
        sess = _session(DAISY_HTML, tmp_path, playwright)
        steps = [{"action": "expand", "selector": "article#product .collapse > input"}]
        submit = {"name": "submit_rule", "args": {**SUBMIT, "steps": steps}}
        try:
            script = ScriptedChat(
                [
                    [{"name": "inspect_page", "args": {}}],
                    [
                        {
                            "name": "interact",
                            "args": {
                                "action": "expand",
                                "selector": "article#product .collapse > input",
                                "gap_id": "gap-1",
                                "expected_evidence": "접힌 할인 조건과 유의사항",
                            },
                        }
                    ],
                    [{"name": "probe_selector", "args": {"selectors": ["article#product"]}}],
                    # The form's consent text sits outside the selection: the first submit is
                    # nudged about it, the unchanged resubmit is accepted.
                    [submit],
                    [submit],
                ]
            )
            discover(sess, Context(data_dir=str(tmp_path), max_turns=12), chat=script)
            assert sess.final_coverage == {"status": "완료", "stop_reason": "full_coverage"}
            expand = next(e for e in sess.agent_trace if e["tool"] == "interact")
            assert expand["new_evidence"] is True
            open_actionable = [
                g
                for g in sess.gaps
                if g["kind"] in ("unexpanded_control", "hidden_text")
                and g["status"] == "open"
                and "개인정보" not in g["detail"]  # the form panel stays closed by design
            ]
            assert open_actionable == []
        finally:
            sess.close()


def test_hidden_text_nothing_can_reveal_does_not_lower_the_status(tmp_path):
    """사용자 결정(2026-09-29): 열어 봐도 볼 수 없는 숨김 글은 제외하고 진행합니다.
    보고서의 한계로만 남기고 상태를 `조사 불충분`으로 낮추지 않습니다."""
    with sync_playwright() as playwright:
        sess = _session(NO_CONTROL_HTML, tmp_path, playwright)
        try:
            call_tool(sess, "inspect_page", {})
            call_tool(sess, "probe_selector", {"selectors": ["article#product"]})
            result = call_tool(sess, "submit_rule", dict(SUBMIT))
            assert result["accepted"] is True
            assert sess.final_coverage == {"status": "완료", "stop_reason": "reachable_coverage"}
            hidden = [g for g in sess.gaps if g["kind"] == "hidden_text"]
            assert hidden and all(g["status"] == "unresolved" for g in hidden)
            assert coverage.unreachable_hidden(sess)
        finally:
            sess.close()


def _info(**over) -> dict:
    base = {
        "href": "",
        "tag": "input",
        "type": "checkbox",
        "cls": "",
        "expandable": False,
        "collapse_toggle": True,
        "checked": False,
        "in_form": False,
        "text": "국내외 가맹점 결제일 할인",
        "visible": True,
    }
    return {**base, **over}


def test_reject_reason_for_accordion_toggles():
    from financial_disclosure_review.domain.product_page.session import reject_reason

    assert reject_reason(_info()) == ""
    assert reject_reason(_info(in_form=True)) == "form control"
    assert reject_reason(_info(collapse_toggle=False)) == "form control"
    assert reject_reason(_info(text="바로 결제하기")) == "apply/login/submit/download wording"
    assert (
        reject_reason(
            _info(
                tag="button", type="", collapse_toggle=False, expandable=True, text="카드 신청 방법"
            )
        )
        == ""
    )


def test_an_unprobed_include_is_probed_by_the_submit_itself(tmp_path):
    """2026-09-29 F1(신한카드): 제출 → 'probe 먼저' 거절 → probe → 제출을 반복하다 20턴을
    다 썼습니다. 제출이 직접 probe해 결과를 돌려주므로 다음 제출에 별도 probe 턴이 필요 없습니다."""
    with sync_playwright() as playwright:
        sess = _session(NO_CONTROL_HTML, tmp_path, playwright)
        try:
            call_tool(sess, "inspect_page", {})
            first = call_tool(sess, "submit_rule", dict(SUBMIT))
            assert first["accepted"] is False
            assert "had not been probed" in " ".join(first["errors"])
            assert first["probe"]["results"][0]["selector"] == "article#product"
            again = call_tool(sess, "submit_rule", dict(SUBMIT))
            assert not any("probed" in e for e in again.get("errors", []))
        finally:
            sess.close()
