"""Loaders and a scripted fake ask shared by the persona overview tests."""

import json
import tempfile
from functools import cache
from pathlib import Path

from financial_disclosure_review.core.context import Context
from financial_disclosure_review.knowledge.build import build_rubric_db
from tests.helpers import FIXTURE_DIR, FakeAsk

PERSONA_DIR = FIXTURE_DIR / "persona"
ASSETS = Path(__file__).resolve().parents[3] / "assets"
PROFILES = ASSETS / "persona_profiles.yaml"
CLASSIFICATION = {"product_type": "신용카드", "page_type": "상품광고", "reason": "테스트"}
LOWFIN = "nemotron-ko-70s-lowfin"
FIRSTCARD = "nemotron-ko-20s-firstcard"
LOANFAMILIAR = "nemotron-ko-40s-loanfamiliar"


def load_persona_fixture(name: str) -> dict:
    return json.loads((PERSONA_DIR / f"{name}.json").read_text(encoding="utf-8"))


@cache
def _reference_db() -> str:
    """The rubric DB built once from assets, so the overview sees the real disclosure items."""
    path = Path(tempfile.mkdtemp()) / "reference.sqlite"
    build_rubric_db(ASSETS, path)
    return str(path)


def fake_ctx() -> Context:
    return Context(model="fake", db_path=_reference_db())


class ScriptedAsk(FakeAsk):
    """Answers the calls in order (the last answer repeats) and keeps each call's data."""

    def __init__(self, answers: tuple[dict, ...]):
        self.queue = list(answers)
        self.data: list[dict] = []
        super().__init__(self._next)

    def _next(self, schema, data) -> dict:
        self.data.append(data)
        return self.queue.pop(0) if len(self.queue) > 1 else self.queue[0]


def scripted_ask(*answers: dict) -> ScriptedAsk:
    return ScriptedAsk(answers)
