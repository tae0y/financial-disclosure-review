"""Response schema of the model call this domain makes."""

from typing import Literal

from pydantic import BaseModel


class DisclosureJudgment(BaseModel):
    code: str
    condition_status: Literal["해당없음", "성립", "불성립", "불명확"]
    verdict: Literal["적합", "부적합", "판정 불가"]
    quote: str
    reason: str


class DisclosureJudgments(BaseModel):
    items: list[DisclosureJudgment]
