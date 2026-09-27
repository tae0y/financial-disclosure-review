"""Entry point of the product_page domain: reuse a saved rule, or discover one."""

from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from ..core.context import Context
from .discover import discover
from .rules import (
    check_rule,
    execute_rule,
    finalize_rule,
    load_rule,
    page_family,
    product_from,
    rule_path,
    save_rule,
    validate_output,
)
from .session import PageSession


def fetch_product_page(url: str, ctx: Context) -> dict:
    """Reuse a validated site rule, or discover one with the agent. Runs in one worker thread."""
    rules_dir = Path(ctx.data_dir) / ctx.rules_subdir
    with sync_playwright() as playwright:
        sess = PageSession(playwright, url, ctx)
        try:
            return visit(sess, url, ctx, rules_dir)
        finally:
            sess.log(
                "summary",
                model_calls=sess.model_calls,
                snapshots=len(sess.snapshots),
                visits=sess.visits,
            )
            sess.close()


def visit(sess: PageSession, url: str, ctx: Context, rules_dir: Path) -> dict:
    viewport = sess.viewport_key()
    path = rule_path(rules_dir, url, viewport)
    key = f"{urlparse(url).hostname} | {page_family(url)} | {viewport}"
    rule, mode = load_rule(path), "discover"
    sess.phase = "render" if rule else "discover"
    sess.goto(url)
    if rule:
        reasons = check_rule(sess.last_html, rule)
        if not reasons:
            content = execute_rule(sess, rule)
            errors = validate_output(rule, content)
            if not errors:
                sess.log(
                    "reuse", key=key, model_calls=0, validation="passed", states=content["states"]
                )
                return finish(sess, url, "reuse", product_from(rule, content), content)
            sess.log("drift", key=key, stage="output", reasons=errors, status="uncertain")
        else:
            sess.log(
                "drift",
                key=key,
                stage="structure",
                reasons=reasons,
                status="rule rejected before use",
            )
        mode, sess.phase = "rediscover", "discover"
        sess.goto(url)
    sess.phase = "discover"
    sess.visits = 1
    sess.log(mode, key=key, max_turns=ctx.max_turns, max_visits=ctx.max_visits)
    proposal = discover(sess, ctx)
    rule, content = finalize_rule(sess, proposal)
    errors = validate_output(rule, content)
    if errors:
        sess.log("uncertain", key=key, reasons=errors)
        raise RuntimeError(f"replay of the discovered rule failed validation: {errors}")
    rule["host"], rule["family"], rule["viewport"] = (
        urlparse(url).hostname,
        page_family(url),
        sess.viewport_key(),
    )
    rule["saved_at"] = datetime.now().isoformat(timespec="seconds")
    save_rule(path, rule)
    sess.log(
        "rule_saved",
        path=str(path),
        validation="passed",
        includes=len(rule["include"]),
        states=content["states"],
    )
    return finish(sess, url, mode, product_from(rule, content), content)


def finish(sess: PageSession, url: str, mode: str, product: dict, content: dict) -> dict:
    sess.log(
        "result",
        mode=mode,
        model_calls=sess.model_calls,
        regions=len(content["pieces"]),
        states=content["states"],
        html_chars=len(content["html"]),
    )
    return {
        "url": url,
        "product": product,
        "actions": sess.actions,
        "snapshots": sess.snapshots,
        "html": content["html"],
    }
