"""Entry point of the classification domain."""

from collections.abc import Mapping
from typing import Any

from ..core.text import locate_quote, visible_text
from ..llm.client import ask
from .prompts import CLASSIFY_TASK, VERIFY_TASK
from .schema import PAGE_TYPE_BY_PRODUCT, ClassifyAnswer, VerifyAnswer
from .stages import STAGES, check_answer, report_answer, stage_question, unjudged


def classify_page(page: Mapping[str, Any], model: str, ask=ask) -> dict:
    html = page.get("html")
    if not html:
        return unjudged("입력 없음: product_page.html이 비어 있음")
    text = visible_text(html)
    data = {"url": page.get("url"), "product": page.get("product"), "html": html}

    problems: list[str] = []
    for _ in range(2):
        extra = {"이전_답변의_문제": problems} if problems else {}
        answer = ask(model, ClassifyAnswer, CLASSIFY_TASK, "medium", **data, **extra)
        report_answer(answer, text)
        problems = check_answer(answer, text)
        if not problems:
            break
    else:
        return unjudged("판정 근거 부족: " + "; ".join(problems))

    labels = {1: "단일 상품 아님", 2: "여신금융 상품 아님"}
    for stage, (flag, quote, reason) in enumerate(STAGES, 1):
        if answer[flag]:
            continue
        located = locate_quote(text, answer[quote])
        assert located is not None  # check_answer rejected a quote that is not on the page
        start, end = located
        task = VERIFY_TASK.format(
            question=stage_question(stage),
            page_subject=answer["page_subject"],
            excerpt=text[max(0, start - 300) : end + 300],
        )
        check = ask(model, VerifyAnswer, task)
        if check["answer"] == "예":
            return unjudged(
                f"판정 불일치: {stage}단계 분류=아니오 / 검증=예 "
                f"(분류 이유: {answer[reason]} / 검증 이유: {check['reason']})"
            )
        return {
            "product_type": "범위 밖",
            "page_type": None,
            "reason": f"{stage}단계({labels[stage]}): {answer['page_subject']} / {answer[reason]}",
        }

    product_type = answer["product_type"]
    return {
        "product_type": product_type,
        "page_type": PAGE_TYPE_BY_PRODUCT[product_type],
        "reason": answer["product_type_reason"],
    }
