"""Stage 4 evaluation: evidence cards, reference cases and the persona explanation on real pages.

Runs on the two real lottecard pages kept in `eval/fixtures/` (gitignored in the public repo),
with the gold set in `eval/fixtures/gold/evidence_cards.json`. Every model call goes through a
cassette, so a recorded run replays for free:

    uv run python eval/agentic_eval.py            # replay, $0 (fails on a missing recording)
    uv run python eval/agentic_eval.py --record   # calls the model for what is not recorded

Measured, separately (구현 프롬프트 Stage 4):
- evidence cards: quote resolution, gold recall, risk-gold recall;
- reference cases: expected-link recall, false links, partial-detectability notes;
- persona explanation: accepted/reverted units, fact-ledger coverage, analogies kept on risk
  cards (must be 0), and whether the ledger check catches a number or condition that a mutated
  explanation drops or changes.

The page agent loop is measured from a live review's trace, not here (it needs a browser).
Writes `eval/results/<timestamp>-agentic-<mode>.{json,md}`.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

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
from financial_disclosure_review.domain.persona_explanation.generate import (  # noqa: E402
    review_unit,
)
from financial_disclosure_review.evaluation.cassette import Cassette  # noqa: E402
from financial_disclosure_review.evaluation.evidence_metrics import card_metrics  # noqa: E402
from financial_disclosure_review.knowledge.reference import (  # noqa: E402
    default_corpus_path,
    retrieve_reference_cases,
)

FIXTURES = ("display_lottecard_card_loan", "display_lottecard_loca_classic")
GOLD = ROOT / "eval" / "fixtures" / "gold" / "evidence_cards.json"
# Cards judged to share a pattern with a corpus case (docs/agent-node-specs/reference_cases.md).
EXPECTED_LINKS = {
    "국내외 가맹점에서 최대 1% 할인": "case.crefia_ad_type_unconditional_discount",
    "모든 무이자할부 이용금액, 국세, 지방세, 도시가스비": (
        "case.fss_20241007_interest_free_benefit_exclusion"
    ),
    "추가적인 혜택(포인트 및 할인혜택 등)에는 제공조건 및 한도등이 적용됩니다.": (
        "case.fss_20241007_addon_limit_restore"
    ),
}
RISK_KINDS = ("rate_claim", "fee_claim", "warning")
MUTATIONS_PER_PAGE = 4


def _overlaps(a: str, b: str) -> bool:
    na, nb = norm(a), norm(b)
    return bool(na) and bool(nb) and (na in nb or nb in na)


def reference_metrics(refs: dict, cards: list[dict], fixture_gold: list[dict]) -> dict:
    """Expected links found and links to anything else, judged by the card quotes they cite."""
    by_id = {c["id"]: c for c in cards}
    expected = {
        q: case for q, case in EXPECTED_LINKS.items() if any(g["quote"] == q for g in fixture_gold)
    }
    found, false_links = [], []
    for link in refs.get("links") or []:
        quotes = [by_id[i]["quote"] for i in link.get("card_ids") or [] if i in by_id]
        hit = [
            q
            for q, case in expected.items()
            if case == link["case_id"] and any(_overlaps(q, quote) for quote in quotes)
        ]
        (found if hit else false_links).append(link["case_id"])
    return {
        "status": refs.get("status"),
        "candidates": len(refs.get("candidates") or []),
        "links": len(refs.get("links") or []),
        "expected": len(expected),
        "expected_found": len(set(found)),
        "false_links": false_links,
        "partial_notes": sum(1 for link in refs.get("links") or [] if link.get("page_only_note")),
        "top_candidates": [(c["case_id"], c["final"]) for c in (refs.get("candidates") or [])[:3]],
    }


def _mutate(text: str, value: str, how: str) -> str | None:
    """The explanation text with one ledger value dropped or changed; None when not applicable."""
    if value not in text:
        return None
    if how == "drop":
        return text.replace(value, "")
    digits = re.search(r"\d", value)
    if not digits:
        return None
    bumped = value[: digits.start()] + str((int(digits.group()) + 1) % 10) + value[digits.end() :]
    return text.replace(value, bumped)


def mutation_checks(persona: dict, original_text: str, model: str, ask) -> list[dict]:
    """Drop or change ledger values of accepted units and ask check_ledger to notice."""
    accepted = {u["unit_id"] for u in persona.get("units") or [] if u["status"] == "accepted"}
    explanation = visible_text(persona.get("html") or "")
    facts = [
        f
        for f in persona.get("fact_ledger") or []
        if set(f.get("unit_ids") or []) & accepted and len(f["value"]) >= 2
    ]
    picked = [f for f in facts if f["kind"] in ("number", "limit", "period")][:2]
    picked += [f for f in facts if f["kind"] in ("condition", "exception")][:2]
    rows = []
    for fact in picked[:MUTATIONS_PER_PAGE]:
        how = "change" if fact["kind"] in ("number", "limit", "period") else "drop"
        mutated = _mutate(explanation, fact["value"], how)
        if mutated is None:
            continue
        result = check_ledger(
            persona["fact_ledger"], persona["units"], original_text, mutated, model, ask
        )
        flagged = [
            r
            for r in result["fidelity"]
            if r["code"] == fact["fact_id"] or (how == "change" and r["kind"] == "추가")
        ]
        rows.append(
            {
                "fact_id": fact["fact_id"],
                "kind": fact["kind"],
                "value": fact["value"],
                "mutation": how,
                "detected": bool(flagged),
                "by": sorted({r["decided_by"] for r in flagged}),
            }
        )
    return rows


def generation_mutations(persona: dict, sources: list[dict], cards: list[dict]) -> list[dict]:
    """First safety layer: mutate accepted drafts and re-run the per-unit code review, free."""
    cards_by_id = {c["id"]: c for c in cards}
    sources_by_id = {s["source_id"]: s for s in sources}
    order = {s["source_id"]: n for n, s in enumerate(sources)}
    ledger = persona.get("fact_ledger") or []
    policy = ((persona.get("profile") or {}).get("attributes") or {}).get("analogy_policy", "none")
    rows = []
    for unit in [u for u in persona.get("units") or [] if u["status"] == "accepted"][:6]:
        facts = [f for f in ledger if unit["unit_id"] in (f.get("unit_ids") or [])]
        risky = any(cards_by_id[i]["kind"] in RISK_KINDS for i in unit["card_ids"])
        variants = []
        if facts:
            value = facts[0]["value"]
            variants.append(
                (
                    "drop_fact",
                    {
                        "exact_fact": unit["exact_fact"].replace(value, ""),
                        "explanation": unit["explanation"].replace(value, ""),
                    },
                    "reverted",
                )
            )
        variants.append(
            ("invent_number", {"explanation": unit["explanation"] + " 약 37만원"}, "reverted")
        )
        variants.append(
            ("verdict_word", {"explanation": unit["explanation"] + " 위반이 아닙니다."}, "reverted")
        )
        if risky:
            variants.append(
                ("risk_analogy", {"analogy": "은행 적금과 비슷합니다."}, "analogy_dropped")
            )
        for name, change, expect in variants:
            draft = {**unit, **change}
            reviewed = review_unit(
                unit["unit_id"], draft, cards_by_id, sources_by_id, order, ledger, policy
            )
            if expect == "reverted":
                caught = reviewed["status"] == "reverted"
            else:
                caught = not reviewed["analogy"]
            rows.append({"unit_id": unit["unit_id"], "mutation": name, "caught": caught})
    return rows


def persona_metrics(persona: dict, ledger: dict, cards: list[dict]) -> dict:
    units = persona.get("units") or []
    kinds = {c["id"]: c["kind"] for c in cards}
    risky_with_analogy = [
        u["unit_id"]
        for u in units
        if u["status"] == "accepted"
        and u.get("analogy")
        and any(kinds.get(i) in RISK_KINDS for i in u.get("card_ids") or [])
    ]
    rows = ledger.get("ledger") or []
    return {
        "status": persona.get("status"),
        "profile": (persona.get("profile") or {}).get("id"),
        "units": len(units),
        "accepted": sum(u["status"] == "accepted" for u in units),
        "reverted": sum(u["status"] == "reverted" for u in units),
        "revert_reasons": sorted(
            {p.split(":")[0] for u in units if u["status"] == "reverted" for p in u["problems"]}
        ),
        "analogies_kept": sum(1 for u in units if u["status"] == "accepted" and u.get("analogy")),
        "analogies_dropped": sum(
            1 for u in units for p in u.get("problems") or [] if p.startswith("analogy_dropped")
        ),
        "risk_analogies_kept": risky_with_analogy,
        "ledger_facts": len(rows),
        "ledger_preserved": sum(r["verdict"] == "보존" for r in rows),
        "ledger_by_code": sum(r["decided_by"] == "code" for r in rows),
        "fidelity_rows": len(ledger.get("fidelity") or []),
        "fidelity_failing": sum(
            1 for r in ledger.get("fidelity") or [] if not r.get("informational")
        ),
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
        refs = retrieve_reference_cases(
            cards["cards"], classification, ctx.db_path, corpus_path=default_corpus_path()
        )
        persona = generate_persona_explanation(
            cards["sources"], cards["cards"], classification, ctx, ask=cassette.ask
        )
        original_text = visible_text(page["html"])
        ledger = check_ledger(
            persona["fact_ledger"],
            persona["units"],
            original_text,
            visible_text(persona["html"]),
            ctx.model,
            cassette.ask,
        )
        mutations = mutation_checks(persona, original_text, ctx.model, cassette.ask)
        pages[name] = {
            "cards": {
                **card_metrics(cards["cards"], cards["sources"], fixture_gold),
                "status": cards["status"],
                "rejected": len(cards["rejected"]),
                "model_calls": cards["model_calls"],
                "sources": len(cards["sources"]),
                "kinds": sorted({c["kind"] for c in cards["cards"]}),
            },
            "references": reference_metrics(refs, cards["cards"], fixture_gold),
            "persona": persona_metrics(persona, ledger, cards["cards"]),
            "mutations": mutations,
            "generation_mutations": generation_mutations(persona, cards["sources"], cards["cards"]),
            "linked_cards": [
                {
                    "case_id": link["case_id"],
                    "cards": [
                        c["quote"][:80] for c in cards["cards"] if c["id"] in link["card_ids"]
                    ],
                    "page_only_note": link["page_only_note"],
                }
                for link in refs.get("links") or []
            ],
            "examples": {
                "card": cards["cards"][0] if cards["cards"] else None,
                "unit": next((u for u in persona["units"] if u["status"] == "accepted"), None),
                "ledger": (ledger["ledger"] or [None])[0],
                "fidelity": (ledger["fidelity"] or [None])[0],
                "link": (refs.get("links") or [None])[0],
            },
        }

    saved = cassette.save()
    result = {
        "mode": mode,
        "model": ctx.model,
        "profile": ctx.persona_profile or "(default)",
        "cassette": {**cassette.stats(), "saved": saved},
        "cost": current().summary(),
        "pages": pages,
    }
    stamp = datetime.now().strftime("%y%m%d-%H%M%S")
    out = ROOT / "eval" / "results" / f"{stamp}-agentic-{mode}"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1, default=str), encoding="utf-8"
    )
    lines = [f"# agentic evaluation ({mode}, {ctx.model})", ""]
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
