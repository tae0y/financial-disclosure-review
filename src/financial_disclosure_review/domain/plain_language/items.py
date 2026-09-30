"""Which rubric 쉬운말서비스 items this node can report on, and what it reports for each."""

from collections.abc import Mapping
from typing import Any

OUT_OF_SCOPE_PLAIN_ITEMS = {
    "쉬운말11": "문장 하나의 복잡도·중의성 판단은 사람의 읽기 판단이 필요해"
    " 이 노드가 기계적으로 확인하지 않음",
    "쉬운말14": "블록 간 배치 순서(우선 설명사항·불이익을 앞에 두는지)는"
    " 블록 단위 생성만으로 확인하지 않음",
    "쉬운말15": "권리·절차 안내 분량의 적정성은 이 노드가 판단하지 않음"
    "(누락 여부는 조건 키워드 검사로 일부만 확인)",
    "쉬운말17": "생성형 AI 사전 고지·결과 표시는 화면 UI 요소로 이 노드의 생성 범위 밖",
    "쉬운말18": "원문 복귀 도구·상시 의무표시 노출은 화면 UI 요소로 이 노드의 생성 범위 밖",
    "쉬운말19": "게시 전 준법감시인·협회 심의는 화면 밖 운영 절차로 이 노드가 수행하지 않음",
    "쉬운말20": "공개 전 사람 검토는 이 노드가 수행하지 않음."
    " 자동 검증 실패 블록을 원문으로 대체하는 부분만 이 노드가 구현함",
    "쉬운말21": "원문 변경 감지·재승인 절차는 이 노드의 생성 범위 밖",
    "쉬운말22": "오류 신고 창구·쉬운말 끄기 스위치는 화면 UI 요소로 이 노드의 생성 범위 밖",
}
PLAIN_ITEM_ERROR_MARKERS = {
    "쉬운말02": ("수치 포함", "단정·최상급"),
    "쉬운말03": ("가능성·조건 표현",),
    "쉬운말04": ("단정·최상급",),
    "쉬운말05": ("수치",),
    "쉬운말06": ("누락 가능",),
    "쉬운말07": ("누락 가능",),
    "쉬운말09": ("누락 가능", "수치 누락"),
    "쉬운말12": ("수치",),
    "쉬운말13": ("단정·최상급",),
    "쉬운말16": ("단정·최상급",),
}
PLAIN_TERM_CODES = {"쉬운말08", "쉬운말10"}


def plain_scope(item: dict, classification: Mapping[str, Any]) -> str:
    """Empty when the item applies and its targets include 쉬운말; otherwise why not."""
    product_type = classification.get("product_type")
    if product_type not in item["applies_to"]:
        return f"applies_to {item['applies_to']} does not include {product_type!r}"
    if "쉬운말" not in item["targets"]:
        return f"targets {item['targets']} does not include '쉬운말'"
    return ""


def plain_items_report(
    applied: list[dict], contract_errors: list[dict], term_refs: list[dict]
) -> list[dict]:
    """루브릭 쉬운말서비스 항목별로, 이 노드가 실제로 확인한 만큼만 적용/판정 불가로 보고한다."""
    all_reasons = " / ".join(e["reason"] for e in contract_errors)
    rows = []
    for item in applied:
        code = item["code"]
        if code in OUT_OF_SCOPE_PLAIN_ITEMS:
            rows.append(
                {"code": code, "verdict": "판정 불가", "reason": OUT_OF_SCOPE_PLAIN_ITEMS[code]}
            )
        elif code == "쉬운말01":
            rows.append(
                {
                    "code": code,
                    "verdict": "판정 불가",
                    "reason": "원문 의무표시 항목의 '예/아니오'는 judge_ad_disclosure가"
                    " 광고 의무표시 기준으로 판정함; 이 노드는 관련 문구를 모델에 안내만 하고"
                    " 결과를 스스로 검증하지 않음",
                }
            )
        elif code in PLAIN_TERM_CODES:
            rows.append(
                {
                    "code": code,
                    "verdict": "적용" if term_refs else "해당없음",
                    "reason": (
                        f"이번 회차에 풀어 쓴 용어 {len(term_refs)}건 (term_refs 참고)"
                        if term_refs
                        else "이번 회차 블록에서 풀어 쓴 용어가 없음"
                    ),
                }
            )
        else:
            markers = PLAIN_ITEM_ERROR_MARKERS.get(code, ())
            hit = any(m in all_reasons for m in markers)
            rows.append(
                {
                    "code": code,
                    "verdict": "위반 발견" if hit else "적용",
                    "reason": (
                        "관련 블록이 자동 검증에서 걸려 원문으로 대체됨"
                        if hit
                        else "관련 블록이 자동 검증을 통과함"
                    ),
                }
            )
    return rows
