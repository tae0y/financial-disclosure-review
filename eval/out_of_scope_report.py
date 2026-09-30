"""Produce the reviewer-facing document for an out-of-scope page, replayed for free.

The demo has three scenes. Two of them already have a recorded artifact a presenter can fall
back on when the venue's network is down: `data/reports/demo-260929.md` for the representative
case and `eval/results/*-duty-flip-record.*` for the defect-injection case (recorded under the
explanation-duty criteria, before the 2026-09-30 switch to `disclosure-flip`). The exception case —
"this screen is not ours to review" — had only the classification suite's JSON, which shows the
verdict but not the document the requester actually receives.

This script closes that gap. It replays the recorded classification calls (no model call, no
cost), then builds the report through the same `build_report` the graph's `end_report` node
calls, so the document is the real output of the real code path rather than a hand-written
sample.

    uv run python eval/out_of_scope_report.py

Writes one markdown file per out-of-scope fixture into `data/reports/`.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from financial_disclosure_review.core.context import Context  # noqa: E402
from financial_disclosure_review.core.usage import current, start_run  # noqa: E402
from financial_disclosure_review.domain.classification import classify_page  # noqa: E402
from financial_disclosure_review.domain.report import build_report  # noqa: E402
from financial_disclosure_review.evaluation.cassette import Cassette  # noqa: E402
from financial_disclosure_review.graph.routes import NON_REVIEW  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "classify"
CASSETTE = ROOT / "eval" / "cassettes" / "gpt-5-mini.json"
OUT_DIR = ROOT / "data" / "reports"

# The four checking modules never run on this path, so the report is built from empty results —
# the same values `end_report` sees when `route_after_classify` sends a non-review verdict
# straight to it.
NOT_RUN: dict = {}
VERIFICATION = {
    "passed": True,
    "reasons": [],
    "failed_modules": [],
    "feedback": [],
    "loop_count": 0,
}


def main() -> int:
    model = Context.model
    cassette = Cassette(CASSETTE, mode="replay")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    written = []
    for path in sorted(FIXTURES.glob("*.json")):
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if fixture["expected"]["product_type"] not in NON_REVIEW:
            continue

        start_run()
        page = {key: fixture[key] for key in ("url", "product", "html")}
        classification = classify_page(page, model, ask=cassette.ask)
        report = build_report(
            page,
            classification,
            NOT_RUN,
            NOT_RUN,
            NOT_RUN,
            VERIFICATION,
            {"max_loops": 2},
        )
        out = OUT_DIR / f"out-of-scope-{path.stem}.md"
        out.write_text(report["markdown"], encoding="utf-8")
        written.append((path.stem, report["status"], out))
        print(f"{path.stem}: {report['status']} -> {out.relative_to(ROOT)}")

    usage = current().summary()
    print(f"cassette: replay, hits={cassette.hits}, misses={cassette.misses}")
    print(f"cost: {usage}")
    if not written:
        print("no out-of-scope fixture found", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
