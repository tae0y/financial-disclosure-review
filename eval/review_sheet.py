"""Blank human review sheet for reader-tailored overviews (backlog F3). No model call.

Human comprehension and harmful-analogy rate cannot be measured by code. This script pulls the
plain-language overview of each finished live review and lays it out, paragraph by paragraph, for
a person to score; every score column is left empty. The page's risk cards (rates, fees,
warnings) are listed under each overview so the scorer can check whether a risk was softened.

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


def paragraphs_for(state: dict[str, Any]) -> list[str]:
    """The overview as shown; an overview held back by its code checks is not scored."""
    persona = state.get("persona_explanation") or {}
    return list(persona.get("overview") or []) if persona.get("html") else []


def risk_facts(state: dict[str, Any]) -> list[str]:
    cards = (state.get("evidence_cards") or {}).get("cards") or []
    return [c.get("quote", "") for c in cards if c.get("kind") in RISK_KINDS][:PER_PAGE]


def sheet(pages: list[tuple[str, dict[str, Any]]]) -> str:
    lines = [
        "## 채점 방법",
        "",
        "- **이해도(1–5)**: 표시된 독자가 이 문단만 읽고 상품을 이해할 수 있는가. 1은 이해 불가,"
        " 5는 바로 이해입니다.",
        "- **사실 왜곡(Y/N)**: 문단이 원문의 수치·조건·예외·불이익을 바꾸거나"
        " 약하게 만들었는가. 아래 위험 사실 목록과 대조합니다.",
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
            "| # | 개요 문단 | 이해도(1–5) | 사실 왜곡(Y/N) | 유해 비유(Y/N) | 메모 |",
            "|---|---|---|---|---|---|",
        ]
        paragraphs = paragraphs_for(state)
        for paragraph in paragraphs:
            n += 1
            lines.append(f"| {n} | {_cell(paragraph)} |  |  |  |  |")
        if not paragraphs:
            lines.append("| - | (게시된 개요 없음) | - | - | - | - |")
        lines += ["", "위험 사실(원문 인용):", ""]
        lines += [f"- {_cell(quote)}" for quote in risk_facts(state)] or ["- (없음)"]
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
    count = sum(len(paragraphs_for(s)) for _, s in pages)
    print(f"wrote {args.out}: {count} paragraphs, {len(pages)} pages")


if __name__ == "__main__":
    main()
