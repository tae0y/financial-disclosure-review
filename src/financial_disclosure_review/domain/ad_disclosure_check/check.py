"""Entry point of ad_disclosure_check: judge the page against the mandatory ad disclosures."""

from collections.abc import Mapping, Sequence
from typing import Any

from ...core.context import Context
from ...core.text import locate_quote, visible_text
from ...knowledge.rubrics import item_scope
from ...llm.client import ask, call_ask
from .prompts import DISCLOSURE_ORIGINAL_TASK
from .rubric import deferred_explanation_items, load_disclosure_items
from .schema import DisclosureJudgments


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
    on the page alone, and list the explanation-duty items left to the product documents."""
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
    classification: Mapping[str, Any],
    ctx: Context,
    previous_original: Sequence[Mapping[str, Any]] | None,
    previous_items: Sequence[Mapping[str, Any]] | None,
    ask=ask,
    *,
    feedback: Sequence[Mapping[str, Any]] = (),
) -> dict:
    """원문을 광고 의무표시 기준으로 판정한다. 재시도 때는 이전 판정을 두고 지적된 코드만 다시
    판정한다(첫 회차의 `deferred`는 State에 그대로 남는다)."""
    if previous_items is None or previous_original is None:
        return judge_original(page, classification, ctx, ask)
    items_rows, original_rows = list(previous_items), list(previous_original)
    requests = [
        f
        for f in feedback
        if f.get("module") == "ad_disclosure_check" and f.get("requested_change") and f.get("code")
    ]
    redo = {f["code"] for f in requests}
    in_scope = [i for i in load_disclosure_items(ctx.db_path) if i["code"] in redo]
    if in_scope:
        judged = judge_original_side(in_scope, visible_text(page["html"]), ctx.model, ask, requests)
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
    return {"items": items_rows, "original": original_rows}
