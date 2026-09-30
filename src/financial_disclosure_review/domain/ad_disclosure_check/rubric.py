"""Which rubric items this domain judges, and which explanation-duty items it only lists."""

from pathlib import Path

from ...knowledge.rubrics import load_rubric, rubric_question

# The mandatory advertising disclosures of card_guardrail_rubric: 공통(A), 대출조건(B), 상품별(C).
DISCLOSURE_GROUPS = ("A", "B", "C")


def load_disclosure_items(db_path: str | Path) -> list[dict]:
    """광고 의무표시 항목(card_guardrail_rubric A·B·C군)을 yaml 순서대로 읽는다."""
    items = load_rubric(db_path, "card_guardrail_rubric", groups=DISCLOSURE_GROUPS)
    for item in items:
        item["rubric"] = "card_guardrail_rubric"
    return items


def deferred_explanation_items(db_path: str | Path, product_type: str | None) -> list[dict]:
    """설명의무 항목 중 이 상품유형에 걸리는 것. 판정하지 않는다.

    설명의무는 청약 단계의 상품설명서·설명화면에 걸리는 의무라서 광고 페이지로는 판정할 수
    없다. 담당자가 상품설명서에서 확인할 목록으로만 돌려준다."""
    return [
        {
            "code": item["code"],
            "question": rubric_question(item["criterion"]),
            "applies_condition": item.get("applies_condition"),
        }
        for item in load_rubric(db_path, "plain_service_rubric", groups=("설명의무",))
        if product_type in item["applies_to"]
    ]
