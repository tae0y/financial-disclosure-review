"""Answer shapes of the two model steps: block labels and per-item verdicts."""

from typing import Literal

from pydantic import BaseModel


class ImageFlag(BaseModel):
    id: str
    alt_phrase: str


class DisplayLabels(BaseModel):
    mandatory: list[str]
    warnings: list[str]
    rates: list[str]
    benefits: list[str]
    penalties: list[str]
    image_disclosure: list[ImageFlag]
    note: str


class ItemVerdict(BaseModel):
    code: str
    verdict: Literal["적합", "부적합", "판정 불가"]
    block_ids: list[str]
    reason: str


class DisplayVerdicts(BaseModel):
    items: list[ItemVerdict]
