"""Entry point of ad_disclosure_check: judge the page and its overview, record differences."""

from collections.abc import Mapping, Sequence
from typing import Any

from ...core.context import Context
from ...core.text import locate_quote, visible_text
from ...knowledge.rubrics import item_scope
from ...llm.client import ask, call_ask
from .prompts import DISCLOSURE_ORIGINAL_TASK, DISCLOSURE_OVERVIEW_TASK, FIDELITY_TASK
from .rubric import OVERVIEW_REQUIRED, deferred_explanation_items, load_disclosure_items
from .schema import DisclosureJudgments, FidelityDiffs, OverviewJudgments


def _quote_ok(verdict: str, quote: str, text: str) -> str:
    """verdict/quote 조합에 대한 공통 검증 문제 하나, 없으면 빈 문자열."""
    if verdict == "적합" and not quote:
        return "적합인데 quote 없음"
    if quote and not locate_quote(text, quote):
        return "quote가 입력 텍스트에 없음"
    return ""


def _feedback_notes(feedback: Sequence[Mapping[str, Any]]) -> dict:
    """The previous verification's requests as extra call data; empty feedback adds nothing."""
    notes = [
        {
            "code": f.get("code", ""),
            "reason": f.get("reason", ""),
            "requested_change": f.get("requested_change", ""),
        }
        for f in feedback
    ]
    return {"previous_feedback": notes} if notes else {}


def judge_overview_side(
    to_judge: list[dict],
    overview_text: str,
    model: str,
    ask,
    feedback: Sequence[Mapping[str, Any]] = (),
) -> list[dict]:
    """to_judge 코드들을 쉬운말 개요 text만 보고 판단한다(원문과 비교하지 않음)."""
    wanted = [i["code"] for i in to_judge]
    evidence = [{"code": i["code"], "criterion": i["criterion"]} for i in to_judge]

    def check(answer: dict) -> list[str]:
        problems = []
        seen = [j["code"] for j in answer["items"]]
        if sorted(seen) != sorted(wanted):
            return [f"codes {sorted(seen)} != {sorted(wanted)}"]
        for j in answer["items"]:
            if not j["reason"].strip():
                problems.append(f"{j['code']}: 근거 없음")
            problem = _quote_ok(j["verdict"], j["quote"], overview_text)
            if problem:
                problems.append(f"{j['code']}: {problem}")
        return problems

    def salvage(answer: dict, problems: list[str]) -> dict:
        bad = {p.split(":", 1)[0].strip() for p in problems}
        if not bad <= set(wanted):
            raise RuntimeError(f"judge_overview failed twice: {'; '.join(problems)[:400]}")
        note = "; ".join(problems)[:150]
        return {
            "items": [
                {
                    **j,
                    "verdict": "판정 불가",
                    "quote": "",
                    "reason": f"검증 실패로 판정 불가 처리: {note}",
                }
                if j["code"] in bad
                else j
                for j in answer["items"]
            ]
        }

    answer = call_ask(
        ask,
        model,
        OverviewJudgments,
        DISCLOSURE_OVERVIEW_TASK,
        check,
        "low",
        salvage,
        by_code=True,
        items=evidence,
        text=overview_text,
        **_feedback_notes(feedback),
    )
    return [
        {"code": j["code"], "verdict": j["verdict"], "quote": j["quote"], "reason": j["reason"]}
        for j in answer["items"]
    ]


def norm_quote(quote: str) -> str:
    return "".join((quote or "").split())


def fidelity_candidates(
    original_rows: Sequence[Mapping[str, Any]],
    overview_rows: Sequence[Mapping[str, Any]],
    to_judge_codes: list[str],
) -> list[dict]:
    """to_judge 코드 중 원문·개요 판정이나 인용이 달라 모델 검토가 필요한 후보만 추린다."""
    overview_by_code = {r["code"]: r for r in overview_rows}
    to_judge_set = set(to_judge_codes)
    candidates = []
    for o in original_rows:
        if o["code"] not in to_judge_set:
            continue
        p = overview_by_code.get(o["code"]) or {
            "verdict": "판정 불가",
            "quote": "",
            "reason": "개요 판정 없음",
        }
        if o["verdict"] != p["verdict"] or norm_quote(o["quote"]) != norm_quote(p["quote"]):
            candidates.append({"code": o["code"], "original": o, "overview": p})
    return candidates


def judge_fidelity_rows(
    candidates: list[dict], model: str, ask, criteria: Mapping[str, str] | None = None
) -> list[dict]:
    """Classify each candidate's difference against its own criterion, not quote against quote."""
    criteria = criteria or {}
    wanted = [c["code"] for c in candidates]
    evidence = [
        {
            "code": c["code"],
            "criterion": criteria.get(c["code"], ""),
            "original": {"verdict": c["original"]["verdict"], "quote": c["original"]["quote"]},
            "overview": {"verdict": c["overview"]["verdict"], "quote": c["overview"]["quote"]},
        }
        for c in candidates
    ]

    def check(answer: dict) -> list[str]:
        seen = [f["code"] for f in answer["items"]]
        if sorted(seen) != sorted(wanted):
            return [f"codes {sorted(seen)} != {sorted(wanted)}"]
        return [f"{f['code']}: 근거 없음" for f in answer["items"] if not f["reason"].strip()]

    def salvage(answer: dict, problems: list[str]) -> dict:
        bad = {p.split(":", 1)[0].strip() for p in problems}
        if not bad <= set(wanted):
            raise RuntimeError(f"judge_fidelity failed twice: {'; '.join(problems)[:400]}")
        note = "; ".join(problems)[:150]
        return {
            "items": [
                {**f, "kind": "판정 불가", "reason": f"검증 실패로 판정 불가 처리: {note}"}
                if f["code"] in bad
                else f
                for f in answer["items"]
            ]
        }

    answer = call_ask(
        ask, model, FidelityDiffs, FIDELITY_TASK, check, "low", salvage, items=evidence
    )
    quotes = {c["code"]: (c["original"]["quote"], c["overview"]["quote"]) for c in candidates}
    carried = {c["code"] for c in candidates if c["overview"]["verdict"] == "적합"}
    return [
        {
            "code": f["code"],
            "kind": f["kind"],
            "reason": f["reason"],
            "original_quote": quotes.get(f["code"], ("", ""))[0],
            "quote": quotes.get(f["code"], ("", ""))[1],
            # A 판정 불가 comparison names no concrete fix, so it goes to a person, not a retry.
            # A 누락 on an item the overview still carries is lost detail, which a summary may
            # drop; only content missing outright makes the overview redraw.
            "informational": f["kind"] == "판정 불가"
            or (f["kind"] == "누락" and f["code"] in carried),
        }
        for f in answer["items"]
        if f["kind"] != "변화없음"
    ]


def judge_original_side(
    in_scope: list[dict],
    original_text: str,
    model: str,
    ask,
    feedback: Sequence[Mapping[str, Any]] = (),
) -> dict[str, dict]:
    """in_scope 코드들을 원문 text만 보고 판단한다. 코드별 모델 답을 코드로 색인해 돌려준다."""
    wanted = [i["code"] for i in in_scope]
    has_condition = {i["code"]: bool(i.get("applies_condition")) for i in in_scope}
    evidence = [
        {
            "code": i["code"],
            "criterion": i["criterion"],
            "applies_condition": i.get("applies_condition"),
        }
        for i in in_scope
    ]

    def check(answer: dict) -> list[str]:
        problems = []
        seen = [j["code"] for j in answer["items"]]
        if sorted(seen) != sorted(wanted):
            return [f"codes {sorted(seen)} != {sorted(wanted)}"]
        for j in answer["items"]:
            if not j["reason"].strip():
                problems.append(f"{j['code']}: 근거 없음")
            expect_none = not has_condition[j["code"]]
            if expect_none and j["condition_status"] != "해당없음":
                problems.append(
                    f"{j['code']}: applies_condition 없음인데"
                    f" condition_status={j['condition_status']}"
                )
            if j["condition_status"] in ("불성립", "불명확"):
                if j["verdict"] != "판정 불가" or j["quote"]:
                    problems.append(
                        f"{j['code']}: condition_status={j['condition_status']}인데"
                        " verdict/quote가 비어있지 않음"
                    )
            else:
                problem = _quote_ok(j["verdict"], j["quote"], original_text)
                if problem:
                    problems.append(f"{j['code']}: {problem}")
        return problems

    def salvage(answer: dict, problems: list[str]) -> dict:
        bad = {p.split(":", 1)[0].strip() for p in problems}
        if not bad <= set(wanted):
            raise RuntimeError(f"judge_original failed twice: {'; '.join(problems)[:400]}")
        note = "; ".join(problems)[:150]
        return {
            "items": [
                {
                    **j,
                    "condition_status": "불명확",
                    "verdict": "판정 불가",
                    "quote": "",
                    "reason": f"검증 실패로 판정 불가 처리: {note}",
                }
                if j["code"] in bad
                else j
                for j in answer["items"]
            ]
        }

    answer = call_ask(
        ask,
        model,
        DisclosureJudgments,
        DISCLOSURE_ORIGINAL_TASK,
        check,
        "medium",
        salvage,
        by_code=True,
        items=evidence,
        text=original_text,
        **_feedback_notes(feedback),
    )
    return {j["code"]: j for j in answer["items"]}


def _original_rows(
    in_scope: Sequence[Mapping[str, Any]], judged: Mapping[str, Mapping[str, Any]]
) -> tuple[list[dict], list[dict]]:
    """Items and verdict rows for in-scope items; a model-omitted code becomes 판정 불가."""
    items_rows, original_rows = [], []
    for item in in_scope:
        j = judged.get(item["code"]) or {
            "condition_status": "불명확",
            "verdict": "판정 불가",
            "quote": "",
            "reason": "모델 응답에 이 항목이 없음",
        }
        applied = j["condition_status"] != "불성립"
        items_rows.append(
            {
                "code": item["code"],
                "rubric": item["rubric"],
                "applied": applied,
                "condition_status": j["condition_status"],
                "reason": j["reason"],
            }
        )
        if applied:
            original_rows.append(
                {
                    "code": item["code"],
                    "verdict": j["verdict"],
                    "quote": j["quote"],
                    "reason": j["reason"],
                }
            )
    return items_rows, original_rows


def judge_original(
    page: Mapping[str, Any], classification: Mapping[str, Any], ctx: Context, ask=ask
) -> dict:
    """The original side of a first round: scope every disclosure item, judge the in-scope ones
    on the page alone, and list the explanation-duty items left to the product documents. It
    reads neither the overview nor feedback, so it can run beside them."""
    in_scope, items_rows = [], []
    for item in load_disclosure_items(ctx.db_path):
        why = item_scope(item, classification)
        if why:
            items_rows.append(
                {
                    "code": item["code"],
                    "rubric": item["rubric"],
                    "applied": False,
                    "condition_status": "",
                    "reason": why,
                }
            )
        else:
            in_scope.append(item)

    judged: dict[str, dict] = {}
    if in_scope:
        judged = judge_original_side(in_scope, visible_text(page["html"]), ctx.model, ask)
    judged_items, original_rows = _original_rows(in_scope, judged)
    return {
        "items": items_rows + judged_items,
        "original": original_rows,
        "deferred": deferred_explanation_items(ctx.db_path, classification.get("product_type")),
    }


def judge_disclosure(
    page: Mapping[str, Any],
    overview: Mapping[str, Any],
    classification: Mapping[str, Any],
    ctx: Context,
    previous_original: Sequence[Mapping[str, Any]] | None,
    previous_items: Sequence[Mapping[str, Any]] | None,
    ask=ask,
    *,
    feedback: Sequence[Mapping[str, Any]] = (),
) -> dict:
    """원문과 개요를 같은 기준으로 판정하고 차이를 기록; 재시도 시 지적된 코드만 다시 판정한다."""
    all_items = load_disclosure_items(ctx.db_path)
    overview_text = visible_text(overview["html"])
    own = [
        f
        for f in feedback
        if f.get("module") == "ad_disclosure_check" and f.get("requested_change")
    ]
    original_feedback = [f for f in own if f.get("target") == "original" and f.get("code")]
    overview_feedback = [f for f in own if f.get("target") == "overview"]
    deferred = None

    if previous_items is not None and previous_original is not None:
        items_rows, original_rows = list(previous_items), list(previous_original)
        redo = {f["code"] for f in original_feedback}
        in_scope = [i for i in all_items if i["code"] in redo]
        if in_scope:
            judged = judge_original_side(
                in_scope, visible_text(page["html"]), ctx.model, ask, original_feedback
            )
            redone_items, redone_original = _original_rows(in_scope, judged)
            by_code = {r["code"]: r for r in redone_items}
            items_rows = [by_code.get(r["code"], r) for r in items_rows]
            # An item re-judged as 불성립 drops out of `original`, exactly as on a first run.
            redone = {r["code"]: r for r in redone_original}
            original_rows = [
                redone[r["code"]] if r["code"] in redone else r
                for r in original_rows
                if r["code"] not in redo or r["code"] in redone
            ]
    else:
        first = judge_original(page, classification, ctx, ask)
        items_rows, original_rows = first["items"], first["original"]
        deferred = first["deferred"]

    # The overview is asked only for what it must carry (OVERVIEW_REQUIRED); page metadata stays
    # on the page it sits beside.
    to_judge_codes = [
        i["code"]
        for i in items_rows
        if i["applied"]
        and i["condition_status"] in ("해당없음", "성립")
        and i["code"] in OVERVIEW_REQUIRED
    ]
    to_judge = [i for i in all_items if i["code"] in to_judge_codes]
    unclear_rows = [
        r
        for r in original_rows
        if r["code"] not in to_judge_codes and r["code"] in OVERVIEW_REQUIRED
    ]

    overview_rows = unclear_rows + (
        judge_overview_side(to_judge, overview_text, ctx.model, ask, overview_feedback)
        if to_judge
        else []
    )

    candidates = fidelity_candidates(original_rows, overview_rows, to_judge_codes)
    criteria = {i["code"]: i["criterion"] for i in all_items}
    fidelity_rows = judge_fidelity_rows(candidates, ctx.model, ask, criteria) if candidates else []

    result = {
        "items": items_rows,
        "original": original_rows,
        "overview": overview_rows,
        "fidelity": fidelity_rows,
    }
    if deferred is not None:
        result["deferred"] = deferred
    return result
