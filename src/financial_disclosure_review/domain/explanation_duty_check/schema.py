"""Response schemas of the three model calls this domain makes."""

from typing import Literal

from pydantic import BaseModel


class ExplanationJudgment(BaseModel):
    code: str
    condition_status: Literal["해당없음", "성립", "불성립", "불명확"]
    verdict: Literal["적합", "부적합", "판정 불가"]
    quote: str
    reason: str


class ExplanationJudgments(BaseModel):
    items: list[ExplanationJudgment]


class PlainJudgment(BaseModel):
    code: str
    verdict: Literal["적합", "부적합", "판정 불가"]
    quote: str
    reason: str


class PlainJudgments(BaseModel):
    items: list[PlainJudgment]


class FidelityDiff(BaseModel):
    code: str
    kind: Literal["누락", "변경", "추가", "판정 불가", "변화없음"]
    reason: str


class FidelityDiffs(BaseModel):
    items: list[FidelityDiff]
