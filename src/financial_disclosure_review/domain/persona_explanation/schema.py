"""Response schema of the one model call this domain makes."""

from pydantic import BaseModel


class PersonaUnitDraft(BaseModel):
    card_ids: list[str]
    source_ids: list[str]
    exact_fact: str
    explanation: str
    analogy: str
    persona_question_answered: str


class PersonaUnitDrafts(BaseModel):
    items: list[PersonaUnitDraft]
