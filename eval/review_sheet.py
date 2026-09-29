"""Blank human review sheet for reader-tailored explanations (backlog F3). No model call.

Human comprehension and harmful-analogy rate cannot be measured by code. This script pulls
accepted explanation units from finished live reviews and lays them out for a person to score;
every score column is left empty. Units with an analogy or on a risk card come first, because
those are where a harmful analogy or a softened risk would show.

    uv run python eval/review_sheet.py --checkpoints data/live3/checkpoints.sqlite \
        --thread f1-lotte-lasvegas --thread f1-shinhan-revolving --out sheet.md
"""

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from langgraph.checkpoint.sqlite import SqliteSaver  # noqa: E402

RISK_KINDS = {"rate_claim", "fee_claim", "warning"}
PER_PAGE = 8


def _cell(text: str) -> str:
    return " ".join((text or "").split()).replace("|", "\\|")


def units_for(state: dict[str, Any]) -> list[dict[str, Any]]:
    persona = state.get("persona_explanation") or {}
    kinds = {c["id"]: c.get("kind") for c in (state.get("evidence_cards") or {}).get("cards") or []}
    accepted = [u for u in persona.get("units") or [] if u.get("status") == "accepted"]

    def priority(unit: dict[str, Any]) -> tuple[int, int]:
        risky = any(kinds.get(c) in RISK_KINDS for c in unit.get("card_ids") or [])
        return (0 if unit.get("analogy") else 1, 0 if risky else 1)

    return sorted(accepted, key=priority)[:PER_PAGE]


def sheet(pages: list[tuple[str, dict[str, Any]]]) -> str:
    lines = [
        "## 채점 방법",
        "",
        "- **이해도(1–5)**: 표시된 독자가 이 설명만 읽고 원 사실을 이해할 수 있는가. 1은 이해 불가,"
        " 5는 바로 이해입니다.",
        "- **사실 왜곡(Y/N)**: 설명이 원 사실의 수치·조건·예외·불이익을 바꾸거나"
        " 약하게 만들었는가.",
        "- **유해 비유(Y/N)**: 비유가 위험을 가볍게 보이게 하거나 사실과 다른 기대를 만드는가."
        " 비유가 없으면 '-'로 둡니다.",
        "- 모든 점수 칸은 비어 있습니다. AI가 채운 값은 없습니다.",
        "",
    ]
    n = 0
    for thread, state in pages:
        page = state.get("product_page") or {}
        profile = (state.get("persona_explanation") or {}).get("profile") or {}
        attributes = profile.get("attributes") or {}
        reader = (attributes.get("reader") or "").split("\n")[0]
        lines += [
            f"## {thread}",
            "",
            f"- 페이지: {page.get('url', '')}",
            f"- 독자: {reader or profile.get('id', '')}"
            f" (금융 익숙도 {attributes.get('financial_familiarity', '-')})",
            "",
            "| # | 원 사실 | 설명 | 비유 | 이해도(1–5) | 사실 왜곡(Y/N) | 유해 비유(Y/N) | 메모 |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for unit in units_for(state):
            n += 1
            fact, text = _cell(unit.get("exact_fact", "")), _cell(unit.get("explanation", ""))
            analogy = _cell(unit.get("analogy", "")) or "-"
            lines.append(f"| {n} | {fact} | {text} | {analogy} |  |  |  |  |")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--checkpoints", required=True)
    parser.add_argument("--thread", action="append", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    pages = []
    with SqliteSaver.from_conn_string(args.checkpoints) as saver:
        for thread in args.thread:
            checkpoint = saver.get({"configurable": {"thread_id": thread}})
            if checkpoint is not None:
                pages.append((thread, dict(checkpoint["channel_values"])))
    Path(args.out).write_text(sheet(pages), encoding="utf-8")
    print(f"wrote {args.out}: {sum(len(units_for(s)) for _, s in pages)} units, {len(pages)} pages")


if __name__ == "__main__":
    main()
