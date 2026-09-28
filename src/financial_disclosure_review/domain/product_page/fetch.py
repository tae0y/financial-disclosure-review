"""Entry point of the product_page domain: reuse a saved rule, or discover one."""

from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from ...core.context import Context
from ...core.urls import url_problem
from ...core.usage import BudgetError
from . import coverage
from .discover import TurnsExhaustedError, discover
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
from .session import PageBlocked, PageSession, VisitCapReached


class ReplayFailedError(RuntimeError):
    """A discovered rule failed its own replay; nothing is saved for reuse."""


def fetch_product_page(url: str, ctx: Context, chat_factory=None) -> dict:
    """Reuse a validated site rule or discover one. Never raises: page/agent failures come back
    as `status="수집 실패"` (or `"조사 불충분"` when a rule was never accepted) with `stop_reason`
    and `error` set, so a bad page never stops the review."""
    problem = url_problem(url, ctx.allowed_hosts)
    if problem:
        return _empty(url, "수집 실패", "invalid_url", f"refusing to open {url}: {problem}")
    rules_dir = Path(ctx.data_dir) / ctx.rules_subdir
    with sync_playwright() as playwright:
        sess = PageSession(playwright, url, ctx)
        try:
            return visit(sess, url, ctx, rules_dir, chat_factory)
        except PageBlocked as error:
            return _empty(url, "수집 실패", "fetch_error", str(error), sess)
        except VisitCapReached as error:
            return _empty(url, "수집 실패", "visit_cap", str(error), sess)
        except ReplayFailedError as error:
            return _empty(url, "수집 실패", "replay_failed", str(error), sess)
        except TurnsExhaustedError as error:
            return _empty(url, "조사 불충분", "max_turns", str(error), sess)
        except BudgetError as error:
            return _empty(url, "조사 불충분", "budget_exhausted", str(error), sess)
        finally:
            sess.log(
                "summary",
                model_calls=sess.model_calls,
                snapshots=len(sess.snapshots),
                visits=sess.visits,
            )
            sess.close()


def _empty(
    url: str, status: str, stop_reason: str, error: str, sess: PageSession | None = None
) -> dict:
    coverage_dict = {"before": {}, "after": {}, "gaps": []}
    actions, snapshots, trace = [], [], []
    if sess is not None:
        actions, snapshots, trace = sess.actions, sess.snapshots, sess.agent_trace
        try:
            coverage_dict = {
                "before": sess.coverage_before,
                "after": coverage.summarize(coverage.observe(sess), sess),
                "gaps": coverage.public_gaps(sess),
            }
        except Exception:  # pragma: no cover - defensive: the page may be unusable by now
            pass
    return {
        "url": url,
        "product": {"product_name": "", "summary": "", "evidence": []},
        "actions": actions,
        "snapshots": snapshots,
        "html": "",
        "status": status,
        "stop_reason": stop_reason,
        "error": error,
        "coverage": coverage_dict,
        "agent_trace": trace,
    }


def visit(sess: PageSession, url: str, ctx: Context, rules_dir: Path, chat_factory=None) -> dict:
    viewport = sess.viewport_key()
    path = rule_path(rules_dir, url, viewport)
    key = f"{urlparse(url).hostname} | {page_family(url)} | {viewport}"
    rule, mode = load_rule(path), "discover"
    sess.phase = "render" if rule else "discover"
    sess.goto(url)
    if rule:
        reasons = check_rule(sess.last_html, rule)
        if not reasons:
            obs_before = coverage.observe(sess)
            coverage.derive_gaps(sess, obs_before)
            before = coverage.summarize(obs_before, sess)
            content = execute_rule(sess, rule)
            errors = validate_output(rule, content)
            if not errors:
                obs_after = coverage.observe(sess)
                coverage.derive_gaps(sess, obs_after)
                after = coverage.summarize(obs_after, sess)
                sess.log(
                    "reuse", key=key, model_calls=0, validation="passed", states=content["states"]
                )
                return finish(
                    sess,
                    url,
                    "reuse",
                    product_from(rule, content),
                    content,
                    status="완료",
                    stop_reason="rule_reused",
                    coverage_dict={
                        "before": before,
                        "after": after,
                        "gaps": coverage.public_gaps(sess),
                    },
                )
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
    chat = chat_factory() if chat_factory is not None else None
    proposal = discover(sess, ctx, chat=chat)
    rule, content = finalize_rule(sess, proposal)
    errors = validate_output(rule, content)
    if errors:
        sess.log("uncertain", key=key, reasons=errors)
        raise ReplayFailedError(f"replay of the discovered rule failed validation: {errors}")
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
    final = sess.final_coverage or {"status": "완료", "stop_reason": "full_coverage"}
    return finish(
        sess,
        url,
        mode,
        product_from(rule, content),
        content,
        status=final["status"],
        stop_reason=final["stop_reason"],
        coverage_dict={
            "before": sess.coverage_before,
            "after": sess.coverage_after,
            "gaps": coverage.public_gaps(sess),
        },
    )


def finish(
    sess: PageSession,
    url: str,
    mode: str,
    product: dict,
    content: dict,
    *,
    status: str,
    stop_reason: str,
    coverage_dict: dict,
) -> dict:
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
        "status": status,
        "stop_reason": stop_reason,
        "error": "",
        "coverage": coverage_dict,
        "agent_trace": sess.agent_trace,
    }
