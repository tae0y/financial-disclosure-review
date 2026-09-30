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
from ...domain.report.build import agent_runs
from ...graph.build import build_review_graph, invoke_to_report
from ..schemas import Detail, PersonaRequest, RunResult
from ..settings import AgentSettings


def new_thread_id(prefix: str = "review") -> str:
    """A sortable thread id with a random tail, since a timestamp alone can collide across calls."""
    return f"{prefix}-{datetime.now().strftime('%y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"


def _context(
    settings: AgentSettings, model: str | None, persona: PersonaRequest | None = None
) -> Context:
    persona = persona or PersonaRequest()
    # Nulls mean "not given"; an all-null attributes object must not outrank a free-text request.
    attributes = {k: v for k, v in (persona.attributes or {}).items() if v is not None}
    return Context(
        model=model or settings.model,
        data_dir=settings.data_dir,
        db_path=settings.resolved_db_path(),
        rubric_dir=settings.rubric_dir,
        allowed_hosts=settings.allowed_hosts,
        persona_request=persona.request or "",
        persona_uuid=persona.uuid or "",
        persona_attributes=attributes or None,
    )


def summarize(state: dict[str, Any], detail: Detail = Detail.summary) -> dict[str, Any]:
    """A compact view of final State; `full` adds rows and overview HTML, never page HTML."""
    page = state.get("product_page") or {}
    display = state.get("display_check") or {}
    persona = state.get("persona_explanation") or {}
    disclosure = state.get("ad_disclosure_check") or {}
    verification = state.get("verification") or {}
    classification = state.get("classification") or {}
    cards = state.get("evidence_cards") or {}

    applied = [row for row in disclosure.get("items") or [] if row.get("applied")]
    view: dict[str, Any] = {
        "agent_runs": agent_runs(page, persona.get("selection") or {}),
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
            "reader_chosen_by": (persona.get("selection") or {}).get("decided_by"),
            "paragraphs": len(persona.get("overview") or []) if persona.get("html") else 0,
            "problems": persona.get("problems") or [],
            "html_chars": len(persona.get("html") or ""),
        },
        "ad_disclosure_check": {
            "applied": len(applied),
            "item_count": len(disclosure.get("items") or []),
            "fidelity_differences": len(disclosure.get("fidelity") or []),
            "deferred_explanation_items": len(disclosure.get("deferred") or []),
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
        view["persona_explanation"]["html"] = persona.get("html")
        view["persona_explanation"]["overview"] = persona.get("overview") or []
        view["persona_explanation"]["selection"] = persona.get("selection") or {}
        for key in ("items", "original", "overview", "fidelity", "deferred"):
            view["ad_disclosure_check"][key] = disclosure.get(key) or []
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
    persona: PersonaRequest | None = None,
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
        final = invoke_to_report(
            build_review_graph(saver), state, config, _context(settings, model, persona)
        )
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
        final = invoke_to_report(graph, None, before.config, _context(settings, model))
    return _result(dict(final), thread_id, detail, time.time() - started, meter.summary())
