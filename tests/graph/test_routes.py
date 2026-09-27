"""route_after_classify sends non-review results straight to END."""

import pytest
from langgraph.graph import END

from financial_disclosure_review.classification.schema import PAGE_TYPE_BY_PRODUCT
from financial_disclosure_review.core.state import empty_state
from financial_disclosure_review.graph.routes import route_after_classify, route_after_verify
from tests.helpers import state_with


@pytest.mark.parametrize("product_type", ["범위 밖", "판정 불가"])
def test_a_non_review_result_ends_the_graph(product_type):
    state = state_with(classification={"product_type": product_type})
    assert route_after_classify(state) == END


@pytest.mark.parametrize("product_type", sorted(PAGE_TYPE_BY_PRODUCT))
def test_a_reviewable_product_goes_on_to_the_display_check(product_type):
    state = state_with(classification={"product_type": product_type})
    assert route_after_classify(state) == "judge_display_method"


def test_verify_goes_to_the_report_until_retries_are_built():
    assert route_after_verify(empty_state()) == "end_report"
