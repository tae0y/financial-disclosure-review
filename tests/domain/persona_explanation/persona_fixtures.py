"""Loaders and a scripted fake ask shared by the persona explanation and ledger-check tests."""

import json
from pathlib import Path

from bs4 import BeautifulSoup

from financial_disclosure_review.core.context import Context
from tests.helpers import FIXTURE_DIR, FakeAsk

PERSONA_DIR = FIXTURE_DIR / "persona"
PROFILES = Path(__file__).resolve().parents[3] / "assets" / "persona_profiles.yaml"
CLASSIFICATION = {"product_type": "신용카드", "page_type": "상품광고", "reason": "테스트"}
LOWFIN = "nemotron-ko-70s-lowfin"
FIRSTCARD = "nemotron-ko-20s-firstcard"
LOANFAMILIAR = "nemotron-ko-40s-loanfamiliar"


def load_persona_fixture(name: str) -> dict:
    return json.loads((PERSONA_DIR / f"{name}.json").read_text(encoding="utf-8"))


def fake_ctx() -> Context:
    return Context(model="fake")


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


def top_level_ids(html: str) -> list[str]:
    """data-source-id of each top-level <p>, or unit:<id> for each <section>, in document order."""
    soup = BeautifulSoup(html, "html.parser")
    ids = []
    for el in soup.find_all(recursive=False):
        if el.name == "section":
            ids.append(f"unit:{el['data-unit-id']}")
        else:
            ids.append(str(el["data-source-id"]))
    return ids
