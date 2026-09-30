"""Ad-disclosure defect injection over several real pages, both arms, pooled.

`evaluate --suite disclosure-flip` deletes 3 sentences on one page. This runs the same suite
(`run_disclosure_flip`, same prompts and arms) on every page in
`eval/cases/disclosure_flip_multi.json` with more deletions and controls per page, then pools
the counts:

    uv run python eval/disclosure_flip_multi.py                    # replay, $0
    uv run python eval/disclosure_flip_multi.py --record --page shinhan-card   # paid, one page

Each page records into its own cassette under `eval/cassettes/disclosure-multi/`, so pages can
record in parallel processes. Answers already in `eval/cassettes/gpt-5-mini.json` (the one-page
suite) are reused and not copied.

A deletion whose label is in doubt — after it, either arm says 적합 citing another sentence that is
really on the edited page — is counted apart ("label doubt") and left out of the second rate.
"""

import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from financial_disclosure_review.core.context import Context  # noqa: E402
from financial_disclosure_review.core.usage import current, start_run  # noqa: E402
from financial_disclosure_review.evaluation.cassette import Cassette  # noqa: E402
from financial_disclosure_review.evaluation.metrics import metrics_for  # noqa: E402
from financial_disclosure_review.evaluation.run_meta import run_meta  # noqa: E402
from financial_disclosure_review.evaluation.suites import (  # noqa: E402
    load_cases,
    run_disclosure_flip,
)

CASES = ROOT / "eval" / "cases" / "disclosure_flip_multi.json"
PARTS = ROOT / "eval" / "cassettes" / "disclosure-multi"
ARMS = ("pipeline", "ablation")


def page_config(page: dict) -> dict:
    config = load_cases(ROOT / page["config"]) if page.get("config") else dict(page)
    config["base_html"] = str((ROOT / config["base_html"]).resolve())
    return config


def open_cassette(name: str, model: str, mode: str) -> tuple[Cassette, set[str]]:
    """This page's cassette, with the one-page suite's answers mixed in (not saved back)."""
    cassette = Cassette(PARTS / f"{name}-{model}.json", mode=mode)
    shared = ROOT / "eval" / "cassettes" / f"{model}.json"
    seeded: set[str] = set()
    if shared.exists():
        entries = json.loads(shared.read_text(encoding="utf-8")).get("entries", {})
        seeded = set(entries) - set(cassette.entries)
        cassette.entries = {**entries, **cassette.entries}
    return cassette, seeded


def label_doubt(results: dict[str, dict]) -> set[str]:
    """Codes where some arm stayed 적합 on another sentence still on the page."""
    return {
        row["code"]
        for result in results.values()
        for row in result["rows"]
        if row["kind"] == "결함 주입"
        and row["landed"]
        and row.get("after_verdict") == "적합"
        and row.get("after_quote_on_page")
    }


def wilson(hit: int, total: int) -> list[float] | None:
    """95% Wilson interval, so a pooled rate is read with its sample size."""
    if not total:
        return None
    z, p = 1.96, hit / total
    centre = (p + z * z / (2 * total)) / (1 + z * z / total)
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return [round(max(0.0, centre - half), 3), round(min(1.0, centre + half), 3)]


def page_summary(results: dict[str, dict]) -> dict:
    doubt = label_doubt(results)
    out: dict[str, Any] = {"label_doubt": sorted(doubt)}
    for arm, result in results.items():
        m = metrics_for(result)
        injected = [r for r in result["rows"] if r["kind"] == "결함 주입" and r["landed"]]
        clean = [r for r in injected if r["code"] not in doubt]
        out[arm] = {
            "injected": m["injected"],
            "detected": m["detected"],
            "clean_injected": len(clean),
            "clean_detected": sum(1 for r in clean if r.get("detected")),
            "softened": m["softened_to_unjudged"],
            "failed": m["failed"],
            "controls": m["controls"],
            "controls_flipped": m["controls_flipped"],
            "false_flips": m["false_flips"],
            "quoted": m["quote_groundedness"]["quoted"],
            "quote_found": m["quote_groundedness"]["found"],
            "base_verdicts": m["base_verdicts"],
            "missed": m["missed"],
        }
    return out


def pooled(pages: dict[str, dict]) -> dict:
    total = {}
    for arm in ARMS:
        keys = ("injected", "detected", "clean_injected", "clean_detected", "softened")
        sums: dict[str, Any] = {k: sum(p[arm][k] for p in pages.values()) for k in keys}
        for k in ("controls", "controls_flipped", "quoted", "quote_found"):
            sums[k] = sum(p[arm][k] for p in pages.values())
        sums["detection_ci95"] = wilson(sums["detected"], sums["injected"])
        sums["clean_detection_ci95"] = wilson(sums["clean_detected"], sums["clean_injected"])
        quoted = sums["quoted"]
        sums["quote_rate"] = round(sums["quote_found"] / quoted, 3) if quoted else None
        total[arm] = sums
    return total


def render(run: dict) -> str:
    lines = [
        "---",
        "ai-generated: true",
        "human-review: false",
        "---",
        "",
        "# 광고 의무표시 결함 주입 — 여러 페이지",
        "",
        f"- 실행 시각: {run['generated_at']}, 모드: {run['mode']}, 모델: {run['model']}",
        f"- 삭제 상한 페이지당 {run['flips']}건, 대조군 페이지당 {run['controls']}건",
        f"- 비용: {run['cost']}",
        "",
        "## 합계",
        "",
        "| 지표 | pipeline | ablation |",
        "|---|---|---|",
    ]
    p, a = run["pooled"]["pipeline"], run["pooled"]["ablation"]

    def frac(d: dict, hit: str, total: str) -> str:
        return f"{d[hit]}/{d[total]}"

    lines += [
        f"| 지운 필수 문구 탐지 | {frac(p, 'detected', 'injected')} {p['detection_ci95']} "
        f"| {frac(a, 'detected', 'injected')} {a['detection_ci95']} |",
        f"| 정답 의심 제외 탐지 | {frac(p, 'clean_detected', 'clean_injected')} "
        f"{p['clean_detection_ci95']} | {frac(a, 'clean_detected', 'clean_injected')} "
        f"{a['clean_detection_ci95']} |",
        f"| 판정 불가로 보류 | {p['softened']} | {a['softened']} |",
        f"| 대조군 중 항목이 뒤집힌 대조군 | {frac(p, 'controls_flipped', 'controls')} "
        f"| {frac(a, 'controls_flipped', 'controls')} |",
        f"| 인용이 페이지에 실재 | {frac(p, 'quote_found', 'quoted')} ({p['quote_rate']}) "
        f"| {frac(a, 'quote_found', 'quoted')} ({a['quote_rate']}) |",
        "",
        "대괄호는 95% Wilson 구간입니다.",
        "",
        "## 페이지별",
        "",
        "| 페이지 | 구성 | 기준 판정 | 탐지 | 정답 의심 제외 | 미탐 | 대조군 뒤집힘 | 인용 실재 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name, page in run["pages"].items():
        for arm in ARMS:
            d = page[arm]
            lines.append(
                f"| {name} | {arm} | {d['base_verdicts']} | {d['detected']}/{d['injected']} "
                f"| {d['clean_detected']}/{d['clean_injected']} | {', '.join(d['missed']) or '-'} "
                f"| {d['controls_flipped']}/{d['controls']} {d['false_flips'] or ''} "
                f"| {d['quote_found']}/{d['quoted']} |"
            )
        if page["label_doubt"]:
            lines.append(f"| {name} | 정답 의심 | {', '.join(page['label_doubt'])} | | | | | |")
    lines += ["", "## 삭제 상세", ""]
    for name, results in run["raw"].items():
        for arm, result in results.items():
            lines.append(f"### {name} — {arm}")
            lines.append("")
            lines.append("| 케이스 | 삭제 후 | 삭제된 문장 | 삭제 후 근거 |")
            lines.append("|---|---|---|---|")
            for row in result["rows"]:
                after = row.get("after_verdict")
                quote = (row.get("after_quote") or "")[:80]
                lines.append(f"| {row['case']} | {after} | {row['removed_quote'][:90]} | {quote} |")
            lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--page", action="append", default=[])
    parser.add_argument("--flips", type=int, default=6)
    parser.add_argument("--controls", type=int, default=2)
    parser.add_argument("--model", default="gpt-5-mini")
    parser.add_argument("--max-usd", type=float, default=0.5)
    parser.add_argument("--max-calls", type=int, default=60)
    args = parser.parse_args()
    mode = "record" if args.record else "replay"
    cases = load_cases(CASES)
    pages = [p for p in cases["pages"] if not args.page or p["name"] in args.page]
    start_run(max_calls=args.max_calls, max_usd=args.max_usd)
    ctx = Context(model=args.model)

    raw: dict[str, dict] = {}
    stats = {}
    for page in pages:
        cassette, seeded = open_cassette(page["name"], args.model, mode)
        config = page_config(page)
        try:
            raw[page["name"]] = {
                arm: run_disclosure_flip(
                    ctx, cassette, config, arm=arm, max_flips=args.flips, controls=args.controls
                )
                for arm in ARMS
            }
        finally:
            for key in seeded:
                cassette.entries.pop(key, None)
            if mode == "record":
                cassette.save()
            stats[page["name"]] = cassette.stats()

    summaries = {name: page_summary(results) for name, results in raw.items()}
    run = {
        "meta": run_meta("disclosure-flip multi-page (cassette)", gold=CASES),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": mode,
        "model": args.model,
        "flips": args.flips,
        "controls": args.controls,
        "cassettes": stats,
        "cost": current().summary(),
        "pooled": pooled(summaries),
        "pages": summaries,
        "raw": raw,
    }
    stamp = datetime.now().strftime("%y%m%d-%H%M%S")
    suffix = "-".join(args.page) if args.page else "all"
    out = ROOT / "eval" / "results" / f"{stamp}-disclosure-multi-{suffix}-{mode}"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".json").write_text(
        json.dumps(run, ensure_ascii=False, indent=1, default=str), encoding="utf-8"
    )
    out.with_suffix(".md").write_text(render(run), encoding="utf-8")
    print(json.dumps(run["pooled"], ensure_ascii=False, indent=1))
    print("wrote", out.with_suffix(".md"))


if __name__ == "__main__":
    main()
