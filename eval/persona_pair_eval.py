"""Two real dataset readers, same page: do both overviews pass, and do they cite the same facts?

For each of the two real lottecard pages, the round-1 evidence cards are summarised for two
readers chosen from the pinned Nemotron-Personas-Korea dataset by explicit attributes (no model
call to choose): a low-familiarity older reader and a finance-familiar reader. Both overviews must
pass their code checks; wording and length may differ with the reader. The Jaccard of the numbers
each overview cites shows how far the facts a reader is told depend on who the reader is (backlog
C4). Until 2026-09-30 this compared fact-ledger verdicts of explanation units.

    uv run python eval/persona_pair_eval.py            # replay, $0
    uv run python eval/persona_pair_eval.py --record   # records the persona calls once

Needs the dataset under data/personas (`python -m financial_disclosure_review fetch-personas`).
Writes `eval/results/<timestamp>-persona-pair-<mode>.{json,md}`.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from cards_persona_eval import FIXTURES, persona_metrics  # noqa: E402

from financial_disclosure_review.core.context import Context, default_data_dir  # noqa: E402
from financial_disclosure_review.core.usage import current, start_run  # noqa: E402
from financial_disclosure_review.domain.evidence_cards import extract_evidence_cards  # noqa: E402
from financial_disclosure_review.domain.persona_explanation import (  # noqa: E402
    choose_profile,
    generate_persona_explanation,
)
from financial_disclosure_review.domain.plain_language.contract import number_set  # noqa: E402
from financial_disclosure_review.evaluation.cassette import Cassette  # noqa: E402
from financial_disclosure_review.evaluation.run_meta import run_meta  # noqa: E402

READERS = {
    "older_low_familiarity": {"age_min": 70, "education_level": ["초등학교"]},
    "finance_familiar": {"age_min": 40, "age_max": 49, "occupation_contains": ["은행", "보험"]},
}


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--model", default="gpt-5-mini")
    parser.add_argument("--max-usd", type=float, default=0.5)
    parser.add_argument(
        "--cassette", default=str(ROOT / "eval" / "cassettes" / "agentic-gpt-5-mini.json")
    )
    args = parser.parse_args()
    mode = "record" if args.record else "replay"
    cassette = Cassette(args.cassette, mode=mode)
    start_run(max_calls=30, max_usd=args.max_usd)

    result: dict = {}
    for name in FIXTURES:
        fixture = json.loads((ROOT / "eval" / "fixtures" / f"{name}.json").read_text("utf-8"))
        page, classification = fixture["page"], fixture["classification"]
        base_ctx = Context(model=args.model)
        cards = extract_evidence_cards(page, classification, base_ctx, ask=cassette.ask)
        rows, numbers = {}, {}
        for reader, attributes in READERS.items():
            ctx = Context(model=args.model, persona_attributes=attributes)
            chosen = choose_profile(
                ctx,
                product_type=classification.get("product_type"),
                cards=cards["cards"],
                data_dir=default_data_dir(),
                rubric_dir=ctx.rubric_dir,
            )
            persona = generate_persona_explanation(
                cards["sources"],
                cards["cards"],
                classification,
                ctx,
                ask=cassette.ask,
                profile=chosen["profile"],
            )
            numbers[reader] = number_set(" ".join(persona.get("overview") or []))
            metrics = persona_metrics(persona)
            rows[reader] = {
                "profile": chosen["profile"]["id"],
                "reader": (chosen["profile"].get("attributes") or {}).get("reader", "")[:120],
                "familiarity": (chosen["profile"].get("attributes") or {}).get(
                    "financial_familiarity"
                ),
                "decided_by": chosen["selection"]["decided_by"],
                **{k: metrics[k] for k in ("shown", "paragraphs", "chars", "problems")},
                "numbers": sorted(numbers[reader]),
                "sample": (persona.get("overview") or [""])[0][:160],
            }
        a, b = (numbers[r] for r in READERS)
        result[name] = {
            "readers": rows,
            "both_shown": all(row["shown"] for row in rows.values()),
            "number_jaccard": round(len(a & b) / len(a | b), 3) if a | b else 1.0,
            "numbers_only_in": {
                r: sorted(numbers[r] - numbers[o])
                for r, o in (
                    (list(READERS)[0], list(READERS)[1]),
                    (list(READERS)[1], list(READERS)[0]),
                )
            },
        }

    saved = cassette.save()
    out = {
        "meta": run_meta("persona overview reader pair (cassette)"),
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
    (folder / f"{stamp}-persona-pair-{mode}.json").write_text(text, encoding="utf-8")
    (folder / f"{stamp}-persona-pair-{mode}.md").write_text(
        f"# persona pair ({mode}, {args.model})\n\n```json\n{text}\n```\n", encoding="utf-8"
    )
    print(text)


if __name__ == "__main__":
    main()
