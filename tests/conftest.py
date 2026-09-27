"""Shared fixtures. The loaders and the fake ask live in tests/helpers.py."""

import pytest

from tests.helpers import load_classify_fixtures


@pytest.fixture(scope="session")
def classify_fixtures() -> dict[str, dict]:
    return load_classify_fixtures()


@pytest.fixture(scope="session")
def revolving(classify_fixtures) -> dict:
    return classify_fixtures["lottecard-revolving"]
