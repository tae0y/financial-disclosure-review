"""Decides whether a failed verification is worth retrying and from which node; else escalate."""

from collections.abc import Mapping
from typing import Any

MAX_LOOPS = 2

# Modules that read the verification feedback on the next round, and the node that owns each.
# `display_check` is deliberately absent: `judge_display` takes no feedback, so re-running it
# would repeat the same call on the same measurements. Its failures go to a person instead.
RETRYABLE: dict[str, str] = {
    "persona_explanation": "generate_persona_explanation",
    "ad_disclosure_check": "judge_ad_disclosure",
}
# Verification fields owned by `retry_dispatch`; `verify_answer` carries them across rounds.
RETRY_KEYS = ("retry_target", "retry_modules", "retry_history")
# Graph order, so a retry restarts at the earliest failed node and the rest follows by edges.
NODE_ORDER = ["generate_persona_explanation", "judge_ad_disclosure"]


def retryable_modules(verification: Mapping[str, Any]) -> list[str]:
    """Modules that failed and were given a concrete requested_change to act on."""
    actionable = {
        entry.get("module")
        for entry in verification.get("feedback") or []
        if entry.get("requested_change")
    }
    return sorted(m for m in verification.get("failed_modules") or [] if m in actionable)


def should_retry(verification: Mapping[str, Any]) -> bool:
    if verification.get("passed"):
        return False
    if int(verification.get("loop_count") or 0) >= MAX_LOOPS:
        return False
    return any(m in RETRYABLE for m in retryable_modules(verification))


def plan_retry(verification: Mapping[str, Any]) -> dict:
    """The Verification fields that name the next round. Written only by `retry_dispatch`."""
    modules = [m for m in retryable_modules(verification) if m in RETRYABLE]
    nodes = {RETRYABLE[m] for m in modules}
    target = next((node for node in NODE_ORDER if node in nodes), "")
    history = list(verification.get("retry_history") or [])
    history.append(
        {
            "loop": int(verification.get("loop_count") or 0),
            "failed_modules": list(verification.get("failed_modules") or []),
            "retried_modules": modules,
            "target": target,
            "feedback_count": len(verification.get("feedback") or []),
        }
    )
    return {"retry_target": target, "retry_modules": modules, "retry_history": history}


def escalation(verification: Mapping[str, Any]) -> dict:
    """Why a run stopped where it did, in the terms `end_report` prints for a reviewer."""
    if verification.get("passed"):
        return {"reason": "", "detail": ""}
    loops = int(verification.get("loop_count") or 0)
    failed = list(verification.get("failed_modules") or [])
    stuck = sorted(set(failed) - set(RETRYABLE))
    if loops >= MAX_LOOPS:
        return {
            "reason": "재시도 한도 초과",
            "detail": f"검증 루프 {loops}회를 모두 사용했으나 {', '.join(failed)} 모듈이"
            " 계속 기준에 미달했습니다.",
        }
    if stuck:
        return {
            "reason": "자동 재시도 불가",
            "detail": f"{', '.join(stuck)} 모듈의 실패는 재생성으로 고칠 수 없습니다"
            "(측정 불가·판정 불가)."
            " 사람이 원문과 화면을 직접 확인해야 합니다.",
        }
    return {
        "reason": "조치 가능한 피드백 없음",
        "detail": "실패 사유에 구체적인 수정 요청이 없어 재시도하지 않았습니다.",
    }
