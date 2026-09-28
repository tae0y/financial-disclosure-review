"""The graph nodes. Each pulls what it needs from State and calls one domain entry point."""

from typing import Any

from langgraph.runtime import Runtime

from ..core.context import Context
from ..core.state import State
from ..core.threads import run_in_thread
from ..domain.classification import classify_page
from ..domain.display_check import judge_display
from ..domain.explanation_duty_check import judge_explanation
from ..domain.plain_language import generate_plain, unjudged_plain
from ..domain.product_page import fetch_product_page
from ..domain.report import build_report
from ..domain.verification import verify
from ..knowledge.search import search_cases_for
from .retry import MAX_LOOPS, escalation, plan_retry


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


def search_cases(state: State, runtime: Runtime[Context]) -> dict:
    """Related sanction/dispute cases for the classified product. Reference data only: this node
    fills `case_search` and no judging node reads it yet."""
    print("[search_cases]")
    cases: dict[str, Any] = dict(state.get("case_search") or {})
    classification = state.get("classification") or {}
    if not classification.get("product_type"):
        cases.update(
            queries=[],
            hits=[],
            status="판정 불가",
            reason="classification is empty; run classify_type first",
        )
    else:
        product = (state.get("product_page") or {}).get("product") or {}
        cases.update(search_cases_for(product, classification, runtime.context.db_path))
    return {"case_search": cases}


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
    page, classification = state["product_page"], state.get("classification") or {}
    feedback = (state.get("verification") or {}).get("feedback") or []
    if not classification.get("product_type") or not classification.get("page_type"):
        plain.update(unjudged_plain("classification이 비어 있음: classify_type을 먼저 실행하세요"))
    elif not page.get("html"):
        plain.update(
            unjudged_plain(
                "product_page.html이 비어 있음: preprocess_product_page를 먼저 실행하세요"
            )
        )
    else:
        plain.update(generate_plain(page, classification, feedback, runtime.context))
    return {"plain_language": plain}


def judge_explanation_duty(state: State, runtime: Runtime[Context]) -> dict:
    print("[judge_explanation_duty]")
    check: dict[str, Any] = dict(state.get("explanation_duty_check") or {})
    page = state.get("product_page") or {}
    plain = state.get("plain_language") or {}
    classification = state.get("classification") or {}

    def blocked(reason: str) -> list[dict]:
        return [
            {
                "code": "",
                "rubric": "",
                "applied": False,
                "condition_status": "",
                "reason": reason,
            }
        ]

    if not classification.get("product_type") or not classification.get("page_type"):
        check.update(
            items=blocked("classification이 비어 있음; classify_type을 먼저 실행해야 함"),
            original=[],
            plain=[],
            fidelity=[],
        )
    elif not page.get("html"):
        check.update(
            items=blocked("product_page.html이 비어 있음"),
            original=[],
            plain=[],
            fidelity=[],
        )
    elif not plain.get("html"):
        check.update(
            items=check.get("items")
            or blocked("plain_language.html이 비어 있음; generate_plain_lang을 먼저 실행해야 함"),
            original=check.get("original") or [],
            plain=[],
            fidelity=[],
        )
    else:
        check.update(
            judge_explanation(
                page,
                plain,
                classification,
                runtime.context,
                check.get("original") or None,
                check.get("items") or None,
                feedback=(state.get("verification") or {}).get("feedback") or [],
            )
        )
    return {"explanation_duty_check": check}


def verify_answer(state: State, runtime: Runtime[Context]) -> dict:
    print("[verify_answer]")
    previous = state.get("verification") or {}
    return {
        "verification": verify(
            state.get("product_page") or {},
            state.get("display_check") or {},
            state.get("plain_language") or {},
            state.get("explanation_duty_check") or {},
            int(previous.get("loop_count") or 0),
        )
    }


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
            {**escalation(state.get("verification") or {}), "max_loops": MAX_LOOPS},
        )
    )
    return {"report": report}
