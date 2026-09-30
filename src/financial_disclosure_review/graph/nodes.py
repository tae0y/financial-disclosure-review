"""The graph nodes. Each pulls what it needs from State and calls one domain entry point."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from langgraph.runtime import Runtime

from ..core.context import Context
from ..core.state import State
from ..core.text import norm
from ..core.threads import run_in_thread
from ..domain.ad_disclosure_check import judge_disclosure
from ..domain.classification import classify_page
from ..domain.display_check import judge_display
from ..domain.evidence_cards import extract_evidence_cards as extract_cards
from ..domain.persona_explanation import choose_profile
from ..domain.persona_explanation import generate_persona_explanation as generate_persona
from ..domain.persona_explanation.profiles import PROFILES_FILE
from ..domain.product_page import fetch_product_page
from ..domain.report import build_report
from ..domain.verification import verify
from ..knowledge.rubrics import rubric_bindings, rubric_labels
from .retry import MAX_LOOPS, RETRY_KEYS, escalation, plan_retry


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


def extract_evidence_cards(state: State, runtime: Runtime[Context]) -> dict:
    """Claims, conditions, exceptions and warnings as quoted cards; coverage gaps stay gaps."""
    print("[extract_evidence_cards]")
    cards: dict[str, Any] = dict(state.get("evidence_cards") or {})
    cards.update(
        extract_cards(state["product_page"], state.get("classification") or {}, runtime.context)
    )
    return {"evidence_cards": cards}


def card_ids_for(quotes: list[str], cards: list[dict]) -> list[str]:
    """Evidence cards whose quote overlaps one of a verdict's quotes, either way round."""
    wanted = [norm(q) for q in quotes if norm(q)]
    ids = []
    for card in cards:
        quote = norm(card.get("quote", ""))
        if quote and any(quote in q or q in quote for q in wanted):
            ids.append(card["id"])
    return ids


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
        cards = (state.get("evidence_cards") or {}).get("cards") or []
        check["items"] = [
            {**item, "card_ids": card_ids_for(item.get("quotes") or [], cards)}
            for item in check.get("items") or []
        ]
    return {"display_check": check}


def generate_persona_explanation(state: State, runtime: Runtime[Context]) -> dict:
    """Advice for one reviewed reader on what to check before signing; never a verdict."""
    print("[generate_persona_explanation]")
    ctx = runtime.context
    persona: dict[str, Any] = dict(state.get("persona_explanation") or {})
    cards = state.get("evidence_cards") or {}
    feedback = (state.get("verification") or {}).get("feedback") or []
    classification = state.get("classification") or {}
    # The reader is chosen once per review; a retry writes for the same reader.
    if not persona.get("profile") or not persona.get("selection"):
        persona.update(
            choose_profile(
                ctx,
                product_type=classification.get("product_type"),
                cards=cards.get("cards") or [],
                data_dir=ctx.data_dir,
                rubric_dir=ctx.rubric_dir,
            )
        )
    persona.update(
        generate_persona(
            list(cards.get("sources") or []),
            cards.get("cards") or [],
            classification,
            ctx,
            feedback,
            profiles_path=Path(ctx.rubric_dir) / PROFILES_FILE,
            profile=persona["profile"],
        )
    )
    return {"persona_explanation": persona}


def judge_ad_disclosure(state: State, runtime: Runtime[Context]) -> dict:
    """The mandatory ad disclosures on the page; on a retry only the codes verification flagged."""
    print("[judge_ad_disclosure]")
    check: dict[str, Any] = dict(state.get("ad_disclosure_check") or {})
    page: dict[str, Any] = dict(state.get("product_page") or {})
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
        )
    elif not page.get("html"):
        check.update(items=blocked("product_page.html이 비어 있음"), original=[])
    else:
        feedback = (state.get("verification") or {}).get("feedback") or []
        check.update(
            judge_disclosure(
                page,
                classification,
                runtime.context,
                # An empty original side (every item ruled out) is a result, not a missing one.
                check.get("original") if check.get("items") else None,
                check.get("items") or None,
                feedback=feedback,
            )
        )
    return {"ad_disclosure_check": check}


def verify_answer(state: State, runtime: Runtime[Context]) -> dict:
    print("[verify_answer]")
    previous: dict[str, Any] = dict(state.get("verification") or {})
    # verify() answers for this round only; the retry bookkeeping `retry_dispatch` wrote on
    # earlier rounds is kept so the report can show how many rounds were spent and why.
    kept = {key: previous[key] for key in RETRY_KEYS if key in previous}
    return {
        "verification": {
            **kept,
            **verify(
                state.get("product_page") or {},
                state.get("display_check") or {},
                state.get("persona_explanation") or {},
                state.get("ad_disclosure_check") or {},
                int(previous.get("loop_count") or 0),
            ),
        }
    }


def retry_dispatch(state: State) -> dict:
    print("[retry_dispatch]")
    verification: dict[str, Any] = dict(state.get("verification") or {})
    verification.update(plan_retry(state.get("verification") or {}))
    return {"verification": verification}


def report_for(state: Mapping[str, Any], ctx: Context, stop: Mapping[str, Any]) -> dict:
    """The Report for whatever State holds; `stop` says why the run ended where it did."""
    report: dict[str, Any] = dict(state.get("report") or {})
    report.update(
        build_report(
            state["product_page"],
            state.get("classification") or {},
            state.get("display_check") or {},
            state.get("persona_explanation") or {},
            state.get("ad_disclosure_check") or {},
            state.get("verification") or {},
            stop,
            bindings=rubric_bindings(ctx.db_path),
            previous_cost=report.get("cost"),
            cards=state.get("evidence_cards") or {},
            labels=rubric_labels(ctx.db_path),
        )
    )
    return report


def end_report(state: State, runtime: Runtime[Context]) -> dict:
    print("[end_report]")
    stop = {**escalation(state.get("verification") or {}), "max_loops": MAX_LOOPS}
    return {"report": report_for(state, runtime.context, stop)}
