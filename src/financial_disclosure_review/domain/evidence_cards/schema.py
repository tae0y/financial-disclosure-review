"""Answer shape of the single evidence-card extraction model call."""

from typing import Literal

from pydantic import BaseModel

EVIDENCE_KINDS = (
    "benefit_claim",
    "rate_claim",
    "fee_claim",
    "eligibility",
    "condition",
    "exception",
    "warning",
    "footnote",
)


class EvidenceCardDraft(BaseModel):
    kind: Literal[
        "benefit_claim",
        "rate_claim",
        "fee_claim",
        "eligibility",
        "condition",
        "exception",
        "warning",
        "footnote",
    ]
    subject: str
    claim: str
    qualifiers: list[str] = []
    exceptions: list[str] = []
    numbers: list[str] = []
    quote: str
    source_id: str


class EvidenceCardDrafts(BaseModel):
    items: list[EvidenceCardDraft]
