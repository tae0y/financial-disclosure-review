"""Response schemas of the two model calls this domain makes."""

from typing import Literal

from pydantic import BaseModel


class PlainBlockDraft(BaseModel):
    id: str
    text: str
    terms: list[str] = []


class PlainDraftAnswer(BaseModel):
    items: list[PlainBlockDraft]


class ConditionJudgment(BaseModel):
    id: str
    verdict: Literal["유지", "누락 가능", "판정 불가"]
    reason: str


class ConditionJudgments(BaseModel):
    items: list[ConditionJudgment]
