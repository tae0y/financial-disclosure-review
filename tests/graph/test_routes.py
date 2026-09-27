"""route_after_classify sends non-review results to the report, not to an empty END."""

import pytest

from financial_disclosure_review.core.state import empty_state
from financial_disclosure_review.domain.classification.schema import PAGE_TYPE_BY_PRODUCT
from financial_disclosure_review.graph.routes import route_after_classify, route_after_verify
from tests.helpers import state_with


@pytest.mark.parametrize("product_type", ["범위 밖", "판정 불가"])
def test_a_non_review_result_still_gets_a_report(product_type):
    """요청자는 '검토 대상이 아니다'라는 답도 문서로 받아야 합니다. end_report는 모델을 부르지
    않으므로 이 경로에 추가 비용이 없습니다."""
    state = state_with(classification={"product_type": product_type})
    assert route_after_classify(state) == "end_report"


@pytest.mark.parametrize("product_type", sorted(PAGE_TYPE_BY_PRODUCT))
def test_a_reviewable_product_goes_on_to_the_case_search(product_type):
    """`search_cases` sits between the classification and the display check, so a reviewable
    product goes there first and reaches `judge_display_method` by a fixed edge."""
    state = state_with(classification={"product_type": product_type})
    assert route_after_classify(state) == "search_cases"


def test_verify_goes_to_the_report_until_retries_are_built():
    assert route_after_verify(empty_state()) == "end_report"
