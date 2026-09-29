"""The reference-case linking agent: a bounded tool loop that proposes report-only case links.

The model reads the page's evidence cards, searches the product type's cases (BM25 from
`reference.py`, the deterministic retrieval, now the agent's search tool), reads a case, and
proposes a link. Code validates every proposal before it becomes a link: the case was searched
and read in this run, the cited cards exist, both quotes are found verbatim, and the stated
pattern carries no verdict. Links are references only; no judging prompt ever reads them.
Provisional design: see docs/agent-node-specs/reference_cases.md.
"""

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from ..core.context import Context
from ..core.text import locate_quote, short
from ..core.usage import BudgetError
from ..llm.client import ToolChat, tool_spec
from .reference import (
    BM25,
    PARTIAL_DETECTABILITY,
    RISK_KIND_BOOST,
    RISK_KINDS,
    bm25_tokens,
    card_query_text,
    case_doc,
    case_material_difference,
    default_risk_kinds_path,
    load_case_source,
    load_risk_kinds,
    split_sentences,
)
from .search import search as vector_search

MAX_TURNS = 8
# Cards that make a concrete claim a regulator case could be about. A first `finish` while some
# of them were never searched (or while nothing was read) is sent back once with their ids.
CONCRETE_KINDS = {
    "rate_claim",
    "fee_claim",
    "benefit_claim",
    "eligibility",
    "condition",
    "exception",
    "warning",
}
MAX_LINKS = 5
MAX_TOP_K = 10
RESULT_LIMIT = 12_000
# A link names a shared pattern; it never says whether the page is compliant.
VERDICT_WORDS = re.compile(r"적합|부적합|위반|합법|불법|문제\s*없")
RERANK_ON = "embedding cosine via case_vectors (reorder only)"
RERANK_UNAVAILABLE = " (case_vectors unavailable, order unchanged)"

SYSTEM_PROMPT = """You link a financial product page's evidence cards to published regulator cases, as references for a human reviewer.

A link is a reference, not a finding: it says "this page shows the same advertising or explanation pattern that a regulator named in this case". It is never a verdict on the page. Most cards have no fitting case, and proposing no link at all is a correct outcome. A weak or merely topical link is worse than none.

Input: the page's product type and its evidence cards (id, kind, claim, qualifiers, exceptions, numbers, quote). The quote is the page's exact wording.

Tools: search_cases (BM25 over this product type's cases; your own query words, optionally plus cited cards' text; returns case summaries, never full text), read_case (one case's fields and its text as numbered sentences), propose_link (one link, validated by code), finish (end).

Method:
1. Pick the cards that make a concrete claim, condition, exception or warning. Skip generic text.
2. search_cases with words describing the pattern (e.g. "최대 할인율만 강조, 조건 미표기"), citing the card ids.
3. read_case on a promising hit. Link only when the case describes the same pattern the card shows, not merely the same topic or vocabulary.
4. propose_link, then continue or finish.

Rules:
- page_quote must be copied exactly from the quote of one of the cited cards. case_quote must be copied exactly from one sentence of the case text read with read_case.
- If read_case says the text may not be quoted (text_verified false), case_quote must be "".
- same_pattern: one Korean sentence naming the shared advertising/explanation pattern. Never a verdict: no 적합, 부적합, 위반, 합법, 불법, 문제없다.
- material_difference: how the page differs from the case (different product, the page does state the condition elsewhere, and so on). Code adds the case's own caveats.
- product_basis 유추 means the case comes from another sector with the same advertising type, not from this product type.
- page_only_detectability partial, review_required or out_of_scope means the page alone cannot settle the pattern; say what else would be needed in material_difference.
- Link only when the card itself shows the problem the case names (a missing or hidden condition, a rate shown without its range, a softened risk, unconditional wording, ...) or wording the case explicitly allows or forbids. A card that states a condition, rate or risk clearly is not a link to a case about hiding or omitting it.
- Cover the page: search every group of concrete cards (rates/fees, benefits with their conditions and exceptions, warnings), several searches per turn. Read the promising hits before deciding. A first finish while concrete cards were never searched is sent back with their ids.
- Only cases returned by search_cases and read with read_case in this run can be linked. At most one link per case, at most 5 links.
- You have a limited number of model turns. Call several independent tools in one turn. Call finish when done."""  # noqa: E501


class SearchCases(BaseModel):
    """BM25 search over this product type's cases. query is your own description of the
    pattern; card_ids adds those cards' text to it; risk_kind (rate_fee, benefit_condition or
    warning_penalty) ranks cases curated with that kind higher. Returns case summaries only."""

    query: str
    card_ids: list[str] = []
    risk_kind: str = ""
    top_k: int = 5


class ReadCase(BaseModel):
    """One case's fields and its text as numbered sentences, with whether it may be quoted."""

    case_id: str


class ProposeLink(BaseModel):
    """Propose one reference link. Code checks that the case was searched and read, the cards
    exist, both quotes are exact, and same_pattern carries no verdict; a refusal says why."""

    case_id: str
    card_ids: list[str]
    page_quote: str
    case_quote: str
    same_pattern: str
    material_difference: list[str] = []


class Finish(BaseModel):
    """End linking. Proposing no link is a correct outcome when no case fits."""

    reason: str = Field(min_length=1)


SCHEMAS: dict[str, type[BaseModel]] = {
    "search_cases": SearchCases,
    "read_case": ReadCase,
    "propose_link": ProposeLink,
    "finish": Finish,
}
TOOLS = [tool_spec(name, schema) for name, schema in SCHEMAS.items()]


def _blocked(reason: str) -> dict:
    return {"blocked": True, "blocked_reason": reason}


class LinkRun:
    """One page's linking state: the cases, what was searched and read, and accepted links."""

    def __init__(
        self,
        cases: Sequence[Mapping[str, Any]],
        risk_map: Mapping[str, Mapping[str, Any]],
        cards: Sequence[Mapping[str, Any]],
        db_path: str | Path,
        product_type: str,
        rerank: bool,
        embed=None,
    ) -> None:
        self.cases = {case["case_id"]: case for case in cases}
        self.risk_map = risk_map
        self.cards = {card["id"]: card for card in cards if card.get("id")}
        self.db_path, self.product_type = db_path, product_type
        self.bm25 = BM25({cid: bm25_tokens(case_doc(case)) for cid, case in self.cases.items()})
        self.rerank = RERANK_ON if rerank else "off"
        self.embed = embed
        self.searches = self.reads = 0
        self.searched: set[str] = set()
        self.read: set[str] = set()
        self.cited_cards: set[str] = set()
        self.nudged = False
        self.candidates: dict[str, dict[str, Any]] = {}
        self.links: list[dict[str, Any]] = []

    def call(self, name: str, args: Mapping[str, Any]) -> dict:
        """Run one tool call; anything invalid comes back blocked with the reason."""
        if name not in SCHEMAS:
            return _blocked(f"unknown tool {name!r}")
        try:
            parsed = SCHEMAS[name].model_validate(args)
        except ValidationError as error:
            fields = sorted({".".join(str(p) for p in e["loc"]) for e in error.errors()})
            return _blocked(f"invalid arguments: {', '.join(fields)}")
        if isinstance(parsed, SearchCases):
            return self.search_cases(parsed)
        if isinstance(parsed, ReadCase):
            return self.read_case(parsed.case_id)
        if isinstance(parsed, ProposeLink):
            return self.propose_link(parsed)
        return self.finish()

    def finish(self) -> dict:
        """End the loop, unless concrete cards were never searched or nothing was read: then
        send it back once, naming what is left (the same one-time nudge the page agent gets)."""
        unsearched = [
            cid
            for cid, card in self.cards.items()
            if card.get("kind") in CONCRETE_KINDS and cid not in self.cited_cards
        ]
        if not self.nudged and (unsearched or (self.searches and not self.reads)):
            self.nudged = True
            return {
                "finished": False,
                "nudge": (
                    "not finished: search the concrete cards never cited in a search"
                    " (group them), read the promising hits, then finish. Finish again to"
                    " stop anyway."
                ),
                "unsearched_card_ids": unsearched[:40],
                "cases_read": self.reads,
            }
        return {"finished": True}

    def _text_verified(self, case_id: str) -> bool:
        return bool((self.risk_map.get(case_id) or {}).get("text_verified", True))

    def _similarities(self, query: str) -> dict[str, float] | None:
        """Cosine similarity per case for the query, or None when rerank is off or unavailable."""
        if self.rerank != RERANK_ON:
            return None
        embed = self.embed
        if embed is None:
            from ..llm.client import embed_texts

            embed = embed_texts
        try:
            hits = vector_search(
                self.db_path, query, kind=self.product_type, k=len(self.cases), embed=embed
            )
        except (FileNotFoundError, RuntimeError):
            self.rerank += RERANK_UNAVAILABLE
            return None
        return {hit["case_id"]: hit["similarity"] for hit in hits}

    def search_cases(self, args: SearchCases) -> dict:
        unknown = [cid for cid in args.card_ids if cid not in self.cards]
        if unknown:
            return _blocked(f"unknown card ids {unknown}")
        if args.risk_kind and args.risk_kind not in RISK_KINDS:
            return _blocked(f"risk_kind must be one of {list(RISK_KINDS)} or empty")
        card_ids = list(dict.fromkeys(args.card_ids))
        self.cited_cards.update(card_ids)
        query = " ".join(
            [args.query.strip(), *(card_query_text(self.cards[cid]) for cid in card_ids)]
        ).strip()
        tokens = bm25_tokens(query)
        if not tokens:
            return _blocked("query is empty")
        self.searches += 1
        scored = []
        for cid in self.cases:
            score = self.bm25.score(cid, tokens)
            if score <= 0:
                continue
            kinds = (self.risk_map.get(cid) or {}).get("risk_kinds") or []
            if args.risk_kind and args.risk_kind in kinds:
                score += RISK_KIND_BOOST
            scored.append((cid, round(score, 6)))
        similarity = self._similarities(query) if scored else None
        if similarity is not None:
            scored.sort(key=lambda s: (-similarity.get(s[0], -1.0), -s[1], s[0]))
        else:
            scored.sort(key=lambda s: (-s[1], s[0]))
        top = scored[: max(1, min(args.top_k, MAX_TOP_K))]
        results = []
        for cid, score in top:
            case = self.cases[cid]
            self.searched.add(cid)
            entry = self.candidates.setdefault(cid, {"case_id": cid, "score": 0.0, "card_ids": []})
            entry["score"] = max(entry["score"], score)
            entry["card_ids"] += [c for c in card_ids if c not in entry["card_ids"]]
            row = {
                "case_id": cid,
                "record_type": case.get("record_type", ""),
                "product_basis": case.get("product_basis", ""),
                "issue": case.get("issue", ""),
                "mvp_signal": case.get("mvp_signal", ""),
                "page_only_detectability": case.get("page_only_detectability", ""),
                "score": score,
            }
            if similarity is not None:
                row["embedding"] = similarity.get(cid)
            results.append(row)
        out: dict[str, Any] = {"results": results}
        if not results:
            out["note"] = "no case shares words with this query"
        return out

    def read_case(self, case_id: str) -> dict:
        case = self.cases.get(case_id)
        if case is None:
            return _blocked(f"unknown case_id {case_id!r} for this product type")
        self.reads += 1
        self.read.add(case_id)
        verified = self._text_verified(case_id)
        out = {
            "case_id": case_id,
            **{
                key: case.get(key, "")
                for key in (
                    "record_type",
                    "institution",
                    "official_date",
                    "product_basis",
                    "product_subtype",
                    "legal_basis",
                    "issue",
                    "outcome",
                    "mvp_signal",
                    "page_only_detectability",
                )
            },
            "text_verified": verified,
            "sentences": [
                {"n": n, "text": sentence}
                for n, sentence in enumerate(split_sentences(case.get("text", "")), start=1)
            ],
        }
        if not verified:
            out["quote_rule"] = (
                "text_verified is false: this text was never checked verbatim against its"
                ' source, so it may not be quoted. Use case_quote "".'
            )
        return out

    def propose_link(self, args: ProposeLink) -> dict:
        case_id = args.case_id
        if len(self.links) >= MAX_LINKS:
            return _blocked(f"link cap {MAX_LINKS} reached")
        if case_id not in self.searched:
            return _blocked(f"search_cases did not return {case_id!r} in this run")
        if case_id not in self.read:
            return _blocked(f"read_case {case_id!r} before proposing a link to it")
        if any(link["case_id"] == case_id for link in self.links):
            return _blocked(f"{case_id!r} is already linked; one link per case")
        card_ids = list(dict.fromkeys(args.card_ids))
        if not card_ids:
            return _blocked("cite at least one card id")
        unknown = [cid for cid in card_ids if cid not in self.cards]
        if unknown:
            return _blocked(f"unknown card ids {unknown}")
        if not any(
            locate_quote(str(self.cards[cid].get("quote") or ""), args.page_quote) is not None
            for cid in card_ids
        ):
            return _blocked("page_quote is not found in the quote of any cited card")
        case = self.cases[case_id]
        verified = self._text_verified(case_id)
        if not verified and args.case_quote.strip():
            return _blocked('text_verified is false for this case: case_quote must be ""')
        if verified and locate_quote(case.get("text", ""), args.case_quote) is None:
            return _blocked("case_quote is not found in the case text")
        same_pattern = args.same_pattern.strip()
        if not same_pattern:
            return _blocked("same_pattern is empty")
        verdict = VERDICT_WORDS.search(same_pattern)
        if verdict:
            return _blocked(
                f"same_pattern names a verdict ({verdict.group()!r}); describe the pattern only"
            )
        detectability = case.get("page_only_detectability", "")
        model_diffs = [d.strip() for d in args.material_difference if d.strip()]
        self.links.append(
            {
                "case_id": case_id,
                "card_ids": card_ids,
                "page_quote": args.page_quote,
                "case_quote": args.case_quote if verified else "",
                "case_quote_note": "" if verified else "원문 재확인 필요",
                "same_pattern": same_pattern,
                "material_difference": list(
                    dict.fromkeys(model_diffs + case_material_difference(case))
                ),
                "page_only_detectability": detectability,
                "page_only_note": (
                    "페이지 단독 판단 불가" if detectability in PARTIAL_DETECTABILITY else ""
                ),
                "official_url": case.get("official_primary_url", ""),
                "decided_by": "agent",
            }
        )
        return {
            "accepted": True,
            "links": len(self.links),
            "links_left": MAX_LINKS - len(self.links),
        }


def _card_view(card: Mapping[str, Any]) -> dict:
    keys = ("id", "kind", "subject", "claim", "qualifiers", "exceptions", "numbers", "quote")
    return {key: card.get(key) for key in keys}


def _result(status: str, reason: str, method: dict, **rest) -> dict:
    return {
        "status": status,
        "reason": reason,
        "method": method,
        "candidates": rest.get("candidates", []),
        "links": rest.get("links", []),
        "agent_trace": rest.get("agent_trace", []),
        "stop_reason": rest.get("stop_reason", ""),
    }


def link_reference_cases(
    cards: Sequence[Mapping[str, Any]],
    classification: Mapping[str, Any],
    db_path: str | Path,
    *,
    ctx: Context,
    risk_kinds_path: str | Path | None = None,
    corpus_path: str | Path | None = None,
    embed=None,
    chat=None,
) -> dict[str, Any]:
    """`{status, reason, method, candidates, links, agent_trace, stop_reason}` for one page.

    `status`: 건너뜀 (no cards) | 판정 불가 (case source or risk-kind file missing, or the run
    stopped before any link) | 해당 사례 없음 (no case for the product type, or none linked) |
    완료. No model is called unless there are cards and cases. Never raises for a budget or
    model failure. `chat` stands in for ToolChat.
    """
    max_turns = int(getattr(ctx, "case_link_max_turns", MAX_TURNS))
    method: dict[str, Any] = {
        "linking": "agent",
        "model": ctx.model,
        "max_turns": max_turns,
        "searches": 0,
        "reads": 0,
        "rerank": RERANK_ON if ctx.case_rerank else "off",
    }
    if not cards:
        return _result("건너뜀", "카드가 없어 사례 연결을 실행하지 않음", method)

    product_type = classification.get("product_type") or ""
    product_types = (product_type,) if product_type else ()
    try:
        cases, source = load_case_source(db_path, corpus_path, product_types)
        method["cases_from"] = source
    except (FileNotFoundError, RuntimeError) as error:
        return _result("판정 불가", str(error), method)
    try:
        risk_map = load_risk_kinds(risk_kinds_path or default_risk_kinds_path())
    except FileNotFoundError as error:
        return _result("판정 불가", f"case_risk_kinds.yaml을 찾을 수 없음: {error}", method)
    if not cases:
        return _result("해당 사례 없음", f"{product_type!r}에 해당하는 사례가 없음", method)

    run = LinkRun(cases, risk_map, cards, db_path, product_type, ctx.case_rerank, embed)
    chat = chat if chat is not None else ToolChat(ctx.model, TOOLS, label="case_link")
    chat.system(SYSTEM_PROMPT)
    chat.user(
        json.dumps(
            {
                "product_type": product_type,
                "cards": [_card_view(card) for card in cards],
                "cases_available": len(cases),
                "risk_kinds": list(RISK_KINDS),
                "max_links": MAX_LINKS,
                "turns_available": max_turns,
            },
            ensure_ascii=False,
        )
    )
    trace: list[dict[str, Any]] = []
    stop_reason, stop_note = "max_turns", ""
    for turn in range(1, max_turns + 1):
        try:
            reply = chat.turn()
        except BudgetError as error:
            stop_reason, stop_note = "budget_exhausted", str(error)
            break
        except Exception as error:  # a model or network failure must not stop the review
            stop_reason, stop_note = "model_error", type(error).__name__
            break
        left = max_turns - turn
        if not reply["tool_calls"]:
            chat.user(f"Use the tools. Call finish when done. Turns left: {left}.")
            continue
        for call in reply["tool_calls"]:
            args = call.get("args") or {}
            result = run.call(call["name"], args)
            text = short(
                json.dumps({**result, "turns_left": left}, ensure_ascii=False), RESULT_LIMIT
            )
            trace.append(
                {
                    "turn": turn,
                    "tool": call["name"],
                    "args": dict(args),
                    "result": text,
                    "blocked": bool(result.get("blocked", False)),
                    "blocked_reason": result.get("blocked_reason", ""),
                }
            )
            chat.tool_result(call["id"], text)
            if result.get("finished"):
                stop_reason = "finished"
                break
            if len(run.links) >= MAX_LINKS:
                stop_reason = "link_cap"
                break
        if stop_reason in ("finished", "link_cap"):
            break

    method.update(searches=run.searches, reads=run.reads, rerank=run.rerank)
    candidates = sorted(run.candidates.values(), key=lambda c: (-c["score"], c["case_id"]))
    rest = {
        "candidates": candidates,
        "links": run.links,
        "agent_trace": trace,
        "stop_reason": stop_reason,
    }
    interrupted = stop_reason in ("budget_exhausted", "model_error")
    if run.links:
        reason = ""
        if interrupted or stop_reason == "max_turns":
            reason = f"사례 연결이 {stop_reason}로 끝나 그때까지 검증된 연결만 보고함"
        return _result("완료", reason, method, **rest)
    if interrupted:
        return _result("판정 불가", f"사례 연결 중단({stop_reason}): {stop_note}", method, **rest)
    if stop_reason == "max_turns":
        return _result(
            "해당 사례 없음", f"턴 한도 {max_turns} 안에 검증된 사례 연결이 없음", method, **rest
        )
    return _result("해당 사례 없음", "에이전트가 같은 패턴의 사례를 연결하지 않음", method, **rest)
