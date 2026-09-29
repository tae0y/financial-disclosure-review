"""Shared fixtures. The loaders and the fake ask live in tests/helpers.py."""

import pytest
from dotenv import find_dotenv, load_dotenv

from tests.helpers import CLASSIFY_MISSING, load_classify_fixtures

# The use_llm tests need the key the app reads at startup; the free ones never look at it.
load_dotenv(find_dotenv(usecwd=True))


@pytest.fixture(scope="session")
def classify_fixtures() -> dict[str, dict]:
    fixtures = load_classify_fixtures()
    if not fixtures:
        pytest.skip(CLASSIFY_MISSING)
    return fixtures


@pytest.fixture(scope="session")
def revolving(classify_fixtures) -> dict:
    return classify_fixtures["lottecard-revolving"]


@pytest.fixture(autouse=True)
def no_paid_tool_loops(request, monkeypatch):
    """Free tests never reach a tool-calling model.

    The page agent and the persona selection agent build a real
    `ToolChat` unless a test injects a scripted chat; with the key in `.env` that would spend
    money. Here a real turn raises instead, which every agent records as a stop reason. The
    `mock_api` fixture's tests keep real turns: their base URL is the local mock, their key fake.
    """
    if request.node.get_closest_marker("use_llm") or "mock_api" in request.fixturenames:
        return

    def refuse(self):
        raise RuntimeError("free test reached a real tool-calling model")

    monkeypatch.setattr("financial_disclosure_review.llm.client.ToolChat.turn", refuse)
