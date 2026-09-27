"""Which rubric items this domain judges, and which ones code alone can rule out."""

from collections import Counter
from pathlib import Path

from ...knowledge.rubrics import load_rubric

APPLICATION_SCREEN_MARKERS = ("신청 화면", "가입 화면", "발급 화면")


def load_explanation_items(db_path: str | Path) -> list[dict]:
    """설명의무 기준: plain_service_rubric의 설명의무 그룹(이 모듈의 1차 기준)과
    card_guardrail_rubric의 F군(같은 취지를 다른 코드 축으로 담은 목록)을 각각의 코드로 유지한 채
    합친다. 두 목록을 임의로 합치거나 문구를 바꾸지 않고 코드별로 독립적으로 판단한다."""
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
    """''면 범위 안(모델이 적용 조건을 판단해야 함). 빈 문자열이 아니면 코드만으로 결정한 제외
    사유. targets/page_types가 설명화면·권유·설명화면이어도 이 페이지(상품광고/업무광고)에
    준용하므로 그 자체로는 제외 사유가 아니다(docs/design.md Rubrics). 다만 조건 문구가 신청·가입·
    발급 화면 전용이면 이 그래프의 입력 자체가 그런 화면일 수 없으므로(신청 단계 설명화면은
    범위 밖) 모델 호출 없이 제외한다."""
    if product_type not in item["applies_to"]:
        return f"applies_to {item['applies_to']}에 product_type {product_type!r} 없음"
    condition = item.get("applies_condition")
    if condition and any(marker in condition for marker in APPLICATION_SCREEN_MARKERS):
        return (
            f"applies_condition({condition!r})은 신청·가입·발급 화면 전용 조건이며, 현재 입력은 "
            "청약·계약 단계의 신청 화면이 아닌 공개 상품광고/업무광고 페이지이므로(docs/design.md "
            "Rubrics: 설명화면은 범위 밖) 준용 대상에서 제외함"
        )
    return ""
