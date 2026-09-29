"""Repeat stability of evidence-card extraction and persona generation (backlog F2).

The same two real lottecard pages as `eval/cards_persona_eval.py`, three rounds each. Round 1
reuses the unsalted recordings of the agentic cassette; rounds 2 and 3 are salted, so they are
separate model answers to the same input. Persona generation runs on the round-1 cards in every
round, so its variance is the generator's own, not inherited from extraction.

    uv run python eval/agentic_stability.py            # replay, $0
    uv run python eval/agentic_stability.py --record   # records rounds 2-3 once

Measured:
- cards: count, gold recall and the pairwise Jaccard of (kind, quote) sets between rounds;
- persona: accepted units, and whether the code-decided fact ledger (value present in its unit)
  gives the same verdict per fact in every round; risk-card analogies kept (must be 0).

Writes `eval/results/<timestamp>-agentic-stability-<mode>.{json,md}`.
"""

import argparse
import json
import sys
from datetime import datetime
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from cards_persona_eval import FIXTURES, GOLD, persona_metrics  # noqa: E402

from financial_disclosure_review.core.context import Context  # noqa: E402
from financial_disclosure_review.core.text import norm, visible_text  # noqa: E402
from financial_disclosure_review.core.usage import current, start_run  # noqa: E402
from financial_disclosure_review.domain.evidence_cards import extract_evidence_cards  # noqa: E402
from financial_disclosure_review.domain.explanation_duty_check.ledger import (  # noqa: E402
    check_ledger,
)
from financial_disclosure_review.domain.persona_explanation import (  # noqa: E402
    generate_persona_explanation,
)
from financial_disclosure_review.evaluation.cassette import Cassette  # noqa: E402
from financial_disclosure_review.evaluation.evidence_metrics import card_metrics  # noqa: E402
from financial_disclosure_review.evaluation.run_meta import run_meta  # noqa: E402

ROUNDS = ("", "round-2", "round-3")


def salted(cassette: Cassette, salt: str):
    def ask(model, schema, task, effort="low", **data):
        return cassette.ask_salted(salt, model, schema, task, effort, **data)

    return ask


def jaccard(a: set, b: set) -> float:
    return round(len(a & b) / len(a | b), 3) if a | b else 1.0


def card_key(card: dict) -> tuple[str, str]:
    return card["kind"], norm(card["quote"])


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--model", default="gpt-5-mini")
    parser.add_argument("--max-usd", type=float, default=1.0)
    parser.add_argument(
        "--cassette", default=str(ROOT / "eval" / "cassettes" / "agentic-gpt-5-mini.json")
    )
    args = parser.parse_args()
    mode = "record" if args.record else "replay"
    cassette = Cassette(args.cassette, mode=mode)
    start_run(max_calls=60, max_usd=args.max_usd)
    ctx = Context(model=args.model)
    gold = json.loads(GOLD.read_text(encoding="utf-8"))["entries"]

    result: dict = {}
    for name in FIXTURES:
        fixture = json.loads((ROOT / "eval" / "fixtures" / f"{name}.json").read_text("utf-8"))
        page, classification = fixture["page"], fixture["classification"]
        fixture_gold = [g for g in gold if g["fixture"] == name]
        original_text = visible_text(page["html"])
        rounds_cards, cards_rows, persona_rows, ledgers = [], [], [], []
        for salt in ROUNDS:
            ask = salted(cassette, salt)
            cards = extract_evidence_cards(page, classification, ctx, ask=ask)
            rounds_cards.append(cards)
            metrics = card_metrics(cards["cards"], cards["sources"], fixture_gold)
            cards_rows.append({"cards": len(cards["cards"]), "gold_recall": metrics["gold_recall"]})
        base = rounds_cards[0]
        for salt in ROUNDS:
            ask = salted(cassette, salt)
            persona = generate_persona_explanation(
                base["sources"], base["cards"], classification, ctx, ask=ask
            )
            ledger = check_ledger(
                persona["fact_ledger"],
                persona["units"],
                original_text,
                visible_text(persona["html"]),
                ctx.model,
                ask,
            )
            ledgers.append({r["fact_id"]: r["in_explanation"] for r in ledger["ledger"]})
            m = persona_metrics(persona, ledger, base["cards"])
            persona_rows.append(
                {
                    k: m[k]
                    for k in (
                        "accepted",
                        "reverted",
                        "ledger_facts",
                        "ledger_by_code",
                        "risk_analogies_kept",
                    )
                }
            )
        sets = [{card_key(c) for c in r["cards"]} for r in rounds_cards]
        facts = sorted(set().union(*ledgers))
        stable = [f for f in facts if len({lg.get(f) for lg in ledgers}) == 1]
        result[name] = {
            "cards": cards_rows,
            "card_jaccard": {
                f"{i + 1}-{j + 1}": jaccard(sets[i], sets[j])
                for i, j in combinations(range(len(sets)), 2)
            },
            "persona": persona_rows,
            "ledger_code_verdict_stable": f"{len(stable)}/{len(facts)}",
            "ledger_unstable_facts": [f for f in facts if f not in stable],
        }

    saved = cassette.save()
    out = {
        "meta": run_meta("evidence_cards+persona_explanation stability (cassette)", gold=GOLD),
        "mode": mode,
        "model": args.model,
        "pages": result,
        "cassette": {**cassette.stats(), "saved": saved},
        "cost": current().summary(),
    }
    stamp = datetime.now().strftime("%y%m%d-%H%M%S")
    folder = ROOT / "eval" / "results"
    folder.mkdir(parents=True, exist_ok=True)
    text = json.dumps(out, ensure_ascii=False, indent=1)
    (folder / f"{stamp}-agentic-stability-{mode}.json").write_text(text, encoding="utf-8")
    (folder / f"{stamp}-agentic-stability-{mode}.md").write_text(
        f"# agentic stability ({mode}, {args.model})\n\n```json\n{text}\n```\n", encoding="utf-8"
    )
    print(text)


if __name__ == "__main__":
    main()
