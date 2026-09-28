"""Write down what every finished review in the checkpoint DB cost, as a file the repository keeps.

The per-review cost lives on each thread's `report.cost` inside `data/checkpoints.sqlite`, which
is gitignored (it also holds whole pages). A number a reader cannot open is only a claim, so this
copies the cost of each finished review — calls, tokens, dollars, seconds, per step — into
`eval/results/<date>-cost-ledger.{json,md}`. It makes no model call.

    uv run python eval/cost_ledger.py [--checkpoints data/checkpoints.sqlite] [--out-dir DIR]
"""

import argparse
import json
import statistics
from datetime import datetime
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

ROOT = Path(__file__).resolve().parent.parent


def finished_reviews(checkpoints: str) -> list[dict]:
    rows = []
    with SqliteSaver.from_conn_string(checkpoints) as saver:
        configs = [c.config.get("configurable") or {} for c in saver.list(None)]
        threads = sorted({cfg["thread_id"] for cfg in configs if cfg.get("thread_id")})
        for thread in threads:
            latest = saver.get_tuple({"configurable": {"thread_id": thread}})
            if latest is None:
                continue
            state = latest.checkpoint["channel_values"]
            report = state.get("report") or {}
            cost = report.get("cost") or {}
            if not cost.get("calls") or cost.get("carried_forward"):
                continue  # unfinished, or a rebuild whose cost belongs to an earlier run
            page = state.get("product_page") or {}
            classification = state.get("classification") or {}
            rows.append(
                {
                    "thread": thread,
                    "checkpoint_ts": latest.checkpoint.get("ts"),
                    "url": page.get("url") or (report.get("summary") or {}).get("url"),
                    "product": (page.get("product") or {}).get("product_name"),
                    "product_type": classification.get("product_type"),
                    "status": report.get("status"),
                    "calls": cost["calls"],
                    "input_tokens": cost.get("input_tokens"),
                    "output_tokens": cost.get("output_tokens"),
                    "usd": cost.get("usd"),
                    "krw": cost.get("krw"),
                    "elapsed_seconds": cost.get("elapsed_seconds"),
                    "by_step": cost.get("by_step") or {},
                }
            )
    return rows


def render(rows: list[dict], source: str) -> str:
    lines = [
        "---",
        "ai-generated: true",
        "human-review: false",
        "---",
        "",
        "# 검토 1건당 실측 비용 기록",
        "",
        f"- 작성: {datetime.now():%Y-%m-%d %H:%M} · 출처: `{source}`의 스레드별 `report.cost`",
        "- 모델 호출 없이 체크포인트에서 옮겨 적었습니다(`uv run python eval/cost_ledger.py`).",
        "- 보고서만 다시 만든 스레드(비용 0회 또는 이월 표시)는 원래 검토 비용이 아니므로"
        " 뺐습니다.",
        "",
        "| 스레드 | 상품 | 유형 | 판정 | 호출 | 입력 tokens | 출력 tokens | 비용 | 소요 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['thread']} | {row['product'] or '-'} | {row['product_type'] or '-'}"
            f" | {row['status'] or '-'} | {row['calls']} | {row['input_tokens']:,}"
            f" | {row['output_tokens']:,} | ${row['usd']} ({row['krw']}원)"
            f" | {row['elapsed_seconds']}초 |"
        )
    if rows:
        usd = [row["usd"] for row in rows]
        secs = [row["elapsed_seconds"] for row in rows]
        lines += [
            "",
            f"{len(rows)}건: 비용 ${min(usd):.4f}~${max(usd):.4f}"
            f" (중앙값 ${statistics.median(usd):.4f}), 소요 {min(secs):.0f}~{max(secs):.0f}초"
            f" (중앙값 {statistics.median(secs):.0f}초).",
            "",
            "단계별 호출과 비용은 같은 이름의 `.json` 파일에 있습니다.",
        ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoints", default=str(ROOT / "data" / "checkpoints.sqlite"))
    parser.add_argument(
        "--out-dir",
        default=str(ROOT / "eval" / "results"),
        help="where the ledger files go (a temporary folder leaves the repository untouched)",
    )
    args = parser.parse_args()
    rows = finished_reviews(args.checkpoints)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = out_dir / f"{datetime.now():%y%m%d-%H%M%S}-cost-ledger"
    source = Path(args.checkpoints).name
    stem.with_suffix(".json").write_text(
        json.dumps({"source": source, "reviews": rows}, ensure_ascii=False, indent=1),
        encoding="utf-8",
        newline="\n",
    )
    stem.with_suffix(".md").write_text(render(rows, source), encoding="utf-8", newline="\n")
    for row in rows:
        print(f"{row['thread']}: {row['calls']} calls, ${row['usd']}, {row['elapsed_seconds']}s")
    print(f"written: {stem.with_suffix('.md')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
