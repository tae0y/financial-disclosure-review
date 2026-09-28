"""Whether a condition/exception/penalty survived in meaning — judged by the model, not matched."""

from ...llm.client import call_ask
from .prompts import CONDITION_TASK
from .schema import ConditionJudgments


def judge_condition_preservation(pairs: list[dict], model: str, ask) -> dict[str, dict]:
    """pairs: [{"id", "quote", "text"}, ...]. 판정을 id로 색인해 돌려준다."""
    wanted = [p["id"] for p in pairs]

    def check(answer: dict) -> list[str]:
        seen = [j["id"] for j in answer["items"]]
        if sorted(seen) != sorted(wanted):
            return [f"ids {sorted(seen)} != {sorted(wanted)}"]
        return [f"{j['id']}: 근거 없음" for j in answer["items"] if not j["reason"].strip()]

    def salvage(answer: dict, problems: list[str]) -> dict:
        bad = {p.split(":", 1)[0].strip() for p in problems}
        if not bad <= set(wanted):
            raise RuntimeError(f"judge_condition failed twice: {'; '.join(problems)[:400]}")
        note = "; ".join(problems)[:150]
        return {
            "items": [
                {**j, "verdict": "판정 불가", "reason": f"검증 실패로 판정 불가 처리: {note}"}
                if j["id"] in bad
                else j
                for j in answer["items"]
            ]
        }

    answer = call_ask(
        ask,
        model,
        ConditionJudgments,
        CONDITION_TASK,
        check,
        "low",
        salvage,
        items=[{"id": p["id"], "quote": p["quote"], "text": p["text"]} for p in pairs],
    )
    return {j["id"]: j for j in answer["items"]}
