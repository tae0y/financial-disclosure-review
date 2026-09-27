"""Entry point of the plain_language domain: rewrite every block, then keep only what checks out."""

from collections.abc import Mapping, Sequence
from html import escape
from typing import Any

from ...core.context import Context
from ...core.text import visible_text
from ...knowledge.rubrics import item_scope, load_rubric
from ...llm.client import ask, call_ask
from .blocks import plain_blocks
from .contract import verify_block, verify_source_quote, verify_terms
from .items import plain_items_report, plain_scope
from .prompts import PLAIN_TASK
from .schema import PlainDraftAnswer


def unjudged_plain(reason: str) -> dict:
    return {
        "items": [],
        "draft": [],
        "html": "",
        "term_refs": [],
        "accepted_blocks": [],
        "contract_errors": [{"source_id": "", "reason": reason}],
    }


def generate_plain(
    page: Mapping[str, Any],
    classification: Mapping[str, Any],
    feedback: Sequence[Mapping[str, Any]],
    ctx: Context,
    ask=ask,
) -> dict:
    """한 페이지의 쉬운말 생성. PlainLanguage의 모든 필드를 돌려준다."""
    html = page["html"]
    text = visible_text(html)
    blocks = plain_blocks(html)
    if not blocks:
        return unjudged_plain("원문에서 나눌 수 있는 텍스트 블록이 없음")

    guardrail_items = load_rubric(ctx.db_path, "card_guardrail_rubric")
    mandatory_items = [
        {"code": i["code"], "criterion": i["criterion"]}
        for i in guardrail_items
        if i["group"][0] in "ABC" and not item_scope(i, classification)
    ]
    plain_rubric_items = load_rubric(ctx.db_path, "plain_service_rubric", groups=("쉬운말서비스",))
    applied = [i for i in plain_rubric_items if not plain_scope(i, classification)]

    by_id = {b["id"]: b for b in blocks}
    wanted = set(by_id)
    own_feedback = [
        f for f in feedback if not f.get("module") or f["module"] == "generate_plain_lang"
    ]

    def check_draft(answer: dict) -> list[str]:
        problems = []
        seen_ids = [d["id"] for d in answer["items"]]
        if sorted(set(seen_ids)) != sorted(wanted) or len(seen_ids) != len(set(seen_ids)):
            problems.append(f"ids {sorted(set(seen_ids))} do not match {sorted(wanted)}")
            return problems
        for d in answer["items"]:
            if not d["text"].strip():
                problems.append(f"{d['id']}: text가 비어 있음")
        return problems

    def salvage(answer: dict, problems: list[str]) -> dict:
        """검증에 걸린 블록만 원문 문장으로 되돌린다. 답의 구성 자체가 어긋났으면 되돌릴 대상을
        특정할 수 없으므로 올린다."""
        bad = {p.split(":")[0] for p in problems if ":" in p and p.split(":")[0] in wanted}
        if not bad or len(bad) != len(problems):
            raise RuntimeError(f"generate_plain failed twice: {'; '.join(problems)[:400]}")
        return {
            "items": [
                {"id": d["id"], "text": by_id[d["id"]]["quote"], "terms": []}
                if d["id"] in bad
                else d
                for d in answer["items"]
            ]
        }

    candidate = call_ask(
        ask,
        ctx.model,
        PlainDraftAnswer,
        PLAIN_TASK,
        check_draft,
        "medium",
        salvage,
        blocks=[{"id": b["id"], "quote": b["quote"]} for b in blocks],
        mandatory_items=mandatory_items,
        previous_feedback=own_feedback,
    )
    draft = candidate["items"]

    accepted_blocks, contract_errors, term_refs = [], [], []
    html_by_id: dict[str, str] = {}
    for d in draft:
        block = by_id[d["id"]]
        quote, generated = block["quote"], d["text"]
        problems = [p for p in [verify_source_quote(text, quote)] if p]
        problems += verify_block(quote, generated)
        if problems:
            contract_errors.append({"source_id": d["id"], "reason": "; ".join(problems)})
            html_by_id[d["id"]] = quote
        else:
            accepted_blocks.append({"source_id": d["id"], "source_quote": quote, "text": generated})
            html_by_id[d["id"]] = generated
            for term in verify_terms(quote, d.get("terms") or []):
                term_refs.append({"source_id": d["id"], "term": term})

    html = "".join(
        f'<p data-source-id="{b["id"]}">{escape(html_by_id[b["id"]])}</p>' for b in blocks
    )
    items = plain_items_report(applied, contract_errors, term_refs)
    return {
        "items": items,
        "draft": draft,
        "html": html,
        "term_refs": term_refs,
        "accepted_blocks": accepted_blocks,
        "contract_errors": contract_errors,
    }
