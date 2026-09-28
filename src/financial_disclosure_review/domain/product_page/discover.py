"""The discovery agent: its brief and the bounded tool-call loop it runs in."""

import re
from typing import cast

from ...core.context import Context
from ...core.text import short
from ...llm.client import ToolChat
from . import coverage
from .session import PageSession
from .tools import TOOLS, call_tool

# The last few turns of the budget are reserved for submit_rule once exploration has closed,
# so the agent is never left holding an open gap with no turns left to act on it.
TURN_BUDGET_RESERVE = 4

BASE64_RUN = re.compile(r"[A-Za-z0-9+/]{200,}={0,2}")

SYSTEM_PROMPT = """You find the product-specific content of a financial product web page and describe it as a reusable rule of CSS selectors.

Goal: submit_rule with selectors that capture ALL text that describes the one product this page is about (name, benefits, rates, fees, conditions, limits, risks, warnings, notes, FAQs, terms shown on the page), including text revealed by tabs and expandable controls, and nothing else.

Tools: inspect_page (outline plus hidden/visible text counts, candidate controls, samples and open coverage gaps), probe_selector (match counts, text samples, rendered font size/color/bounds), interact (scroll, expand, open_link, go_back), submit_rule.

Method:
1. inspect_page. It lists open coverage gaps (unexpanded_control, hidden_text, benefit_without_condition, image_only) -- these are hints, not verdicts.
2. probe_selector on candidate regions to confirm what each selects. Look for content scattered across several regions; include each one.
3. Reveal hidden content: interact expand on a control that closes an open gap, citing that gap's id as gap_id and what you expect to find as expected_evidence. Then inspect_page again if new content appeared.
4. submit_rule. If it returns errors, fix them and submit again.

Rules:
- scroll, expand and open_link all require gap_id and expected_evidence naming the coverage gap being investigated. go_back needs neither.
- Repeating the exact same expand or open_link (same selector) is refused and ends exploration for this page -- after that, only inspect_page, probe_selector and submit_rule work.
- Exploration also ends once no open gap remains, once interactions or turns without new evidence run out, or near the end of the turn budget. After it ends, submit_rule with what you have.
- Use plain CSS built from the ids, classes, tags and roles that inspect_page showed. No text-matching pseudo selectors.
- include: several selectors, one per content region. exclude: only noise inside a broad included region (menus, banners, share buttons, related-product lists, recommendations).
- Never include global header, navigation, footer, unrelated sidebars, or cookie/popup layers.
- Never touch forms, apply, login, submit or download controls. Open a link only when it clearly continues the same product's explanation, then go_back.
- steps: exactly the interactions (scroll, expand) needed to reveal hidden content, in order.
- landmarks: 2-6 stable structural elements (selector, tag, optional role) that show where the content sits, such as its container and main heading. No product text.
- name_selector must match an element whose text contains product_name.
- You have a limited number of model turns. Call several independent tools in one turn."""


class TurnsExhaustedError(RuntimeError):
    """The agent used every model turn without an accepted submit_rule."""


def discover(sess: PageSession, ctx: Context, chat=None) -> dict:
    """Bounded tool-call loop. Returns the rule proposal that passed validation."""
    chat = chat if chat is not None else ToolChat(ctx.model, TOOLS)
    obs0 = coverage.observe(sess)
    coverage.derive_gaps(sess, obs0)
    sess.coverage_before = coverage.summarize(obs0, sess)
    intro = (
        f"Product page: {sess.url}\nViewport: {ctx.viewport_width}x{ctx.viewport_height}\n"
        f"Model turns available: {ctx.max_turns}. Page visits available: {ctx.max_visits} "
        f"(used {sess.visits}). Interaction budget: {coverage.max_interactions(ctx)}."
    )
    chat.system(SYSTEM_PROMPT)
    chat.user(intro)
    for turn in range(1, ctx.max_turns + 1):
        if not sess.exploration_closed and turn > ctx.max_turns - TURN_BUDGET_RESERVE:
            sess.exploration_closed = "turn_budget"
        sess.model_calls += 1
        reply = chat.turn()
        left = ctx.max_turns - turn
        if not reply["tool_calls"]:
            sess.log("model_turn", turn=turn, tool_calls=0, tokens=reply["tokens"])
            chat.user(f"Use the tools. Call submit_rule when ready. Turns left: {left}.")
            continue
        for call in reply["tool_calls"]:
            result = call_tool(sess, call["name"], call["args"])
            sess.log(
                "tool_call",
                turn=turn,
                tool=call["name"],
                args=short(call["args"]),
                result=short(result, 12_000),
                tokens=reply["tokens"],
            )
            text = _for_model(result, left)
            sess.agent_trace.append(_trace_entry(turn, call, result, text))
            chat.tool_result(call["id"], text)
            if call["name"] == "submit_rule" and result.get("accepted"):
                assert sess.pending is not None
                obs_final = coverage.observe(sess)
                coverage.derive_gaps(sess, obs_final)
                sess.coverage_after = coverage.summarize(obs_final, sess)
                return sess.pending
    raise TurnsExhaustedError(f"agent used all {ctx.max_turns} turns without an accepted rule")


def _for_model(result: dict, turns_left: int) -> str:
    """What the discovery agent sees: the tool result plus turns left, snapshot paths and long
    base64-looking runs stripped, capped at 12,000 characters -- the same limit as the log."""

    def strip(value):
        if isinstance(value, dict):
            return {
                k: strip(v) for k, v in value.items() if k not in ("html_path", "visual_samples")
            }
        if isinstance(value, list):
            return [strip(v) for v in value]
        return value

    cleaned = cast(dict, strip(result))
    text = short({**cleaned, "turns_left": turns_left}, 12_000)
    return BASE64_RUN.sub("<omitted>", text)


def _trace_entry(turn: int, call: dict, result: dict, text: str) -> dict:
    args = call.get("args", {})
    is_interact = call["name"] == "interact"
    return {
        "turn": turn,
        "tool": call["name"],
        "args": short(args),
        "rationale": {
            "gap_id": args.get("gap_id", "") if is_interact else "",
            "expected_evidence": args.get("expected_evidence", "") if is_interact else "",
        },
        "result": text,
        "blocked": bool(result.get("blocked", False)),
        "blocked_reason": result.get("blocked_reason", ""),
        "new_evidence": bool(result.get("new_evidence", False)),
        "coverage_before": result.get("coverage_before", {}),
        "coverage_after": result.get("coverage_after", {}),
    }
