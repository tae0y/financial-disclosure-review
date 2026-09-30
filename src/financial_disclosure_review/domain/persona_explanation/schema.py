"""Response schema of the one model call this domain makes."""

from pydantic import BaseModel


class AdviceDraft(BaseModel):
    advice: str
    advice_codes: list[str]
