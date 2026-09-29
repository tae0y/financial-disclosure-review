"""The graph nodes. Each pulls what it needs from State and calls one domain entry point."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from langgraph.runtime import Runtime

from ..core.context import Context
from ..core.state import State
from ..core.text import norm, visible_text
from ..core.threads import run_in_thread
from ..domain.classification import classify_page
from ..domain.display_check import judge_display
from ..domain.evidence_cards import extract_evidence_cards as extract_cards
from ..domain.explanation_duty_check import judge_explanation, judge_original
from ..domain.explanation_duty_check.ledger import check_ledger, map_rubric_fidelity
from ..domain.persona_explanation import choose_profile
from ..domain.persona_explanation import generate_persona_explanation as generate_persona
from ..domain.persona_explanation.profiles import PROFILES_FILE
from ..domain.product_page import fetch_product_page
from ..domain.report import build_report
from ..domain.verification import verify
from ..knowledge.build_cases import CASE_CORPUS_FILE
from ..knowledge.linking import link_reference_cases
from ..knowledge.reference import RISK_KINDS_FILE
from ..knowledge.rubrics import rubric_bindings, rubric_labels
from ..llm.client import ask
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


def retrieve_reference_cases(state: State, runtime: Runtime[Context]) -> dict:
    """Report-only case references for the page's cards; no judging node reads the result."""
    print("[retrieve_reference_cases]")
    ctx = runtime.context
    refs: dict[str, Any] = dict(state.get("reference_cases") or {})
    rubric_dir = Path(ctx.rubric_dir)
    # A bounded agent searches, reads and proposes links; code validates every quote.
    refs.update(
        link_reference_cases(
            (state.get("evidence_cards") or {}).get("cards") or [],
            state.get("classification") or {},
            ctx.db_path,
            ctx=ctx,
            risk_kinds_path=rubric_dir / RISK_KINDS_FILE,
            corpus_path=rubric_dir / CASE_CORPUS_FILE,
        )
    )
    return {"reference_cases": refs}


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


def mark_mandatory(
    sources: list[dict[str, Any]], display: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Flag the source lines display_check labelled as 의무표시, so the explanation keeps them
    emphasised (audit P2-12). Matching is by normalised text containment either way."""
    judgments = display.get("judgments") or {}
    wanted = set((judgments.get("labels") or {}).get("mandatory") or [])
    texts = [
        norm(b.get("text") or "")
        for b in judgments.get("blocks") or []
        if b.get("id") in wanted and len(norm(b.get("text") or "")) >= 6
    ]

    def hit(text: str) -> bool:
        line = norm(text)
        return any(t in line or (len(line) >= 6 and line in t) for t in texts)

    return [{**s, "mandatory": True} if texts and hit(s.get("text", "")) else s for s in sources]


def generate_persona_explanation(state: State, runtime: Runtime[Context]) -> dict:
    """A supplementary explanation for one reviewed reader profile; never a verdict."""
    print("[generate_persona_explanation]")
    ctx = runtime.context
    persona: dict[str, Any] = dict(state.get("persona_explanation") or {})
    cards = state.get("evidence_cards") or {}
    feedback = (state.get("verification") or {}).get("feedback") or []
    classification = state.get("classification") or {}
    # The reader is chosen once per review; a retry explains for the same reader.
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
    sources = mark_mandatory(list(cards.get("sources") or []), state.get("display_check") or {})
    persona.update(
        generate_persona(
            sources,
            cards.get("cards") or [],
            classification,
            ctx,
            feedback,
            profiles_path=Path(ctx.rubric_dir) / PROFILES_FILE,
            profile=persona["profile"],
        )
    )
    return {"persona_explanation": persona}


def judge_explanation_original(state: State, runtime: Runtime[Context]) -> dict:
    """The original side of explanation duty, beside the persona explanation it does not read.

    `judge_explanation_duty` reuses these rows; without them (a rerun from an older checkpoint,
    or nothing to judge yet) it judges the original side itself.
    """
    print("[judge_explanation_original]")
    classification = state.get("classification") or {}
    page = state.get("product_page") or {}
    if not classification.get("product_type") or not classification.get("page_type"):
        return {}
    if not page.get("html"):
        return {}
    check: dict[str, Any] = dict(state.get("explanation_duty_check") or {})
    check.update(judge_original(page, classification, runtime.context))
    return {"explanation_duty_check": check}


def judge_explanation_duty(state: State, runtime: Runtime[Context]) -> dict:
    print("[judge_explanation_duty]")
    check: dict[str, Any] = dict(state.get("explanation_duty_check") or {})
    page: dict[str, Any] = dict(state.get("product_page") or {})
    persona: dict[str, Any] = dict(state.get("persona_explanation") or {})
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
            ledger=[],
            fidelity=[],
        )
    elif not page.get("html"):
        check.update(
            items=blocked("product_page.html이 비어 있음"),
            original=[],
            plain=[],
            ledger=[],
            fidelity=[],
        )
    elif not persona.get("html"):
        check.update(
            items=check.get("items")
            or blocked(
                "persona_explanation.html이 비어 있음;"
                " generate_persona_explanation을 먼저 실행해야 함"
            ),
            original=check.get("original") or [],
            plain=[],
            ledger=[],
            fidelity=[],
        )
    else:
        feedback = (state.get("verification") or {}).get("feedback") or []
        judged = judge_explanation(
            page,
            {"html": persona["html"]},
            classification,
            runtime.context,
            # An empty original side (every item ruled out) is a result, not a missing one.
            check.get("original") if check.get("items") else None,
            check.get("items") or None,
            feedback=feedback,
        )
        # Rubric-level differences are tied to the units they came from; one tied to an accepted
        # unit (e.g. a warning whose cause the explanation changed) fails verification.
        rubric_fidelity = map_rubric_fidelity(
            judged.get("fidelity") or [], persona.get("units") or []
        )
        ledger = check_ledger(
            persona.get("fact_ledger") or [],
            persona.get("units") or [],
            visible_text(page["html"]),
            visible_text(persona["html"]),
            runtime.context.model,
            ask,
        )
        check.update(
            {**judged, "ledger": ledger["ledger"], "fidelity": rubric_fidelity + ledger["fidelity"]}
        )
    return {"explanation_duty_check": check}


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
                state.get("explanation_duty_check") or {},
                int(previous.get("loop_count") or 0),
            ),
        }
    }


def retry_dispatch(state: State) -> dict:
    print("[retry_dispatch]")
    verification: dict[str, Any] = dict(state.get("verification") or {})
    verification.update(plan_retry(state.get("verification") or {}))
    return {"verification": verification}


def _explanation_of(state: State) -> dict[str, Any]:
    legacy: dict[str, Any] = dict(state).get("plain_language") or {}  # type: ignore[assignment]
    return dict(state.get("persona_explanation") or legacy)


def report_for(state: Mapping[str, Any], ctx: Context, stop: Mapping[str, Any]) -> dict:
    """The Report for whatever State holds; `stop` says why the run ended where it did."""
    report: dict[str, Any] = dict(state.get("report") or {})
    report.update(
        build_report(
            state["product_page"],
            state.get("classification") or {},
            state.get("display_check") or {},
            # A checkpoint from before the persona explanation still has `plain_language`.
            _explanation_of(cast(State, state)),
            state.get("explanation_duty_check") or {},
            state.get("verification") or {},
            stop,
            bindings=rubric_bindings(ctx.db_path),
            previous_cost=report.get("cost"),
            cards=state.get("evidence_cards") or {},
            references=state.get("reference_cases") or {},
            labels=rubric_labels(ctx.db_path),
        )
    )
    return report


def end_report(state: State, runtime: Runtime[Context]) -> dict:
    print("[end_report]")
    stop = {**escalation(state.get("verification") or {}), "max_loops": MAX_LOOPS}
    return {"report": report_for(state, runtime.context, stop)}
