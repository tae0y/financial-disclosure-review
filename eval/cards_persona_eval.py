"""Evidence cards and the persona advice on real pages (single structured calls, no agent).

Named `agentic_eval.py` until 2026-09-29. The audit of that date (A-05) found the name implied
it measured the agents while it also had a reference-case part; that part is removed along
with the case-linking node itself. The page agent and reader selection are measured by
`eval/agent_loop_eval.py`.

Runs on the two real lottecard pages kept in `eval/fixtures/` (gitignored in the public repo),
with the gold set in `eval/fixtures/gold/evidence_cards.json`. Every model call goes through a
cassette, so a recorded run replays for free:

    uv run python eval/cards_persona_eval.py            # replay, $0 (fails on a missing recording)
    uv run python eval/cards_persona_eval.py --record   # calls the model for what is not recorded

Measured, separately:
- evidence cards: quote resolution, gold recall, risk-gold recall;
- persona advice: status, the explanation-duty codes it recommends, its length, the code-check
  problems, and whether those checks catch an advice mutated to invent a term, add a verdict
  word, write a rubric code or run long. (Until 2026-09-30 this measured explanation units and
  the fact ledger, then a summary overview; the graph now writes the advice only.)

Writes `eval/results/<timestamp>-cards-persona-<mode>.{json,md}` with a `meta` block naming the
code revision, prompt hashes and gold version.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from financial_disclosure_review.core.context import Context  # noqa: E402
from financial_disclosure_review.core.usage import current, start_run  # noqa: E402
from financial_disclosure_review.domain.ad_disclosure_check.rubric import (  # noqa: E402
    deferred_explanation_items,
)
from financial_disclosure_review.domain.evidence_cards import extract_evidence_cards  # noqa: E402
from financial_disclosure_review.domain.persona_explanation import (  # noqa: E402
    generate_persona_explanation,
)
from financial_disclosure_review.domain.persona_explanation.generate import (  # noqa: E402
    MAX_CHARS,
    advice_problems,
)
from financial_disclosure_review.evaluation.cassette import Cassette  # noqa: E402
from financial_disclosure_review.evaluation.evidence_metrics import card_metrics  # noqa: E402
from financial_disclosure_review.evaluation.run_meta import run_meta  # noqa: E402

FIXTURES = ("display_lottecard_card_loan", "display_lottecard_loca_classic")
GOLD = ROOT / "eval" / "fixtures" / "gold" / "evidence_cards.json"


def generation_mutations(
    persona: dict, sources: list[dict], db_path: str, product_type: str
) -> list[dict]:
    """Mutate an accepted advice and re-run its code checks, free. Each must be caught."""
    advice, codes = persona.get("advice") or "", persona.get("advice_codes") or []
    if not persona.get("html") or not advice:
        return []
    allowed = [i["code"] for i in deferred_explanation_items(db_path, product_type)]
    source_text = " ".join(s.get("text", "") for s in sources)
    variants = [
        ("invent_term", {"advice": advice + " 철회 기한은 37일입니다.", "advice_codes": codes}),
        ("verdict_word", {"advice": advice + " 이 광고는 위반이 아닙니다.", "advice_codes": codes}),
        ("code_in_text", {"advice": advice + " (설명16)", "advice_codes": codes}),
        ("too_long", {"advice": advice + "가" * (MAX_CHARS + 1), "advice_codes": codes}),
        ("unknown_code", {"advice": advice, "advice_codes": [*codes, "설명99"]}),
    ]
    return [
        {"mutation": name, "caught": bool(advice_problems(changed, allowed, source_text))}
        for name, changed in variants
    ]


def persona_metrics(persona: dict) -> dict:
    return {
        "status": persona.get("status"),
        "profile": (persona.get("profile") or {}).get("id"),
        "shown": bool(persona.get("html")),
        "advice_codes": persona.get("advice_codes") or [],
        "chars": len(persona.get("advice") or ""),
        "problems": persona.get("problems") or [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--model", default="gpt-5-mini")
    parser.add_argument("--max-usd", type=float, default=1.0)
    parser.add_argument("--profile", default="")
    parser.add_argument(
        "--cassette", default=str(ROOT / "eval" / "cassettes" / "agentic-gpt-5-mini.json")
    )
    args = parser.parse_args()
    mode = "record" if args.record else "replay"
    cassette = Cassette(args.cassette, mode=mode)
    start_run(max_calls=60, max_usd=args.max_usd)
    ctx = Context(model=args.model, persona_profile=args.profile)
    gold = json.loads(GOLD.read_text(encoding="utf-8"))["entries"]

    pages = {}
    for name in FIXTURES:
        fixture = json.loads((ROOT / "eval" / "fixtures" / f"{name}.json").read_text("utf-8"))
        page, classification = fixture["page"], fixture["classification"]
        fixture_gold = [g for g in gold if g["fixture"] == name]
        cards = extract_evidence_cards(page, classification, ctx, ask=cassette.ask)
        persona = generate_persona_explanation(
            cards["sources"], cards["cards"], classification, ctx, ask=cassette.ask
        )
        pages[name] = {
            "cards": {
                **card_metrics(cards["cards"], cards["sources"], fixture_gold),
                "status": cards["status"],
                "rejected": len(cards["rejected"]),
                "model_calls": cards["model_calls"],
                "sources": len(cards["sources"]),
                "kinds": sorted({c["kind"] for c in cards["cards"]}),
            },
            "persona": persona_metrics(persona),
            "generation_mutations": generation_mutations(
                persona, cards["sources"], ctx.db_path, classification.get("product_type")
            ),
            "examples": {
                "card": cards["cards"][0] if cards["cards"] else None,
                "advice": persona.get("advice") or "",
            },
        }

    saved = cassette.save()
    result = {
        "meta": run_meta("evidence_cards+persona_advice (cassette)", gold=GOLD),
        "mode": mode,
        "model": ctx.model,
        "profile": ctx.persona_profile or "(default)",
        "cassette": {**cassette.stats(), "saved": saved},
        "cost": current().summary(),
        "pages": pages,
    }
    stamp = datetime.now().strftime("%y%m%d-%H%M%S")
    out = ROOT / "eval" / "results" / f"{stamp}-cards-persona-{mode}"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1, default=str), encoding="utf-8"
    )
    meta = result["meta"]
    lines = [
        f"# evidence cards and persona advice ({mode}, {ctx.model})",
        "",
        f"meta: commit {meta['commit']}{' (dirty)' if meta['dirty'] else ''}, gold {meta['gold']}",
        "",
    ]
    for name, page in pages.items():
        lines += [f"## {name}", "", "```json"]
        lines += [
            json.dumps(
                {k: v for k, v in page.items() if k != "examples"},
                ensure_ascii=False,
                indent=1,
                default=str,
            )
        ]
        lines += ["```", ""]
    lines += [f"cassette: {result['cassette']}", f"cost: {json.dumps(result['cost'])}"]
    out.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {n: {k: v for k, v in p.items() if k != "examples"} for n, p in pages.items()},
            ensure_ascii=False,
            indent=1,
            default=str,
        )
    )
    print("cassette:", result["cassette"])
    print("cost:", json.dumps(result["cost"]))
    print("written:", out.with_suffix(".md"))


if __name__ == "__main__":
    main()
