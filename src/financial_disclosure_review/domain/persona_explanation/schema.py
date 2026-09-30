"""Response schema of the one model call this domain makes."""

from pydantic import BaseModel


class OverviewDraft(BaseModel):
    paragraphs: list[str]
