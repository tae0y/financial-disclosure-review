"""Stage 4 agent-loop metrics over finished live reviews (backlog F1). No model call.

Reads the final State of each thread from a checkpoint DB and measures the page agent, the
reference-case linking agent and the reader selection, per page and overall:

- evidence-gap closure: of the gaps an action could close (`unexpanded_control`, `hidden_text`),
  how many were closed; hidden text set aside as unreachable is counted separately;
- unnecessary actions: interactions that were allowed but revealed nothing new;
- blocked actions: interactions the tools refused;
- stop reasons, status, per-page cost, calls and time;
- one outcome per requested thread (complete / insufficient / collection_failed / interrupted /
  no_report / no_checkpoint) and the success rate over every requested thread, so a crash or a
  missing report counts as a failure instead of dropping out of the denominator.

    uv run python eval/agent_loop_eval.py --checkpoints data/live3/checkpoints.sqlite \
        --thread f1-lottecard-lasvegas --thread f1-shinhan-card ...

Writes `eval/results/<timestamp>-agent-loop.{json,md}`.
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from langgraph.checkpoint.sqlite import SqliteSaver  # noqa: E402

from financial_disclosure_review.domain.product_page.discover import (  # noqa: E402
    SYSTEM_PROMPT as PAGE_PROMPT,
)
from financial_disclosure_review.evaluation.agent_outcomes import (  # noqa: E402
    outcome_rates,
    page_outcome,
)
from financial_disclosure_review.evaluation.run_meta import run_meta  # noqa: E402
from financial_disclosure_review.knowledge.linking import (  # noqa: E402
    SYSTEM_PROMPT as LINK_PROMPT,
)

ACTIONABLE = ("unexpanded_control", "hidden_text")


def final_state(saver: SqliteSaver, thread_id: str) -> dict[str, Any] | None:
    """The thread's last State, or None when it was never checkpointed (counted as a failure)."""
    checkpoint = saver.get({"configurable": {"thread_id": thread_id}})
    return None if checkpoint is None else dict(checkpoint["channel_values"])


def page_metrics(thread_id: str, state: dict[str, Any] | None) -> dict[str, Any]:
    outcome = page_outcome(state)
    state = state or {}
    page = state.get("product_page") or {}
    gaps = (page.get("coverage") or {}).get("gaps") or []
    # Gaps inside the submitted regions only (recorded since 2026-09-29); older runs have no
    # flag, and then every gap counts.
    actionable = [g for g in gaps if g.get("kind") in ACTIONABLE and g.get("in_region", True)]
    trace = page.get("agent_trace") or []
    interactions = [t for t in trace if t.get("tool") == "interact"]
    allowed = [t for t in interactions if not t.get("blocked")]
    refs = state.get("reference_cases") or {}
    persona = state.get("persona_explanation") or {}
    cost = (state.get("report") or {}).get("cost") or {}
    return {
        "thread": thread_id,
        "outcome": outcome,
        "url": page.get("url"),
        "status": page.get("status"),
        "stop_reason": page.get("stop_reason"),
        "report_status": (state.get("report") or {}).get("status"),
        "actionable_gaps": len(actionable),
        "closed_gaps": sum(g.get("status") == "closed" for g in actionable),
        "unreachable_hidden": sum(
            g.get("kind") == "hidden_text" and g.get("status") == "unresolved" for g in actionable
        ),
        "open_gaps": sum(g.get("status") == "open" for g in actionable),
        "turns": max((t.get("turn", 0) for t in trace), default=0),
        "interactions": len(interactions),
        "unnecessary_actions": sum(not t.get("new_evidence") for t in allowed),
        "blocked_actions": sum(bool(t.get("blocked")) for t in interactions),
        "blocked_reasons": [
            t.get("blocked_reason", "")[:80] for t in interactions if t.get("blocked")
        ],
        "case_links": len(refs.get("links") or []),
        "case_link_stop": refs.get("stop_reason"),
        "case_link_turns": max(
            (t.get("turn", 0) for t in refs.get("agent_trace") or []), default=0
        ),
        "reader_chosen_by": (persona.get("selection") or {}).get("decided_by"),
        "reader": (persona.get("profile") or {}).get("id"),
        "usd": cost.get("usd"),
        "calls": cost.get("calls"),
        "seconds": cost.get("elapsed_seconds"),
    }


def overall(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def ratio(num: int, den: int) -> float | None:
        return round(num / den, 3) if den else None

    actionable = sum(r["actionable_gaps"] for r in rows)
    interactions = sum(r["interactions"] for r in rows)
    allowed = interactions - sum(r["blocked_actions"] for r in rows)
    return {
        "pages": len(rows),
        **outcome_rates(r["outcome"] for r in rows),
        "gap_closure_rate": ratio(sum(r["closed_gaps"] for r in rows), actionable),
        "unreachable_hidden_share": ratio(sum(r["unreachable_hidden"] for r in rows), actionable),
        "unnecessary_action_rate": ratio(sum(r["unnecessary_actions"] for r in rows), allowed),
        "blocked_action_rate": ratio(sum(r["blocked_actions"] for r in rows), interactions),
        "stop_reasons": dict(Counter(r["stop_reason"] for r in rows)),
        "statuses": dict(Counter(r["status"] for r in rows)),
        "report_statuses": dict(Counter(r["report_status"] for r in rows)),
        "usd_total": round(sum(r["usd"] or 0 for r in rows), 4),
        "usd_per_page": round(sum(r["usd"] or 0 for r in rows) / len(rows), 4) if rows else None,
        "seconds_per_page": round(sum(r["seconds"] or 0 for r in rows) / len(rows), 1)
        if rows
        else None,
    }


def markdown(rows: list[dict[str, Any]], total: dict[str, Any]) -> str:
    head = [
        "thread",
        "outcome",
        "status/stop",
        "gaps closed",
        "unreachable",
        "interact (unneeded/blocked)",
        "links",
        "reader",
        "$",
        "s",
    ]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in rows:
        cells = [
            r["thread"],
            r["outcome"],
            f"{r['status']}/{r['stop_reason']}",
            f"{r['closed_gaps']}/{r['actionable_gaps']}",
            str(r["unreachable_hidden"]),
            f"{r['interactions']} ({r['unnecessary_actions']}/{r['blocked_actions']})",
            f"{r['case_links']} ({r['case_link_stop']})",
            str(r["reader_chosen_by"]),
            str(r["usd"]),
            str(r["seconds"]),
        ]
        lines.append("| " + " | ".join(cells) + " |")
    lines += ["", "```json", json.dumps(total, ensure_ascii=False, indent=2), "```"]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument("--checkpoints", required=True)
    parser.add_argument("--thread", action="append", required=True)
    args = parser.parse_args()
    with SqliteSaver.from_conn_string(args.checkpoints) as saver:
        rows = [page_metrics(t, final_state(saver, t)) for t in args.thread]
    total = overall(rows)
    meta = run_meta(
        "page_agent+linking_agent+reader_selection (live checkpoints)",
        prompts={"page_agent": PAGE_PROMPT, "linking_agent": LINK_PROMPT},
    )
    stamp = datetime.now().strftime("%y%m%d-%H%M%S")
    out = ROOT / "eval" / "results"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{stamp}-agent-loop.json").write_text(
        json.dumps({"meta": meta, "pages": rows, "overall": total}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    note = (
        f"meta: {meta['implementation']}, commit {meta['commit']}"
        f"{' (dirty)' if meta['dirty'] else ''}, prompts {meta['prompt_sha256']}\n\n"
    )
    (out / f"{stamp}-agent-loop.md").write_text(note + markdown(rows, total), encoding="utf-8")
    print(markdown(rows, total))


if __name__ == "__main__":
    main()
