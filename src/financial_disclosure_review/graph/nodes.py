"""The graph nodes. Each pulls what it needs from State and calls one domain entry point."""

from typing import Any

from langgraph.runtime import Runtime

from ..classification import classify_page
from ..core.context import Context
from ..core.state import State
from ..core.threads import run_in_thread
from ..display_check import judge_display
from ..explanation_duty_check import check_duty
from ..plain_language import write_plain
from ..product_page import fetch_product_page
from ..report import build_report
from ..verification import verify
from .retry import plan_retry


def preprocess_product_page(state: State, runtime: Runtime[Context]) -> dict:
    print("[preprocess_product_page]")
    page: dict[str, Any] = dict(state["product_page"])
    page.update(run_in_thread(fetch_product_page, page["url"], runtime.context))
    return {"product_page": page}


def classify_type(state: State, runtime: Runtime[Context]) -> dict:
    print("[classify_type]")
    classification: dict[str, Any] = dict(state.get("classification") or {})
    classification.update(classify_page(state["product_page"], runtime.context.model))
    return {"classification": classification}


def judge_display_method(state: State, runtime: Runtime[Context]) -> dict:
    print("[judge_display_method]")
    check: dict[str, Any] = dict(state.get("display_check") or {})
    page, classification = state["product_page"], state.get("classification") or {}
    if not classification.get("product_type") or not classification.get("page_type"):
        check.update(
            items=[],
            judgments={
                "status": "판정 불가",
                "reason": "classification is empty; run classify_type first",
            },
        )
    elif not page.get("html") or not page.get("snapshots"):
        check.update(
            items=[],
            judgments={
                "status": "판정 불가",
                "reason": "product_page has no html or snapshots",
            },
        )
    else:
        check.update(judge_display(page, classification, runtime.context))
    return {"display_check": check}


def generate_plain_lang(state: State, runtime: Runtime[Context]) -> dict:
    print("[generate_plain_lang]")
    plain: dict[str, Any] = dict(state.get("plain_language") or {})
    plain.update(
        write_plain(
            state["product_page"],
            state.get("classification") or {},
            (state.get("verification") or {}).get("feedback"),
            runtime.context,
        )
    )
    return {"plain_language": plain}


def judge_explanation_duty(state: State, runtime: Runtime[Context]) -> dict:
    print("[judge_explanation_duty]")
    duty: dict[str, Any] = dict(state.get("explanation_duty_check") or {})
    duty.update(
        check_duty(
            state["product_page"],
            state.get("classification") or {},
            state.get("plain_language") or {},
            duty or None,
            runtime.context,
        )
    )
    return {"explanation_duty_check": duty}


def verify_answer(state: State, runtime: Runtime[Context]) -> dict:
    print("[verify_answer]")
    verification: dict[str, Any] = dict(state.get("verification") or {})
    verification.update(
        verify(
            state.get("display_check") or {},
            state.get("plain_language") or {},
            state.get("explanation_duty_check") or {},
            int(verification.get("loop_count") or 0),
            runtime.context,
        )
    )
    return {"verification": verification}


def retry_dispatch(state: State) -> dict:
    print("[retry_dispatch]")
    verification: dict[str, Any] = dict(state.get("verification") or {})
    verification.update(plan_retry(state.get("verification") or {}))
    return {"verification": verification}


def end_report(state: State) -> dict:
    print("[end_report]")
    report: dict[str, Any] = dict(state.get("report") or {})
    report.update(
        build_report(
            state["product_page"],
            state.get("classification") or {},
            state.get("display_check") or {},
            state.get("plain_language") or {},
            state.get("explanation_duty_check") or {},
            state.get("verification") or {},
        )
    )
    return {"report": report}
