"""Entry point of evidence_cards: split sources, draft cards once, keep only what checks out."""

import re
from collections.abc import Mapping
from typing import Any

from ...core.context import Context
from ...core.text import norm
from ...llm.client import ask, call_ask
from .blocks import page_sources
from .contract import validate_candidate
from .prompts import EVIDENCE_CARD_TASK
from .schema import EvidenceCardDrafts

# One model call sees at most this many sources (the real pages measured have 93 and 136); a page
# with more distinct lines than this sends only the first SOURCE_CAP (in page order) to the model,
# but every source still appears in the returned `sources` list and in coverage_gaps matching.
SOURCE_CAP = 300

BENEFIT_KINDS = ("benefit_claim", "rate_claim")
_ITEM_PROBLEM = re.compile(r"^item(\d+):\s*(.*)$")


def _empty(status: str, reason: str, sources: list[dict] | None = None) -> dict:
    return {
        "status": status,
        "reason": reason,
        "sources": sources or [],
        "cards": [],
        "rejected": [],
        "coverage_gaps": [],
        "model_calls": 0,
    }


def _claim_without_condition(cards: list[dict]) -> list[str]:
    return [
        c["id"]
        for c in cards
        if c["kind"] in BENEFIT_KINDS and not c["qualifiers"] and not c["exceptions"]
    ]


def _coverage_gaps(page: Mapping[str, Any], cards: list[dict]) -> list[dict]:
    gaps: list[dict] = []
    for gap in (page.get("coverage") or {}).get("gaps") or []:
        if gap.get("status") not in ("open", "unresolved"):
            continue
        kind = gap.get("kind")
        if kind == "hidden_text":
            card_ids = [c["id"] for c in cards if c["visibility"] in ("hidden", "unresolved")]
        elif kind == "benefit_without_condition":
            card_ids = _claim_without_condition(cards)
        else:
            card_ids = []
        gaps.append({**gap, "card_ids": card_ids})

    claim_ids = _claim_without_condition(cards)
    if claim_ids:
        gaps.append(
            {"kind": "claim_without_visible_condition", "card_ids": claim_ids, "status": "open"}
        )
    return gaps


def extract_evidence_cards(
    page: Mapping[str, Any], classification: Mapping[str, Any], ctx: Context, ask=ask
) -> dict:
    """한 페이지의 증거 카드 추출. EvidenceCards의 모든 필드를 돌려준다."""
    html = page.get("html")
    if not html:
        return _empty("판정 불가", "입력 없음: html이 비어 있음")
    product_type = classification.get("product_type")
    if not product_type:
        return _empty("판정 불가", "classification에 product_type이 없음")

    sources = page_sources(page)
    if not sources:
        return _empty("카드 없음", "원문에서 인용할 수 있는 소스가 없음")

    capped = sources[:SOURCE_CAP]
    sources_by_id = {s["source_id"]: s for s in capped}
    source_order = {s["source_id"]: i for i, s in enumerate(capped)}

    calls = {"n": 0}

    def counted_ask(*args, **kwargs):
        calls["n"] += 1
        return ask(*args, **kwargs)

    rejected: list[dict] = []

    def check(answer: dict) -> list[str]:
        problems = []
        for i, item in enumerate(answer["items"]):
            problems += [f"item{i}: {p}" for p in validate_candidate(item, sources_by_id)]
        return problems

    def salvage(answer: dict, problems: list[str]) -> dict:
        """검증에 걸린 후보만 rejected로 보내고, 통과한 후보만 남긴다."""
        by_index: dict[int, list[str]] = {}
        for p in problems:
            m = _ITEM_PROBLEM.match(p)
            if m:
                by_index.setdefault(int(m.group(1)), []).append(m.group(2))
        kept = []
        for i, item in enumerate(answer["items"]):
            reasons = by_index.get(i)
            if reasons:
                rejected.append({"candidate": item, "reason": "; ".join(reasons)})
            else:
                kept.append(item)
        return {"items": kept}

    candidate = call_ask(
        counted_ask,
        ctx.model,
        EvidenceCardDrafts,
        EVIDENCE_CARD_TASK,
        check,
        "medium",
        salvage,
        sources=[{"source_id": s["source_id"], "text": s["text"]} for s in capped],
        product_type=product_type,
    )

    def sort_key(pair: tuple[int, dict]) -> tuple[int, int]:
        index, item = pair
        return source_order[item["source_id"]], index

    ordered = sorted(enumerate(candidate["items"]), key=sort_key)
    seen: set[tuple[str, str]] = set()
    cards: list[dict] = []
    for _, item in ordered:
        key = (norm(item["quote"]), item["kind"])
        if key in seen:
            continue
        seen.add(key)
        cards.append(
            {
                "id": f"c{len(cards) + 1}",
                "kind": item["kind"],
                "subject": item["subject"],
                "claim": item["claim"],
                "qualifiers": list(item.get("qualifiers") or []),
                "exceptions": list(item.get("exceptions") or []),
                "numbers": list(item.get("numbers") or []),
                "quote": item["quote"],
                "source_id": item["source_id"],
                "visibility": sources_by_id[item["source_id"]]["visibility"],
            }
        )

    status = "완료" if cards else "카드 없음"
    reason = "" if cards else "코드 검증을 통과한 카드 후보가 없음"
    return {
        "status": status,
        "reason": reason,
        "sources": sources,
        "cards": cards,
        "rejected": rejected,
        "coverage_gaps": _coverage_gaps(page, cards),
        "model_calls": calls["n"],
    }
