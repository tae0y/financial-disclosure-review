"""The fact ledger: every number, period, limit, target, condition, exception and penalty of the
evidence cards, as literal source strings an explanation has to keep. Pure code, deterministic."""

import re
from collections.abc import Mapping, Sequence
from typing import Any

from ..plain_language.contract import strip_ws

PERIOD_UNIT_RE = re.compile(r"^(?:개월|개년|년|일|주|회차|시간|영업일)")
LIMIT_MARKERS = ("최대", "한도")
# Whitespace-free characters read around the number: "월 최대 2만원", "할인한도 월 2만원" and
# "2만원 한도" are limits, while the 30만원 of "30만원 이상 시 월 최대 2만원" is not.
LIMIT_WINDOW_BEFORE = 4
LIMIT_WINDOW_AFTER = 3


def number_kind(value: str, quote: str) -> str:
    """period, limit or number for one of a card's number strings, read off the quote around it."""
    compact_value, compact_quote = strip_ws(value), strip_ws(quote)
    digits = re.search(r"\d[\d,.]*", compact_value)
    unit = compact_value[digits.end() :] if digits else ""
    start = compact_quote.find(compact_value) if compact_value else -1
    after = compact_quote[start + len(compact_value) :] if start >= 0 else ""
    if PERIOD_UNIT_RE.match(unit) or (not unit and PERIOD_UNIT_RE.match(after)):
        return "period"
    if start >= 0:
        before = compact_quote[max(0, start - LIMIT_WINDOW_BEFORE) : start]
        if (
            any(marker in before for marker in LIMIT_MARKERS)
            or "한도" in after[:LIMIT_WINDOW_AFTER]
        ):
            return "limit"
    return "number"


def _target_value(card: Mapping[str, Any]) -> str:
    """An eligibility card's claim when it is literally in the quote, else the quote itself."""
    claim, quote = card.get("claim") or "", card.get("quote") or ""
    return claim if strip_ws(claim) and strip_ws(claim) in strip_ws(quote) else quote


def card_facts(card: Mapping[str, Any]) -> list[tuple[str, str]]:
    """(kind, value) pairs of one card, in a fixed order, without repeats."""
    quote = card.get("quote") or ""
    facts = [(number_kind(str(n), quote), str(n)) for n in card.get("numbers") or []]
    facts += [("condition", q) for q in card.get("qualifiers") or []]
    facts += [("exception", e) for e in card.get("exceptions") or []]
    if card.get("kind") == "eligibility":
        facts.append(("target", _target_value(card)))
    if card.get("kind") == "warning" and quote:
        facts.append(("penalty", quote))
    seen: set[tuple[str, str]] = set()
    unique = []
    for kind, value in facts:
        key = (kind, strip_ws(value))
        if key[1] and key not in seen:
            seen.add(key)
            unique.append((kind, value))
    return unique


def build_fact_ledger(cards: Sequence[Mapping[str, Any]]) -> list[dict]:
    """[{fact_id, card_id, source_id, kind, value}, ...] in card order; fact ids are f1, f2, …"""
    ledger = []
    for card in cards:
        for kind, value in card_facts(card):
            ledger.append(
                {
                    "fact_id": f"f{len(ledger) + 1}",
                    "card_id": card.get("id", ""),
                    "source_id": card.get("source_id", ""),
                    "kind": kind,
                    "value": value,
                }
            )
    return ledger
