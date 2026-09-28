"""Invokes the review graph per request in a worker thread; each run gets a fresh, serial meter."""

import time
import uuid
from datetime import datetime
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite import SqliteSaver

from ...core.context import Context
from ...core.state import empty_state
from ...core.usage import start_run
from ...graph.build import build_review_graph
from ..schemas import Detail, RunResult
from ..settings import AgentSettings


def new_thread_id(prefix: str = "review") -> str:
    """A sortable thread id with a random tail, since a timestamp alone can collide across calls."""
    return f"{prefix}-{datetime.now().strftime('%y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"


def _context(settings: AgentSettings, model: str | None) -> Context:
    return Context(
        model=model or settings.model,
        data_dir=settings.data_dir,
        db_path=settings.resolved_db_path(),
        rubric_dir=settings.rubric_dir,
        allowed_hosts=settings.allowed_hosts,
    )


def summarize(state: dict[str, Any], detail: Detail = Detail.summary) -> dict[str, Any]:
    """A compact view of final State; `full` adds rows and explanation HTML, never page HTML."""
    page = state.get("product_page") or {}
    display = state.get("display_check") or {}
    persona = state.get("persona_explanation") or {}
    duty = state.get("explanation_duty_check") or {}
    verification = state.get("verification") or {}
    classification = state.get("classification") or {}
    cards = state.get("evidence_cards") or {}
    references = state.get("reference_cases") or {}

    applied = [row for row in duty.get("items") or [] if row.get("applied")]
    view: dict[str, Any] = {
        "product_page": {
            "url": page.get("url"),
            "product": page.get("product"),
            "html_chars": len(page.get("html") or ""),
            "snapshot_count": len(page.get("snapshots") or []),
            "status": page.get("status"),
            "stop_reason": page.get("stop_reason"),
            "error": page.get("error"),
            "open_gaps": sum(
                1
                for gap in (page.get("coverage") or {}).get("gaps") or []
                if gap.get("status") in ("open", "unresolved")
            ),
            "agent_steps": len(page.get("agent_trace") or []),
        },
        "classification": dict(classification),
        "evidence_cards": {
            "status": cards.get("status"),
            "cards": len(cards.get("cards") or []),
            "rejected": len(cards.get("rejected") or []),
            "open_gaps": sum(
                1
                for gap in cards.get("coverage_gaps") or []
                if gap.get("status") in ("open", "unresolved")
            ),
        },
        "reference_cases": {
            "status": references.get("status"),
            "links": len(references.get("links") or []),
        },
        "display_check": {
            "status": (display.get("judgments") or {}).get("status"),
            "reason": (display.get("judgments") or {}).get("reason"),
            "item_count": len(display.get("items") or []),
            "verdicts": [
                {
                    "code": row.get("code"),
                    "verdict": row.get("verdict"),
                    "reason": row.get("reason"),
                }
                for row in display.get("items") or []
            ],
        },
        "persona_explanation": {
            "status": persona.get("status"),
            "profile": (persona.get("profile") or {}).get("id"),
            "accepted_units": sum(
                1 for u in persona.get("units") or [] if u.get("status") == "accepted"
            ),
            "reverted_units": sum(
                1 for u in persona.get("units") or [] if u.get("status") == "reverted"
            ),
            "html_chars": len(persona.get("html") or ""),
        },
        "explanation_duty_check": {
            "applied": len(applied),
            "item_count": len(duty.get("items") or []),
            "fidelity_differences": len(duty.get("fidelity") or []),
        },
        "verification": {
            "passed": verification.get("passed"),
            "failed_modules": verification.get("failed_modules"),
            "loop_count": verification.get("loop_count"),
            "reasons": verification.get("reasons"),
        },
    }
    if detail is Detail.full:
        view["product_page"]["coverage"] = page.get("coverage") or {}
        view["product_page"]["agent_trace"] = page.get("agent_trace") or []
        view["display_check"]["items"] = display.get("items") or []
        view["evidence_cards"]["rows"] = cards.get("cards") or []
        view["reference_cases"]["rows"] = references.get("links") or []
        view["persona_explanation"]["html"] = persona.get("html")
        view["persona_explanation"]["units"] = persona.get("units") or []
        view["persona_explanation"]["fact_ledger"] = persona.get("fact_ledger") or []
        view["explanation_duty_check"]["items"] = duty.get("items") or []
        view["explanation_duty_check"]["original"] = duty.get("original") or []
        view["explanation_duty_check"]["plain"] = duty.get("plain") or []
        view["explanation_duty_check"]["fidelity"] = duty.get("fidelity") or []
        view["explanation_duty_check"]["ledger"] = duty.get("ledger") or []
    return view


def _report(state: dict[str, Any]) -> dict[str, Any]:
    """The report as-is; it is already reviewer-sized and carries no page HTML."""
    return dict(state.get("report") or {})


def _result(
    state: dict[str, Any], thread_id: str, detail: Detail, elapsed: float, cost: dict[str, Any]
) -> RunResult:
    report = _report(state)
    page = state.get("product_page") or {}
    return RunResult(
        thread_id=thread_id,
        url=page.get("url"),
        status=report.get("status"),
        decision=report.get("decision"),
        summary=summarize(state, detail),
        report=report,
        cost=cost,
        elapsed_seconds=round(elapsed, 1),
    )


def run_review(
    url: str,
    settings: AgentSettings,
    *,
    model: str | None = None,
    thread_id: str | None = None,
    detail: Detail = Detail.summary,
    max_calls: int | None = None,
    max_usd: float | None = None,
) -> RunResult:
    """Review one URL from a fresh State, writing checkpoints under its own thread id."""
    thread = thread_id or new_thread_id()
    config: RunnableConfig = {"configurable": {"thread_id": thread}}
    state = empty_state()
    state["product_page"] = {"url": url}

    meter = start_run(
        max_calls=settings.max_calls if max_calls is None else max_calls,
        max_usd=settings.max_usd if max_usd is None else max_usd,
    )
    started = time.time()
    with SqliteSaver.from_conn_string(settings.resolved_checkpoints()) as saver:
        final = build_review_graph(saver).invoke(state, config, context=_context(settings, model))
    return _result(dict(final), thread, detail, time.time() - started, meter.summary())


def run_rerun(
    thread_id: str,
    from_node: str,
    settings: AgentSettings,
    *,
    model: str | None = None,
    detail: Detail = Detail.summary,
    max_calls: int | None = None,
    max_usd: float | None = None,
) -> RunResult:
    """Resume a recorded thread at the checkpoint whose next node is `from_node`."""
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    meter = start_run(
        max_calls=settings.max_calls if max_calls is None else max_calls,
        max_usd=settings.max_usd if max_usd is None else max_usd,
    )
    started = time.time()
    with SqliteSaver.from_conn_string(settings.resolved_checkpoints()) as saver:
        graph = build_review_graph(saver)
        before = next((s for s in graph.get_state_history(config) if from_node in s.next), None)
        if before is None:
            raise LookupError(
                f"thread {thread_id!r} has no checkpoint whose next node is {from_node!r}"
            )
        final = graph.invoke(None, before.config, context=_context(settings, model))
    return _result(dict(final), thread_id, detail, time.time() - started, meter.summary())
