"""Response schema of the one model call this domain makes."""

from pydantic import BaseModel


class OverviewDraft(BaseModel):
    summary: str
    advice: str
    advice_codes: list[str]
