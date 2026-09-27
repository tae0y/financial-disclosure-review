"""The discovery agent: its brief and the bounded tool-call loop it runs in."""

from ..core.context import Context
from ..core.text import short
from ..llm.client import ToolChat
from .session import PageSession
from .tools import TOOLS, call_tool

SYSTEM_PROMPT = """You find the product-specific content of a financial product web page and describe it as a reusable rule of CSS selectors.

Goal: submit_rule with selectors that capture ALL text that describes the one product this page is about (name, benefits, rates, fees, conditions, limits, risks, warnings, notes, FAQs, terms shown on the page), including text revealed by tabs and expandable controls, and nothing else.

Tools: inspect_page (outline with candidate selectors), probe_selector (match counts, text samples, rendered font size/color/bounds), interact (scroll, expand, open_link, go_back), submit_rule.

Method:
1. inspect_page. Scroll with interact if the outline looks short or content loads lazily.
2. probe_selector on candidate regions to confirm what each selects. Look for content scattered across several regions; include each one.
3. Reveal hidden content: use interact expand with a selector that matches all tab or accordion controls (one call clicks every match). Then inspect_page again if new content appeared.
4. submit_rule. If it returns errors, fix them and submit again.

Rules:
- Use plain CSS built from the ids, classes, tags and roles that inspect_page showed. No text-matching pseudo selectors.
- include: several selectors, one per content region. exclude: only noise inside a broad included region (menus, banners, share buttons, related-product lists, recommendations).
- Never include global header, navigation, footer, unrelated sidebars, or cookie/popup layers.
- Never touch forms, apply, login, submit or download controls. Open a link only when it clearly continues the same product's explanation, then go_back.
- steps: exactly the interactions (scroll, expand) needed to reveal hidden content, in order.
- landmarks: 2-6 stable structural elements (selector, tag, optional role) that show where the content sits, such as its container and main heading. No product text.
- name_selector must match an element whose text contains product_name.
- You have a limited number of model turns. Call several independent tools in one turn."""


def discover(sess: PageSession, ctx: Context) -> dict:
    """Bounded tool-call loop. Returns the rule proposal that passed validation."""
    chat = ToolChat(ctx.model, TOOLS)
    intro = (
        f"Product page: {sess.url}\nViewport: {ctx.viewport_width}x{ctx.viewport_height}\n"
        f"Model turns available: {ctx.max_turns}. Page visits available: {ctx.max_visits} "
        f"(used {sess.visits})."
    )
    chat.system(SYSTEM_PROMPT)
    chat.user(intro)
    for turn in range(1, ctx.max_turns + 1):
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
                result=short(result, 300),
                tokens=reply["tokens"],
            )
            chat.tool_result(call["id"], short({**result, "turns_left": left}, 12_000))
            if call["name"] == "submit_rule" and result.get("accepted"):
                assert sess.pending is not None
                return sess.pending
    raise RuntimeError(f"agent used all {ctx.max_turns} turns without an accepted rule")
