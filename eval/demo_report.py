"""Rebuild the representative review's report from its saved state, for free.

`data/reports/demo-260928.md` is the report the live run of 2026-09-28 wrote (22 calls, $0.1844,
723 seconds; transcript `eval/results/260928-demo-review-run.txt`). Its checkpoint lives in the
gitignored `data/checkpoints.sqlite`, so a reader of the repository could not otherwise re-derive
it. `eval/fixtures/demo_state_260928.json` keeps that run's final State (without the page
snapshots), and this script passes it through the same `build_report` the graph's `end_report`
node calls — no model call, no network.

    uv run python eval/demo_report.py            # writes data/reports/demo-260928.rebuilt.md

The rebuilt document must equal the committed one everywhere except the first sentence of the
cost section, which says the figures are carried forward from the original run. The script checks
that and exits non-zero if anything else differs.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from financial_disclosure_review.core.context import default_db_path  # noqa: E402
from financial_disclosure_review.core.usage import start_run  # noqa: E402
from financial_disclosure_review.domain.report import build_report  # noqa: E402
from financial_disclosure_review.graph.retry import MAX_LOOPS, escalation  # noqa: E402
from financial_disclosure_review.knowledge.rubrics import rubric_bindings  # noqa: E402

FIXTURE = ROOT / "eval" / "fixtures" / "demo_state_260928.json"
ORIGINAL = ROOT / "data" / "reports" / "demo-260928.md"
REBUILT = ROOT / "data" / "reports" / "demo-260928.rebuilt.md"


def main() -> int:
    state = json.loads(FIXTURE.read_text(encoding="utf-8"))
    start_run()
    report = build_report(
        state["page"],
        state["classification"],
        state["display_check"],
        state["plain_language"],
        state["explanation_duty_check"],
        state["verification"],
        {**escalation(state["verification"]), "max_loops": MAX_LOOPS},
        bindings=rubric_bindings(default_db_path()),
        previous_cost=state["cost"],
    )
    REBUILT.write_text(report["markdown"], encoding="utf-8", newline="\n")
    print(f"{report['status']} -> {REBUILT.relative_to(ROOT)} (calls this run: 0)")

    original = ORIGINAL.read_text(encoding="utf-8").splitlines()
    rebuilt = report["markdown"].splitlines()
    differing = [(a, b) for a, b in zip(original, rebuilt, strict=False) if a != b] + (
        [("<length>", "<length>")] if len(original) != len(rebuilt) else []
    )
    allowed = [pair for pair in differing if "원래 검토 실행" in pair[1]]
    unexpected = [pair for pair in differing if pair not in allowed]
    if unexpected:
        for a, b in unexpected[:5]:
            print(f"- committed: {a[:120]}\n+ rebuilt:   {b[:120]}")
        return 1
    print(f"identical to {ORIGINAL.relative_to(ROOT)} apart from the cost preamble")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
