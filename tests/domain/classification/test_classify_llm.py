"""classify_page against the fixtures with a real model. Paid; runs only with -m use_llm."""

import pytest

from financial_disclosure_review.domain.classification import classify_page
from tests.helpers import load_classify_fixtures, page_of

FIXTURES = load_classify_fixtures()


@pytest.mark.use_llm
@pytest.mark.parametrize("name", sorted(FIXTURES))
def test_the_model_reaches_the_expected_classification(name):
    fixture = FIXTURES[name]
    result = classify_page(page_of(fixture), "gpt-5-nano")
    expected = fixture["expected"]
    assert result["reason"]
    assert (result["product_type"], result["page_type"]) == (
        expected["product_type"],
        expected["page_type"],
    ), result["reason"]
