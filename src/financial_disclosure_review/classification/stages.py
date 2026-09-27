"""The three judgment steps: their questions, what each answer must carry, and how it reads."""

import re

from ..core.text import locate_quote, quote_percent
from .prompts import CLASSIFY_TASK

STAGES = [
    ("single_product", "single_product_quote", "single_product_reason"),
    ("loan_product", "loan_product_quote", "loan_product_reason"),
]
FIELDS_AFTER_STAGE = {
    1: [
        "loan_product_quote",
        "loan_product_reason",
        "loan_product",
        "evidence",
        "product_type_reason",
        "product_type",
    ],
    2: ["evidence", "product_type_reason", "product_type"],
}


def stage_question(stage: int) -> str:
    match = re.search(rf"(\[{stage}단계:[^\n]*\]\n.*?)- 답:", CLASSIFY_TASK, re.DOTALL)
    assert match, f"CLASSIFY_TASK에 {stage}단계가 없음"
    return match.group(1).strip()


def unjudged(reason: str) -> dict:
    return {"product_type": "판정 불가", "page_type": None, "reason": reason}


def check_answer(answer: dict, text: str) -> list[str]:
    """분류 답변의 빠진 값, 비워야 할 값, 페이지에 없는 quote를 찾아 문제 목록으로 돌려준다."""
    problems = []

    def check_quote(name: str) -> None:
        if answer[name] and not locate_quote(text, answer[name]):
            problems.append(f"{name}가 페이지의 보이는 텍스트에 없음")

    for stage, (flag, quote, reason) in enumerate(STAGES, 1):
        missing = [k for k in (quote, reason) if not answer[k]]
        if answer[flag] is None:
            missing.append(flag)
        if missing:
            problems.append(f"{stage}단계에 {', '.join(missing)} 없음")
            return problems
        check_quote(quote)
        if not answer[flag]:
            filled = [k for k in FIELDS_AFTER_STAGE[stage] if answer[k] is not None]
            if filled:
                problems.append(f"{stage}단계가 아니오인데 {', '.join(filled)}에 값이 있음")
            return problems
    missing = [k for k in FIELDS_AFTER_STAGE[2] if not answer[k]]
    if missing:
        problems.append(f"3단계에 {', '.join(missing)} 없음")
    check_quote("evidence")
    return problems


def report_answer(answer: dict, text: str) -> None:
    """관측용 출력. 판단에는 쓰지 않는다."""
    rows = [
        (
            1,
            answer["single_product"],
            answer["single_product_reason"],
            answer["single_product_quote"],
        ),
        (2, answer["loan_product"], answer["loan_product_reason"], answer["loan_product_quote"]),
        (3, answer["product_type"], answer["product_type_reason"], answer["evidence"]),
    ]
    for stage, result, reason, quote in rows:
        if result is None:
            continue
        print(
            f"    {stage}단계: {result} | {reason} | quote 위치 {quote_percent(text, quote or '')}"
        )
    print(f"    confidence: {answer['confidence']}")
