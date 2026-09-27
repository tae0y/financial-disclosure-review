"""계약 검사의 오탐 두 가지에 대한 회귀 테스트.

둘 다 2026-09-27 `evaluate --suite plain-contract`가 무결함 대조군 4건 중 2건을 위반으로
잡아내면서 드러났다(`eval/results/260927-173641-*.before-fix.json`).
"""

from financial_disclosure_review.domain.plain_language.contract import (
    counter_ones,
    has_phrase,
    verify_block,
)


def test_a_one_plus_period_unit_is_not_an_invented_number():
    """'연회비 20,000원' → '1년에 20,000원'은 수치를 지어낸 것이 아니다."""
    assert verify_block("연회비는 국내전용 20,000원입니다.", "1년에 20,000원을 냅니다.") == []
    assert counter_ones("1년에 20,000원") == {"1"}
    assert counter_ones("2개월 무이자") == set()


def test_an_invented_amount_is_still_caught():
    problems = verify_block("연회비는 국내전용 20,000원입니다.", "연회비는 12,000원입니다.")
    assert any("원문에 없는 수치 포함" in p for p in problems)
    assert any("원문 수치 누락" in p for p in problems)


def test_a_changed_period_is_still_caught_through_the_missing_number():
    problems = verify_block(
        "국내 가맹점에서 2개월 무이자 할부를 제공합니다.", "1개월 무이자 할부를 줍니다."
    )
    assert any("원문 수치 누락" in p for p in problems), problems


def test_a_short_phrase_inside_another_word_is_not_a_superlative():
    """'결제일에'의 '제일'은 최상급 표현이 아니다."""
    assert has_phrase("결제일에 카드 대금을 내지 않으면", "제일") is False
    assert verify_block(
        "카드 대금을 연체하면 개인신용평점이 하락할 수 있습니다.",
        "결제일에 카드 대금을 내지 않고 연체하면 신용평점이 하락할 수 있습니다.",
    ) == []


def test_a_real_superlative_is_still_caught_with_or_without_a_space():
    assert has_phrase("업계 제일의 혜택", "제일") is True
    assert has_phrase("최고 수준의 혜택", "최고") is True
    problems = verify_block(
        "국내 가맹점에서 2개월 무이자 할부를 제공합니다.",
        "국내 가맹점에서 업계 최고의 2개월 무이자 할부를 제공합니다.",
    )
    assert any("단정·최상급" in p for p in problems)


def test_a_superlative_the_original_already_used_is_not_flagged():
    assert verify_block("월 최대 5천원까지 적립됩니다.", "한 달에 최대 5천원까지 쌓입니다.") == []
