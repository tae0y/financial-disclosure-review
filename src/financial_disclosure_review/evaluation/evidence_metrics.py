"""Evidence-card quality: quote grounding against sources, recall against a curated gold set."""

from typing import Any

from ..core.text import locate_quote, norm
from .metrics import rate


def _covers(a: str, b: str) -> bool:
    """True if the normalized text of a and b overlap as a substring, in either direction."""
    na, nb = norm(a), norm(b)
    return bool(na) and bool(nb) and (na in nb or nb in na)


def card_metrics(cards: list[dict], sources: list[dict], gold: list[dict]) -> dict[str, Any]:
    """quote_resolution: share of cards whose quote is locatable in its own source.
    gold_recall: share of gold quotes matched by some card quote (either substring direction).
    risk_gold_recall: the same, restricted to gold entries marked risk=true."""
    sources_by_id = {s["source_id"]: s for s in sources}

    def resolved(card: dict) -> bool:
        source = sources_by_id.get(card.get("source_id"))
        if source is None:
            return False
        return locate_quote(source["text"], card.get("quote", "")) is not None

    resolved_cards = [c for c in cards if resolved(c)]

    def covered(entry: dict) -> bool:
        return any(_covers(entry["quote"], c["quote"]) for c in cards)

    covered_gold = [g for g in gold if covered(g)]
    risky_gold = [g for g in gold if g.get("risk")]
    covered_risky = [g for g in risky_gold if covered(g)]

    return {
        "cards": len(cards),
        "quote_resolution": rate(len(resolved_cards), len(cards)),
        "gold_entries": len(gold),
        "gold_recall": rate(len(covered_gold), len(gold)),
        "risk_gold_entries": len(risky_gold),
        "risk_gold_recall": rate(len(covered_risky), len(risky_gold)),
        "unresolved_card_ids": [c["id"] for c in cards if c not in resolved_cards],
        "missed_gold_quotes": [g["quote"] for g in gold if not covered(g)],
    }
