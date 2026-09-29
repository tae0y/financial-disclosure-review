"""Reference-case linking agent against a real-page gold set (backlog B4). Paid: it runs the agent.

The gold file (`eval/fixtures/gold/reference_links.json`, local only) lists, per page, the cards
that should link to a case (`expected`: card quote substring -> acceptable case ids) and cards
that must not link (`negatives`: card quote substrings). Cards come from the page's evidence
cards: the two lottecard fixtures through the agentic cassette (free), live pages from their
checkpoints. The linking agent is a tool loop and has no cassette, so every run calls the model;
the JSON result is the record.

    uv run python eval/linking_eval.py --checkpoints data/live3/checkpoints.sqlite [--rounds 1]

Measured: expected-link recall (a card linked to an acceptable case), false links (a link whose
card is a negative, or a link to an unacceptable case for an expected card), links on cards the
gold does not mention (reported for review, not scored), partial-detectability notes present on
every partial/review_required/out_of_scope link, stop reasons and cost, and the completion rate:
the share of rounds that ended by `finish` or the link cap. A round cut short by its turn or
budget limit is incomplete and stays in the recall denominator with the links it did find.
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

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from langgraph.checkpoint.sqlite import SqliteSaver  # noqa: E402

from financial_disclosure_review.core.context import Context, default_rubric_dir  # noqa: E402
from financial_disclosure_review.core.text import norm  # noqa: E402
from financial_disclosure_review.core.usage import current, start_run  # noqa: E402
from financial_disclosure_review.domain.evidence_cards import extract_evidence_cards  # noqa: E402
from financial_disclosure_review.evaluation.cassette import Cassette  # noqa: E402
from financial_disclosure_review.evaluation.run_meta import run_meta  # noqa: E402
from financial_disclosure_review.knowledge.linking import (  # noqa: E402
    SYSTEM_PROMPT,
    link_reference_cases,
)

GOLD = ROOT / "eval" / "fixtures" / "gold" / "reference_links.json"
PARTIAL = ("partial", "review_required", "out_of_scope")
COMPLETE_STOPS = ("finished", "link_cap")


def page_cards(page: dict, checkpoints: str | None, cassette: Cassette, ctx: Context):
    """(cards, classification) of one gold page: a fixture or a live thread."""
    if page["source"] == "fixture":
        fixture = json.loads(
            (ROOT / "eval" / "fixtures" / f"{page['name']}.json").read_text("utf-8")
        )
        classification = fixture["classification"]
        cards = extract_evidence_cards(fixture["page"], classification, ctx, ask=cassette.ask)
        return cards["cards"], classification
    if not checkpoints:
        raise SystemExit(f"{page['name']} needs --checkpoints")
    with SqliteSaver.from_conn_string(checkpoints) as saver:
        checkpoint = saver.get({"configurable": {"thread_id": page["name"]}})
        if checkpoint is None:
            raise SystemExit(f"no checkpoint for {page['name']}")
        state = checkpoint["channel_values"]
    return (state.get("evidence_cards") or {}).get("cards") or [], state.get("classification")


def _matches(card: dict, needle: str) -> bool:
    return norm(needle) in norm(card.get("quote", ""))


def score(page: dict, cards: list[dict], result: dict) -> dict[str, Any]:
    by_id = {c["id"]: c for c in cards}
    links = result.get("links") or []
    found, false_links, extra = [], [], []
    for needle, acceptable in page["expected"].items():
        hit = any(
            link["case_id"] in acceptable
            and any(_matches(by_id[c], needle) for c in link["card_ids"] if c in by_id)
            for link in links
        )
        found.append({"card": needle[:60], "found": hit})
    for link in links:
        linked = [by_id[c] for c in link["card_ids"] if c in by_id]
        negative = [n for n in page["negatives"] if any(_matches(c, n) for c in linked)]
        wrong_case = [
            n
            for n, ok in page["expected"].items()
            if any(_matches(c, n) for c in linked) and link["case_id"] not in ok
        ]
        known = negative or any(any(_matches(c, n) for c in linked) for n in page["expected"])
        row = {"case_id": link["case_id"], "cards": [c["quote"][:60] for c in linked]}
        if negative or wrong_case:
            false_links.append(row)
        elif not known:
            extra.append({**row, "same_pattern": link.get("same_pattern", "")})
    partial = [link for link in links if link.get("page_only_detectability") in PARTIAL]
    return {
        "expected": len(page["expected"]),
        "found": sum(f["found"] for f in found),
        "found_detail": found,
        "links": len(links),
        "false_links": false_links,
        "unscored_links": extra,
        "partial_notes_ok": all(link.get("page_only_note") for link in partial),
        "stop_reason": result.get("stop_reason"),
        "status": result.get("status"),
        "searches": (result.get("method") or {}).get("searches"),
        "reads": (result.get("method") or {}).get("reads"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--checkpoints", default="")
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--model", default="gpt-5-mini")
    parser.add_argument("--max-usd", type=float, default=1.0)
    args = parser.parse_args()
    gold = json.loads(GOLD.read_text(encoding="utf-8"))
    cassette = Cassette(ROOT / "eval" / "cassettes" / "agentic-gpt-5-mini.json", mode="replay")
    start_run(max_calls=200, max_usd=args.max_usd)
    ctx = Context(model=args.model)
    rubric_dir = Path(default_rubric_dir())
    rows = []
    for page in gold["pages"]:
        cards, classification = page_cards(page, args.checkpoints, cassette, ctx)
        for round_no in range(1, args.rounds + 1):
            result = link_reference_cases(
                cards,
                classification or {},
                ctx.db_path,
                ctx=ctx,
                risk_kinds_path=rubric_dir / "case_risk_kinds.yaml",
                corpus_path=rubric_dir / "case_corpus.yaml",
            )
            rows.append({"page": page["name"], "round": round_no, **score(page, cards, result)})
            print(json.dumps(rows[-1], ensure_ascii=False)[:400])
    expected = sum(r["expected"] for r in rows)
    links = sum(r["links"] for r in rows)
    overall = {
        "rounds": args.rounds,
        "pages": len(gold["pages"]),
        "recall": round(sum(r["found"] for r in rows) / expected, 3) if expected else None,
        "false_link_rate": round(sum(len(r["false_links"]) for r in rows) / links, 3)
        if links
        else None,
        "links": links,
        "unscored_links": sum(len(r["unscored_links"]) for r in rows),
        "partial_notes_ok": all(r["partial_notes_ok"] for r in rows),
        "stop_reasons": dict(Counter(r["stop_reason"] for r in rows)),
        "completion_rate": round(
            sum(r["stop_reason"] in COMPLETE_STOPS for r in rows) / len(rows), 3
        )
        if rows
        else None,
        "statuses": dict(Counter(r["status"] for r in rows)),
        "cost": current().summary(),
    }
    meta = run_meta("linking_agent", prompts={"system": SYSTEM_PROMPT}, gold=GOLD)
    stamp = datetime.now().strftime("%y%m%d-%H%M%S")
    folder = ROOT / "eval" / "results"
    folder.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        {"meta": meta, "overall": overall, "rows": rows}, ensure_ascii=False, indent=1
    )
    (folder / f"{stamp}-linking.json").write_text(text, encoding="utf-8")
    print(json.dumps(overall, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
