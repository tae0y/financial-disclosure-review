"""Which rubric items this domain judges, and which ones code alone can rule out."""

from collections import Counter
from pathlib import Path

from ...knowledge.rubrics import load_rubric

APPLICATION_SCREEN_MARKERS = ("신청 화면", "가입 화면", "발급 화면")


def load_explanation_items(db_path: str | Path) -> list[dict]:
    """설명의무 그룹(plain_service_rubric)과 F군(card_guardrail_rubric)을 코드별로 유지해 합친다."""
    plain_items = load_rubric(db_path, "plain_service_rubric", groups=("설명의무",))
    f_items = [
        i for i in load_rubric(db_path, "card_guardrail_rubric") if i["group"].startswith("F")
    ]
    for item in plain_items:
        item["rubric"] = "plain_service_rubric"
    for item in f_items:
        item["rubric"] = "card_guardrail_rubric"
    combined = plain_items + f_items
    dupes = [c for c, n in Counter(i["code"] for i in combined).items() if n > 1]
    if dupes:
        raise RuntimeError(f"explanation-duty codes collide across rubrics: {dupes}")
    return combined


def explanation_scope(item: dict, product_type: str | None) -> str:
    """Return "" if the item applies; otherwise the code-only exclusion reason."""
    if product_type not in item["applies_to"]:
        return f"applies_to {item['applies_to']}에 product_type {product_type!r} 없음"
    condition = item.get("applies_condition")
    if condition and any(marker in condition for marker in APPLICATION_SCREEN_MARKERS):
        return (
            f"applies_condition({condition!r})은 신청·가입·발급 화면 전용 조건이며, 현재 입력은 "
            "청약·계약 단계의 신청 화면이 아닌 공개 상품광고/업무광고 페이지이므로(docs/README.md "
            "Rubrics and scope: 설명화면은 범위 밖) 준용 대상에서 제외함"
        )
    return ""
