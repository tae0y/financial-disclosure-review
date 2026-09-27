"""classify_page against the six saved fixtures, with the model call faked."""

import pytest

from financial_disclosure_review.classification import classify_page
from financial_disclosure_review.classification.schema import PAGE_TYPE_BY_PRODUCT
from financial_disclosure_review.core.text import visible_text
from tests.helpers import load_classify_fixtures, make_fake_ask, page_of

FIXTURES = load_classify_fixtures()


def test_six_fixtures_are_loaded():
    assert len(FIXTURES) == 6


@pytest.mark.parametrize("name", sorted(FIXTURES))
def test_expected_answer_gives_the_expected_classification(name):
    fixture = FIXTURES[name]
    fake = make_fake_ask(fixture)
    result = classify_page(page_of(fixture), "fake", ask=fake)
    expected = fixture["expected"]
    assert result["product_type"] == expected["product_type"]
    assert result["page_type"] == expected["page_type"]
    assert result["reason"]
    if expected["product_type"] == "범위 밖":
        assert result["reason"].startswith("2단계")
        assert fake.calls == ["ClassifyAnswer", "VerifyAnswer"]
    else:
        assert fake.calls == ["ClassifyAnswer"]


def test_quote_missing_from_the_page_retries_once_then_gives_up(revolving):
    fake = make_fake_ask(revolving, quote="이 문장은 페이지 어디에도 없습니다")
    result = classify_page(page_of(revolving), "fake", ask=fake)
    assert result["product_type"] == "판정 불가"
    assert result["page_type"] is None
    assert result["reason"].startswith("판정 근거 부족")
    assert fake.calls == ["ClassifyAnswer", "ClassifyAnswer"]


def test_missing_reason_retries_once_then_gives_up(revolving):
    fake = make_fake_ask(revolving, reason="")
    result = classify_page(page_of(revolving), "fake", ask=fake)
    assert result["product_type"] == "판정 불가"
    assert result["reason"].startswith("판정 근거 부족")
    assert fake.calls == ["ClassifyAnswer", "ClassifyAnswer"]


def test_a_bad_first_answer_followed_by_a_good_one_is_accepted(revolving):
    good, bad = (
        make_fake_ask(revolving),
        make_fake_ask(revolving, quote="이 문장은 페이지 어디에도 없습니다"),
    )

    def flaky(model, schema, task, effort="low", **data):
        fake = good if bad.calls else bad
        return fake(model, schema, task, effort, **data)

    result = classify_page(page_of(revolving), "fake", ask=flaky)
    assert result["product_type"] == "리볼빙"
    assert result["page_type"] == "업무광고"


def test_verification_disagreeing_is_reported_as_a_mismatch(revolving):
    fake = make_fake_ask(revolving, stage=2, verify="예")
    result = classify_page(page_of(revolving), "fake", ask=fake)
    assert result["product_type"] == "판정 불가"
    assert result["page_type"] is None
    assert result["reason"].startswith("판정 불일치")
    assert "검증 이유" in result["reason"]
    assert "분류 이유" in result["reason"]


def test_a_quote_that_differs_only_in_whitespace_is_located(revolving):
    text = visible_text(revolving["html"])
    spaced = " \n ".join(text[:40])
    result = classify_page(page_of(revolving), "fake", ask=make_fake_ask(revolving, quote=spaced))
    assert result["product_type"] == "리볼빙"


def test_a_no_at_step_one_ends_the_review_out_of_scope(revolving):
    result = classify_page(page_of(revolving), "fake", ask=make_fake_ask(revolving, stage=1))
    assert result["product_type"] == "범위 밖"
    assert result["page_type"] is None
    assert result["reason"].startswith("1단계")


def test_every_product_type_has_a_page_type():
    assert set(PAGE_TYPE_BY_PRODUCT.values()) == {"상품광고", "업무광고"}
