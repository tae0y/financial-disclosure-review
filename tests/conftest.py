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
