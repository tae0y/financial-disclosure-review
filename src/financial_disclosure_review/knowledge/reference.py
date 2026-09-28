"""Deterministic reference-case retrieval (Stage 2, part B).

Given the evidence cards a page produced and the page's classification, finds the sanction/
dispute cases that plausibly describe the same pattern, using only in-memory scoring over the
cases the case DB already has — no DB rebuild, no required model or embedding call.

Ranking, per the design record (`Stage 0 설계 기록.md` §2.3, §8-13): BM25 slot overlap is the
default and only required signal. The risk-kind match (`assets/case_risk_kinds.yaml`) is a
ranking *boost*, never a filter. `classification["product_type"]` is the only hard filter
(via `knowledge.cases.load_cases`). Embedding rerank (`rerank=True`) is opt-in, paid, and only
reorders candidates that already cleared the threshold — it never adds a candidate.

Threshold: `DEFAULT_THRESHOLD` was set on real page cards, not on the synthetic paraphrase set
in `tests/fixtures/reference_links.synthetic.json` (which only checks that a case paraphrase finds
its own case). See `docs/agent-node-specs/reference_cases.md` §Threshold for the measurements.
"""

import math
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

from ..core.context import default_rubric_dir
from ..core.text import locate_quote, norm
from .build_cases import CASE_CORPUS_FILE, case_schema_problems
from .cases import load_cases
from .search import search as vector_search

RISK_KINDS = ("rate_fee", "benefit_condition", "warning_penalty")

# Fixed card-kind -> risk-kind mapping (design record §2.3). Every `kind` in the input contract
# maps to exactly one risk kind.
CARD_KIND_RISK_KIND: dict[str, str] = {
    "rate_claim": "rate_fee",
    "fee_claim": "rate_fee",
    "benefit_claim": "benefit_condition",
    "eligibility": "benefit_condition",
    "condition": "benefit_condition",
    "exception": "benefit_condition",
    "warning": "warning_penalty",
    "footnote": "warning_penalty",
}

SLOTS = ("claim", "qualifier", "exception", "number")
SLOT_WEIGHTS: dict[str, float] = {"claim": 0.4, "qualifier": 0.25, "exception": 0.15, "number": 0.2}
RISK_KIND_BOOST = 1.0
PARTIAL_DETECTABILITY = ("partial", "review_required", "out_of_scope")

# Set on 2026-09-29 against 25 real-page gold cards (two lottecard pages, 3 expected links):
# threshold 4 -> recall 3/3 with 18 false links, 6 -> 1/3 with 3, 8 -> 0/3 with 1, 10 -> 0/3
# with 0. Lexical overlap with 19 short case summaries does not separate true links from shared
# financial vocabulary, so the default favours no link over a wrong one ("연결이 약하면 연결하지
# 않는다"). Pass a lower `threshold` explicitly to inspect weaker candidates.
DEFAULT_THRESHOLD = 10.0

RISK_KINDS_FILE = "case_risk_kinds.yaml"


def default_risk_kinds_path() -> str:
    """Where the curated risk-kind file lives by default, next to the case corpus."""
    return str(Path(default_rubric_dir()) / RISK_KINDS_FILE)


def default_corpus_path() -> str:
    """The checked-in case corpus the DB is built from; read directly when the DB has no cases."""
    return str(Path(default_rubric_dir()) / CASE_CORPUS_FILE)


def _corpus_cases(corpus_path: str | Path, product_types: tuple[str, ...]) -> list[dict]:
    """Cases straight from the corpus yaml, validated like `build-cases` does, no embedding.

    BM25 needs only the case text, so a DB whose case tables were never built (building them
    embeds every case, a paid step) does not have to block reference retrieval.
    """
    path = Path(corpus_path)
    if not path.exists():
        raise FileNotFoundError(f"case corpus {path} does not exist")
    items = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("items") or []
    problems = case_schema_problems(items)
    if problems:
        raise RuntimeError(f"case corpus {path.name} is invalid: {problems[:3]}")
    return [
        {**item, "text": item["text"].strip()}
        for item in items
        if not product_types or set(item["product_types"]) & set(product_types)
    ]


def _load_cases(
    db_path: str | Path, corpus_path: str | Path | None, product_types: tuple[str, ...]
) -> tuple[list[dict], str]:
    """Cases from the DB, else from the corpus yaml; the second value names the source used."""
    try:
        return load_cases(db_path, product_types=product_types), "db"
    except (FileNotFoundError, RuntimeError) as db_error:
        if corpus_path is None:
            raise
        try:
            return _corpus_cases(corpus_path, product_types), f"corpus:{Path(corpus_path).name}"
        except (FileNotFoundError, RuntimeError) as corpus_error:
            raise RuntimeError(f"{db_error}; {corpus_error}") from corpus_error


def _load_risk_kinds(path: str | Path) -> dict[str, dict[str, Any]]:
    data = yaml.safe_load(Path(path).read_text()) or {}
    cases = data.get("cases")
    return cases if isinstance(cases, dict) else {}


NUMBER_RE = re.compile(r"\d[\d,.]*\s*(?:만원|억원|원|%|개월|일|년|배|포인트|점)?")


def _number_tokens(text: str) -> list[str]:
    """Number-ish substrings ("30만원", "16.9%") kept whole, not decomposed into bigrams."""
    return [t.strip() for t in NUMBER_RE.findall(text or "") if any(c.isdigit() for c in t)]


def _bigrams(text: str) -> list[str]:
    """Character bigrams of the normalized (whitespace-collapsed, lowercased) text."""
    compact = re.sub(r"\s+", "", norm(text))
    if len(compact) < 2:
        return [compact] if compact else []
    return [compact[i : i + 2] for i in range(len(compact) - 1)]


def _tokens(text: str) -> list[str]:
    """Korean-friendly BM25 tokens: character bigrams plus whole number tokens."""
    return _bigrams(text) + _number_tokens(text)


class _BM25:
    """Okapi BM25 over a small, in-memory set of case documents. No index is persisted."""

    def __init__(self, docs: Mapping[str, list[str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.docs = docs
        self.doc_len = {doc_id: len(toks) for doc_id, toks in docs.items()}
        self.avgdl = (sum(self.doc_len.values()) / len(docs)) if docs else 0.0
        self.df: dict[str, int] = {}
        for toks in docs.values():
            for term in set(toks):
                self.df[term] = self.df.get(term, 0) + 1
        self.n = len(docs)

    def _idf(self, term: str) -> float:
        n_t = self.df.get(term, 0)
        return math.log((self.n - n_t + 0.5) / (n_t + 0.5) + 1)

    def score(self, doc_id: str, query_tokens: Sequence[str]) -> float:
        if not query_tokens or doc_id not in self.docs:
            return 0.0
        toks = self.docs[doc_id]
        dl = self.doc_len[doc_id]
        if not toks or not dl:
            return 0.0
        freq: dict[str, int] = {}
        for t in toks:
            freq[t] = freq.get(t, 0) + 1
        total = 0.0
        for term in set(query_tokens):
            f = freq.get(term, 0)
            if f == 0:
                continue
            denom = f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
            total += self._idf(term) * (f * (self.k1 + 1)) / denom
        return total


def _case_doc(case: Mapping[str, Any]) -> str:
    return " ".join([case.get("issue", ""), case.get("mvp_signal", ""), case.get("text", "")])


def _slot_text(card: Mapping[str, Any], slot: str) -> str:
    if slot == "claim":
        return str(card.get("claim") or "")
    if slot == "qualifier":
        return " ".join(card.get("qualifiers") or [])
    if slot == "exception":
        return " ".join(card.get("exceptions") or [])
    return " ".join(card.get("numbers") or [])


def _card_query_text(card: Mapping[str, Any]) -> str:
    return " ".join(filter(None, (_slot_text(card, slot) for slot in SLOTS)))


def _card_risk_kind(card: Mapping[str, Any]) -> str | None:
    return CARD_KIND_RISK_KIND.get(str(card.get("kind") or ""))


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?다음])\s*\n+|\n{2,}|(?<=[.!?])\s+", (text or "").strip())
    return [p.strip() for p in parts if p.strip()]


def _best_case_quote(case_text: str, card: Mapping[str, Any]) -> str:
    """The sentence of `case_text` with the most bigram overlap with the card's slot text."""
    sentences = _sentences(case_text)
    if not sentences:
        return ""
    query = set(_bigrams(_card_query_text(card)))
    if not query:
        return ""
    best, best_overlap = "", 0
    for sentence in sentences:
        overlap = len(query & set(_bigrams(sentence)))
        if overlap > best_overlap:
            best, best_overlap = sentence, overlap
    if best and locate_quote(case_text, best) is not None:
        return best
    return ""


def _same_pattern(card: Mapping[str, Any], case: Mapping[str, Any]) -> str:
    qualifiers = ", ".join(card.get("qualifiers") or []) or "명시된 조건 없음"
    return (
        f"페이지 주장 '{card.get('claim', '')}'(조건: {qualifiers})이"
        f" 사례 신호 '{case.get('mvp_signal', '')}'와 같은 패턴입니다."
    )


def _material_difference(case: Mapping[str, Any], slot_scores: Mapping[str, float]) -> list[str]:
    diffs: list[str] = []
    if case.get("product_basis") == "유추":
        diffs.append(
            "product_basis 유추 (제재 대상이 이 상품유형이 아니라 같은 광고유형의 다른 업권)"
        )
    if case.get("record_type") != "위반사례":
        diffs.append(f"record_type {case.get('record_type')} (제재로 확정된 위반사례가 아님)")
    subtype = case.get("product_subtype")
    if subtype:
        diffs.append(f"사례 상품: {subtype} (페이지 상품과 정확히 같은 상품인지 확인 필요)")
    for slot in ("qualifier", "exception", "number"):
        if slot_scores.get(slot, 0.0) <= 0:
            diffs.append(f"{slot} 슬롯: 사례에 대응하는 카드 근거 없음")
    return diffs


def _build_link(
    case: Mapping[str, Any],
    entry: Mapping[str, Any],
    best_card: Mapping[str, Any],
    text_verified: bool,
) -> dict[str, Any]:
    detectability = case.get("page_only_detectability", "")
    if text_verified:
        case_quote = _best_case_quote(case.get("text", ""), best_card)
        case_quote_note = ""
    else:
        case_quote = ""
        case_quote_note = "원문 재확인 필요"
    return {
        "case_id": case["case_id"],
        "card_ids": list(entry["card_ids"]),
        "page_quote": best_card.get("quote", ""),
        "case_quote": case_quote,
        "case_quote_note": case_quote_note,
        "same_pattern": _same_pattern(best_card, case),
        "material_difference": _material_difference(case, entry["slots"]),
        "page_only_detectability": detectability,
        "page_only_note": "페이지 단독 판단 불가" if detectability in PARTIAL_DETECTABILITY else "",
        "official_url": case.get("official_primary_url", ""),
    }


def retrieve_reference_cases(
    cards: Sequence[Mapping[str, Any]],
    classification: Mapping[str, Any],
    db_path: str | Path,
    *,
    risk_kinds_path: str | Path | None = None,
    corpus_path: str | Path | None = None,
    embed=None,
    rerank: bool = False,
    threshold: float | None = None,
) -> dict[str, Any]:
    """`{status, reason, method, candidates, links}` for one page's evidence cards.

    `status`: 건너뜀 (no cards, no DB touched) | 판정 불가 (DB/risk-kind file missing or
    unbuilt) | 해당 사례 없음 (product type has no cases, or nothing cleared the threshold) |
    완료.
    """
    threshold = DEFAULT_THRESHOLD if threshold is None else threshold
    method: dict[str, Any] = {
        "candidate": "product_type hard filter (knowledge.cases.load_cases)",
        "score": "BM25 slot overlap (claim/qualifier/exception/number) + risk_kind boost",
        "rerank": "embedding cosine via case_vectors (reorder only)" if rerank else "off",
        "threshold": threshold,
        "threshold_source": "real-page gold, 2026-09-29 (docs/agent-node-specs/reference_cases.md)",
    }
    if not cards:
        return {
            "status": "건너뜀",
            "reason": "카드가 없어 사례 검색을 실행하지 않음",
            "method": method,
            "candidates": [],
            "links": [],
        }

    product_type = classification.get("product_type") or ""
    product_types = (product_type,) if product_type else ()
    try:
        cases, source = _load_cases(db_path, corpus_path, product_types)
        method["cases_from"] = source
    except (FileNotFoundError, RuntimeError) as error:
        return {
            "status": "판정 불가",
            "reason": str(error),
            "method": method,
            "candidates": [],
            "links": [],
        }

    risk_path = risk_kinds_path or default_risk_kinds_path()
    try:
        risk_map = _load_risk_kinds(risk_path)
    except FileNotFoundError as error:
        return {
            "status": "판정 불가",
            "reason": f"case_risk_kinds.yaml을 찾을 수 없음: {error}",
            "method": method,
            "candidates": [],
            "links": [],
        }

    if not cases:
        return {
            "status": "해당 사례 없음",
            "reason": f"{product_type!r}에 해당하는 사례가 없음",
            "method": method,
            "candidates": [],
            "links": [],
        }

    cases_by_id = {case["case_id"]: case for case in cases}
    docs = {cid: _tokens(_case_doc(case)) for cid, case in cases_by_id.items()}
    bm25 = _BM25(docs)

    # A case scores as its best single card, never a sum over cards: a long page with many cards
    # must not push every case over the threshold by volume alone. `card_ids` lists the cards
    # that clear the threshold on their own.
    per_case: dict[str, dict[str, Any]] = {}
    best_card_by_case: dict[str, Mapping[str, Any]] = {}

    for card in cards:
        card_id = card.get("id")
        card_risk = _card_risk_kind(card)
        for cid in cases_by_id:
            case_risk_kinds = list((risk_map.get(cid) or {}).get("risk_kinds") or [])
            slot_scores = {slot: bm25.score(cid, _tokens(_slot_text(card, slot))) for slot in SLOTS}
            weighted = sum(SLOT_WEIGHTS[slot] * value for slot, value in slot_scores.items())
            if weighted <= 0:
                continue  # the boost alone never makes a candidate
            boost = RISK_KIND_BOOST if (card_risk and card_risk in case_risk_kinds) else 0.0
            score = weighted + boost
            entry = per_case.setdefault(
                cid,
                {
                    "case_id": cid,
                    "risk_kinds": case_risk_kinds,
                    "bm25": 0.0,
                    "slots": {slot: 0.0 for slot in SLOTS},
                    "boost": 0.0,
                    "embedding": None,
                    "final": 0.0,
                    "card_ids": [],
                },
            )
            if score >= threshold and card_id not in entry["card_ids"]:
                entry["card_ids"].append(card_id)
            if score > entry["final"]:
                entry.update(
                    bm25=round(weighted, 6),
                    slots={slot: round(value, 6) for slot, value in slot_scores.items()},
                    boost=boost,
                    final=round(score, 6),
                )
                best_card_by_case[cid] = card

    candidates = sorted(per_case.values(), key=lambda e: (-e["final"], e["case_id"]))
    kept = [entry for entry in candidates if entry["final"] >= threshold]

    if rerank and kept:
        if embed is None:
            from ..llm.client import embed_texts

            embed = embed_texts
        for entry in kept:
            best_card = best_card_by_case[entry["case_id"]]
            try:
                hits = vector_search(
                    db_path, _card_query_text(best_card), k=len(cases), embed=embed
                )
            except (FileNotFoundError, RuntimeError):
                hits = []
                method["rerank"] += " (case_vectors unavailable, order unchanged)"
            by_id = {h["case_id"]: h["similarity"] for h in hits}
            entry["embedding"] = by_id.get(entry["case_id"])
        kept.sort(
            key=lambda e: (
                -(e["embedding"] if e["embedding"] is not None else -1.0),
                -e["final"],
                e["case_id"],
            )
        )

    links = [
        _build_link(
            cases_by_id[entry["case_id"]],
            entry,
            best_card_by_case[entry["case_id"]],
            bool((risk_map.get(entry["case_id"]) or {}).get("text_verified", True)),
        )
        for entry in kept
    ]

    status = "완료" if links else "해당 사례 없음"
    reason = "" if links else "임계값을 넘는 사례 연결이 없음"
    return {
        "status": status,
        "reason": reason,
        "method": method,
        "candidates": candidates,
        "links": links,
    }
