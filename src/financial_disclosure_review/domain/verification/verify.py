"""Entry point of the verification domain: cross-check the three modules' answers."""

import re
from collections.abc import Mapping
from typing import Any

from ...core.display_codes import VIOLATION_KEYS
from ...core.text import locate_quote, visible_text


def verify(
    page: Mapping[str, Any],
    display_check: Mapping[str, Any],
    persona_explanation: Mapping[str, Any],
    ad_disclosure_check: Mapping[str, Any],
    loop_count: int,
) -> dict:
    """Cross-checks the three modules against each other and the input text; needs no model call."""
    product_text = visible_text(page.get("html") or "")
    advice_text = visible_text(persona_explanation.get("html") or "")

    failed: set[str] = set()
    reasons: list[str] = [
        "이 검증은 입력 텍스트에 대한 인용/ID의 정합성과 각 모듈 결과 내부의 모순 여부만"
        " 확인합니다. 통과가 실제 법률 준수를 뜻하지는 않습니다.",
    ]
    feedback: list[dict] = []

    def fail(
        module: str,
        reason: str,
        *,
        code: str = "",
        source_id: str = "",
        requested_change: str = "",
        target: str = "",
    ):
        failed.add(module)
        reasons.append(reason)
        if requested_change:
            feedback.append(
                {
                    "module": module,
                    "code": code,
                    "source_id": source_id,
                    "reason": reason,
                    "requested_change": requested_change,
                    "target": target,
                }
            )

    # ---- display_check ----
    if not display_check:
        fail(
            "display_check",
            "display_check가 비어 있습니다. judge_display_method를 먼저 실행하세요.",
        )
    else:
        judgments = display_check.get("judgments") or {}
        status = judgments.get("status")
        if status != "완료":
            fail(
                "display_check",
                f"display_check.judgments.status={status!r}: {judgments.get('reason', '')}",
            )
        for skipped in judgments.get("skipped") or []:
            reasons.append(f"display_check {skipped.get('code')} 제외: {skipped.get('reason')}")
        known_block_ids = {b.get("id") for b in judgments.get("blocks") or []}
        measures = judgments.get("measures") or {}
        for item in display_check.get("items") or []:
            code, verdict = item.get("code", ""), item.get("verdict")
            if verdict is None:
                continue
            if verdict == "판정 불가":
                fail("display_check", f"display_check {code}: 판정 불가 ({item.get('reason', '')})")
                continue
            block_ids, quotes = item.get("block_ids") or [], item.get("quotes") or []
            if not block_ids or not quotes:
                fail(
                    "display_check",
                    f"display_check {code} {verdict}: 인용 근거(block_ids/quotes)가 없습니다",
                    code=code,
                    requested_change="이 판정에 근거가 되는 block_id/quote를 최소 하나 인용하세요",
                )
                continue
            unknown = [b for b in block_ids if known_block_ids and b not in known_block_ids]
            if unknown:
                fail(
                    "display_check",
                    f"display_check {code}: block_ids {unknown}이(가) 측정된 블록 목록에 없습니다",
                    code=code,
                    source_id=",".join(unknown),
                    requested_change=(
                        "display_check.judgments.blocks에 실제로 있는 id로 다시 인용하세요"
                    ),
                )
            key = VIOLATION_KEYS.get(code)
            if key and code in measures:
                violating = measures[code].get(key) or []
                if verdict == "적합" and violating:
                    fail(
                        "display_check",
                        f"display_check {code} 적합 판정이 측정값 {key}={violating}과 모순됩니다",
                        code=code,
                        source_id=",".join(violating),
                        requested_change="측정된 위반이 있으므로 이 항목을 다시 판정하세요",
                    )

    # ---- persona_explanation ----
    # The advice sits beside the page. One that failed its own code checks is not shown, and its
    # problems are sent back as the request for the next draft.
    number_pattern = re.compile(r"\d+(?:[.,]\d+)?%?")
    problems = persona_explanation.get("problems") or []
    if not persona_explanation:
        fail(
            "persona_explanation",
            "persona_explanation이 비어 있습니다. generate_persona_explanation을 먼저 실행하세요.",
        )
    elif problems:
        fail(
            "persona_explanation",
            f"확인 권고가 코드 검사를 통과하지 못했습니다: {'; '.join(problems)}",
            requested_change=f"다음 문제를 고쳐 확인 권고를 다시 쓰세요: {'; '.join(problems)}",
        )
    elif not persona_explanation.get("html"):
        fail(
            "persona_explanation",
            f"persona_explanation.html이 비어 있습니다: {persona_explanation.get('reason', '')}",
        )
    else:
        ungrounded = sorted(
            {n for n in number_pattern.findall(advice_text) if n not in product_text}
        )
        if ungrounded:
            fail(
                "persona_explanation",
                f"확인 권고: 수치 {ungrounded}이(가) 원문에서 근거를 찾을 수 없습니다",
                requested_change=f"수치 {ungrounded}를 빼고 무엇을 확인할지만 쓰세요",
            )

    # ---- ad_disclosure_check ----
    if not ad_disclosure_check:
        fail(
            "ad_disclosure_check",
            "ad_disclosure_check가 비어 있습니다. judge_ad_disclosure를 먼저 실행하세요.",
        )
    else:
        original = ad_disclosure_check.get("original") or []
        if not original:
            fail("ad_disclosure_check", "ad_disclosure_check에 원문 판정이 없습니다.")
        for entry in original:
            code, verdict = entry.get("code", ""), entry.get("verdict")
            quote, reason = entry.get("quote", ""), entry.get("reason", "")
            if verdict is None:
                continue
            if verdict == "판정 불가":
                fail("ad_disclosure_check", f"ad_disclosure_check {code}: 판정 불가 ({reason})")
                continue
            # A missing disclosure cannot be quoted, so 부적합 may cite nothing (the prompt
            # asks for an empty quote there). A quote that is given must still be real.
            if verdict == "부적합" and not quote:
                continue
            if not quote or locate_quote(product_text, quote) is None:
                fail(
                    "ad_disclosure_check",
                    f"ad_disclosure_check {code}: 인용문이 product_page.html에서 발견되지 않습니다",
                    code=code,
                    requested_change="product_page.html에 실제로 있는 문구로 다시 인용하세요",
                    target="original",
                )

    return {
        "passed": not failed,
        "reasons": reasons,
        "failed_modules": sorted(failed),
        "feedback": feedback,
        "loop_count": loop_count + 1,
    }
