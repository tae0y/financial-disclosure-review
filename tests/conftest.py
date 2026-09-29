"""Shared fixtures. The loaders and the fake ask live in tests/helpers.py."""

import pytest
from dotenv import find_dotenv, load_dotenv

from tests.helpers import load_classify_fixtures

# The use_llm tests need the key the app reads at startup; the free ones never look at it.
load_dotenv(find_dotenv(usecwd=True))


@pytest.fixture(scope="session")
def classify_fixtures() -> dict[str, dict]:
    return load_classify_fixtures()


@pytest.fixture(scope="session")
def revolving(classify_fixtures) -> dict:
    return classify_fixtures["lottecard-revolving"]


@pytest.fixture(autouse=True)
def no_paid_embeddings(request, monkeypatch):
    """Free tests never reach the embedding API.

    `search_cases` runs inside the compiled graph, so any full-graph test would otherwise spend
    money on a real `embed_texts` call. A test that means to pay marks itself `use_llm`; one that
    points the client at the local mock API (the `mock_api` fixture) reaches no paid API either.
    """
    if request.node.get_closest_marker("use_llm") or "mock_api" in request.fixturenames:
        return
    from tests.helpers import FakeEmbed

    monkeypatch.setattr("financial_disclosure_review.llm.client.embed_texts", FakeEmbed())


@pytest.fixture(autouse=True)
def no_paid_tool_loops(request, monkeypatch):
    """Free tests never reach a tool-calling model.

    The page agent, the case-linking agent and the persona selection agent build a real
    `ToolChat` unless a test injects a scripted chat; with the key in `.env` that would spend
    money. Here a real turn raises instead, which every agent records as a stop reason. The
    `mock_api` fixture's tests keep real turns: their base URL is the local mock, their key fake.
    """
    if request.node.get_closest_marker("use_llm") or "mock_api" in request.fixturenames:
        return

    def refuse(self):
        raise RuntimeError("free test reached a real tool-calling model")

    monkeypatch.setattr("financial_disclosure_review.llm.client.ToolChat.turn", refuse)
