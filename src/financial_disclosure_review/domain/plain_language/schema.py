"""Response schema of the one model call this domain makes."""

from pydantic import BaseModel


class PlainBlockDraft(BaseModel):
    id: str
    text: str
    terms: list[str] = []


class PlainDraftAnswer(BaseModel):
    items: list[PlainBlockDraft]
