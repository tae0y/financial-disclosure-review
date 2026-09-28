"""Entry point of the verification domain: cross-check the three modules' answers."""

import re
from collections.abc import Mapping
from typing import Any

from ...core.display_codes import VIOLATION_KEYS
from ...core.text import locate_quote, visible_text


def verify(
    page: Mapping[str, Any],
    display_check: Mapping[str, Any],
    plain_language: Mapping[str, Any],
    explanation_duty_check: Mapping[str, Any],
    loop_count: int,
) -> dict:
    """Cross-check display_check / plain_language / explanation_duty_check against each other
    and against the real input text (product_page.html / plain_language.html). Every check here
    is decidable from the data itself (presence, quote/id lookup, numeric consistency), so this
    needs no model call. Returns exactly the Verification fields; it does not touch any other
    module's key.
    """
    product_text = visible_text(page.get("html") or "")
    plain_text = visible_text(plain_language.get("html") or "")
    accepted_blocks = plain_language.get("accepted_blocks") or []
    contract_errors = plain_language.get("contract_errors") or []
    known_plain_source_ids = {b.get("source_id", "") for b in accepted_blocks}

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

    # ---- plain_language ----
    if not accepted_blocks and not contract_errors:
        fail(
            "plain_language",
            "plain_language에 accepted_blocks와 contract_errors가 모두 없습니다."
            " 생성된 내용이 없습니다.",
        )
    for error in contract_errors:
        fail(
            "plain_language",
            f"plain_language contract_errors 남음: {error.get('source_id', '')}"
            f" - {error.get('reason', '')}",
            source_id=error.get("source_id", ""),
            requested_change="계약 오류를 해결하도록 이 블록을 다시 생성하세요",
        )
    number_pattern = re.compile(r"\d+(?:[.,]\d+)?%?")
    for block in accepted_blocks:
        source_id = block.get("source_id", "")
        source_quote, text = block.get("source_quote", ""), block.get("text", "")
        if not source_quote or locate_quote(product_text, source_quote) is None:
            fail(
                "plain_language",
                f"plain_language 블록 {source_id}: source_quote가 product_page.html에서"
                " 발견되지 않습니다",
                source_id=source_id,
                requested_change=(
                    "source_quote를 원문에 실제로 있는 문구로 수정하거나 블록을 다시 생성하세요"
                ),
            )
            continue
        ungrounded = sorted({n for n in number_pattern.findall(text) if n not in source_quote})
        if ungrounded:
            fail(
                "plain_language",
                f"plain_language 블록 {source_id}: 수치 {ungrounded}이(가) source_quote에서"
                " 근거를 찾을 수 없습니다",
                source_id=source_id,
                requested_change=f"수치 {ungrounded}를 원문과 대조해 제거하거나 근거를 보완하세요",
            )

    # ---- explanation_duty_check ----
    if not explanation_duty_check:
        fail(
            "explanation_duty_check",
            "explanation_duty_check가 비어 있습니다. judge_explanation_duty를 먼저 실행하세요.",
        )
    else:
        original = explanation_duty_check.get("original") or []
        plain = explanation_duty_check.get("plain") or []
        if not original and not plain:
            fail(
                "explanation_duty_check", "explanation_duty_check에 original/plain 판정이 없습니다."
            )
        for label, entries, text, source_name in (
            ("original", original, product_text, "product_page.html"),
            ("plain", plain, plain_text, "plain_language.html"),
        ):
            for entry in entries:
                code, verdict = entry.get("code", ""), entry.get("verdict")
                quote, reason = entry.get("quote", ""), entry.get("reason", "")
                if verdict is None:
                    continue
                if verdict == "판정 불가":
                    fail(
                        "explanation_duty_check",
                        f"explanation_duty_check.{label} {code}: 판정 불가 ({reason})",
                    )
                    continue
                if not quote or locate_quote(text, quote) is None:
                    fail(
                        "explanation_duty_check",
                        f"explanation_duty_check.{label} {code}: 인용문이 {source_name}에서"
                        " 발견되지 않습니다",
                        code=code,
                        requested_change=f"{source_name}에 실제로 있는 문구로 다시 인용하세요",
                        target=label,
                    )
        for entry in explanation_duty_check.get("fidelity") or []:
            source_id, kind = entry.get("source_id", ""), entry.get("kind", "")
            reason = entry.get("reason", "")
            fail(
                "plain_language",
                f"explanation_duty_check.fidelity: 쉬운말이 원문과 어긋납니다"
                f" ({source_id}, {kind}): {reason}",
                source_id=source_id,
                requested_change="원문의 사실/수치/조건을 보존하도록 이 블록을 다시 생성하세요",
            )
            if source_id and known_plain_source_ids and source_id not in known_plain_source_ids:
                fail(
                    "explanation_duty_check",
                    f"explanation_duty_check.fidelity의 source_id {source_id!r}가"
                    " plain_language 블록에 없습니다",
                    source_id=source_id,
                    requested_change=(
                        "plain_language.accepted_blocks에 실제로 있는 source_id를 인용하세요"
                    ),
                )

    return {
        "passed": not failed,
        "reasons": reasons,
        "failed_modules": sorted(failed),
        "feedback": feedback,
        "loop_count": loop_count + 1,
    }
