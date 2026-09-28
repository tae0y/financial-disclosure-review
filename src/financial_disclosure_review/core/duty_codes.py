"""Explanation-duty codes that state the same duty on two rubric axes (audit P1-7).

`card_guardrail_rubric` (F group) and `plain_service_rubric` (설명의무 group) carry the same duties
with different codes, and both are judged so each citation survives. The report counts such a pair
as one topic. F01–F18 repeat 설명01–설명18 word for word; F19, F21 and F22 restate 설명19, 설명27
and 설명28. F20 has no counterpart.
"""

DUTY_TWINS: dict[str, str] = {
    **{f"F{n:02d}": f"설명{n:02d}" for n in range(1, 20)},
    "F21": "설명27",
    "F22": "설명28",
}


def duty_topic(code: str) -> str:
    """The 설명 code a duty code shares its topic with, or the code itself."""
    return DUTY_TWINS.get(code, code)
