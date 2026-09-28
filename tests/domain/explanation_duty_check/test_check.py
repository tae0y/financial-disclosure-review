"""judge_explanation with the model faked: what code rules out, what the model decides, and what
the retry path is allowed to recompute."""

import pytest

from financial_disclosure_review.core.context import Context
from financial_disclosure_review.core.text import locate_quote, visible_text
from financial_disclosure_review.domain.explanation_duty_check.check import judge_explanation
from financial_disclosure_review.domain.explanation_duty_check.rubric import (
    load_explanation_items,
)
from financial_disclosure_review.domain.explanation_duty_check.schema import (
    ExplanationJudgments,
    FidelityDiffs,
    PlainJudgments,
)
from financial_disclosure_review.knowledge.build import build_rubric_db
from tests.helpers import FIXTURE_DIR

CLASSIFICATION = {"product_type": "신용카드", "page_type": "상품광고", "reason": "테스트"}
PAGE = {
    "html": """
<html><body>
<p>본 상품은 신한카드가 발행하는 신용카드입니다.</p>
<p>금리는 연 15%이며 변동금리입니다. 중도상환수수료는 없습니다.</p>
<p>일시불 이용시 이자가 없으며, 할부 이용시 수수료율은 정확히 15%입니다.</p>
<p>연회비는 1만원이며 최대 5% 할인 혜택을 제공합니다.</p>
</body></html>
"""
}
PLAIN_1 = {
    "html": """
<html><body>
<p>이 카드는 신한카드의 신용카드예요.</p>
<p>금리는 연 15%입니다.</p>
<p>할부 수수료율은 최대 15%입니다.</p>
<p>언제든 위약금 없이 해지할 수 있습니다.</p>
</body></html>
"""
}
PLAIN_2 = {
    "html": """
<html><body>
<p>이 카드는 신한카드의 신용카드예요.</p>
<p>금리는 연 15%이고 변동금리이며 중도상환수수료는 없어요.</p>
<p>할부 수수료율은 15%예요.</p>
</body></html>
"""
}


class FakeExplanationAsk:
    """공통 계약을 따르는 가짜 ask. data['items']로 넘어온 코드에 맞춰 기본값(판정 불가/조건
    불명확/변화없음)을 채우고, overrides로 지정한 코드만 원하는 답으로 바꾼다."""

    def __init__(self, original=None, plain=None, fidelity=None):
        self.original = original or {}
        self.plain = plain or {}
        self.fidelity = fidelity or {}
        self.calls: list[str] = []
        self.sent: list[tuple[str, dict]] = []

    def __call__(self, model, schema, task, effort="low", **data):
        self.calls.append(schema.__name__)
        self.sent.append((schema.__name__, data))
        if schema is ExplanationJudgments:
            return {"items": [self._original_row(item) for item in data["items"]]}
        if schema is PlainJudgments:
            return {
                "items": [
                    {"code": item["code"], **self.plain[item["code"]]}
                    if item["code"] in self.plain
                    else {
                        "code": item["code"],
                        "verdict": "판정 불가",
                        "quote": "",
                        "reason": "테스트 기본값",
                    }
                    for item in data["items"]
                ]
            }
        if schema is FidelityDiffs:
            return {
                "items": [
                    {"code": item["code"], **self.fidelity[item["code"]]}
                    if item["code"] in self.fidelity
                    else {"code": item["code"], "kind": "변화없음", "reason": "테스트 기본값"}
                    for item in data["items"]
                ]
            }
        raise AssertionError(f"unexpected schema {schema}")

    def _original_row(self, item: dict) -> dict:
        code = item["code"]
        if code in self.original:
            return {"code": code, **self.original[code]}
        if item["applies_condition"]:
            return {
                "code": code,
                "condition_status": "불명확",
                "verdict": "판정 불가",
                "quote": "",
                "reason": "테스트 기본값: 조건 불명확으로 둠",
            }
        return {
            "code": code,
            "condition_status": "해당없음",
            "verdict": "판정 불가",
            "quote": "",
            "reason": "테스트 기본값: 판정 불가로 둠",
        }


FIRST_ROUND_ASK = dict(
    original={
        "설명01": {
            "condition_status": "해당없음",
            "verdict": "적합",
            "quote": "금리는 연 15%이며 변동금리입니다. 중도상환수수료는 없습니다.",
            "reason": "금리·변동여부·중도상환수수료가 모두 있음",
        },
        "설명02": {
            "condition_status": "해당없음",
            "verdict": "적합",
            "quote": "일시불 이용시 이자가 없으며, 할부 이용시 수수료율은 정확히 15%입니다.",
            "reason": "상환방법별 금액·이자율이 있음",
        },
        "설명05": {
            "condition_status": "해당없음",
            "verdict": "부적합",
            "quote": "",
            "reason": "계약 해지·해제에 관한 내용이 없음",
        },
        "설명10": {
            "condition_status": "불명확",
            "verdict": "판정 불가",
            "quote": "",
            "reason": "페이지에 리볼빙 제공·권유 여부가 언급되지 않아 조건 성립을 알 수 없음",
        },
    },
    plain={
        "설명01": {
            "verdict": "부적합",
            "quote": "",
            "reason": "변동 여부와 중도상환수수료 언급이 빠짐",
        },
        "설명02": {
            "verdict": "적합",
            "quote": "할부 수수료율은 최대 15%입니다.",
            "reason": "할부 수수료율이 있음",
        },
        "설명05": {
            "verdict": "적합",
            "quote": "언제든 위약금 없이 해지할 수 있습니다.",
            "reason": "해지 방법을 설명함",
        },
    },
    fidelity={
        "설명01": {"kind": "누락", "reason": "변동 여부·중도상환수수료 언급이 쉬운말에서 빠짐"},
        "설명02": {"kind": "변경", "reason": "확정 표현 15%가 최대라는 가능성 표현으로 바뀜"},
        "설명05": {
            "kind": "추가",
            "reason": "원문에 없던 해지 조건을 쉬운말이 새로 채움; 원문 결함 해결로 보지 않음",
        },
    },
)


@pytest.fixture(scope="module")
def ctx(tmp_path_factory) -> Context:
    path = tmp_path_factory.mktemp("reference") / "reference.sqlite"
    build_rubric_db(FIXTURE_DIR / "rubric", path)
    return Context(model="fake", db_path=str(path))


@pytest.fixture(scope="module")
def first_round(ctx) -> dict:
    ask = FakeExplanationAsk(**FIRST_ROUND_ASK)
    result = judge_explanation(PAGE, PLAIN_1, CLASSIFICATION, ctx, None, None, ask=ask)
    return {"result": result, "ask": ask}


@pytest.fixture(scope="module")
def rows(first_round) -> dict:
    result = first_round["result"]
    return {
        "items": {row["code"]: row for row in result["items"]},
        "original": {row["code"]: row for row in result["original"]},
        "plain": {row["code"]: row for row in result["plain"]},
        "fidelity": {row["code"]: row for row in result["fidelity"]},
    }


def test_every_rubric_item_is_reported_exactly_once(ctx, first_round):
    all_items = load_explanation_items(ctx.db_path)
    assert len(first_round["result"]["items"]) == len(all_items)


@pytest.mark.parametrize("code", ["설명19", "F19"])
def test_an_application_screen_condition_is_ruled_out_without_a_model_call(code, rows):
    assert rows["items"][code]["applied"] is False
    assert any(
        marker in rows["items"][code]["reason"]
        for marker in ("신청 화면", "가입 화면", "발급 화면")
    )
    assert code not in rows["original"] and code not in rows["plain"]


@pytest.mark.parametrize("code", ["설명03", "F03"])
def test_another_products_item_is_ruled_out_too(code, rows):
    assert rows["items"][code]["applied"] is False
    assert "applies_to" in rows["items"][code]["reason"]
    assert code not in rows["original"]


def test_an_unclear_condition_stays_unjudged_and_is_reused_on_the_plain_side(rows):
    assert rows["items"]["설명10"]["applied"] is True
    assert rows["items"]["설명10"]["condition_status"] == "불명확"
    assert rows["original"]["설명10"]["verdict"] == "판정 불가"
    assert rows["original"]["설명10"]["quote"] == ""
    assert rows["plain"]["설명10"] == rows["original"]["설명10"]
    assert "설명10" not in rows["fidelity"]


def test_something_the_plain_text_dropped_is_a_missing_diff(rows):
    assert rows["original"]["설명01"]["verdict"] == "적합"
    assert locate_quote(visible_text(PAGE["html"]), rows["original"]["설명01"]["quote"]) is not None
    assert rows["plain"]["설명01"]["verdict"] == "부적합"
    assert rows["fidelity"]["설명01"]["kind"] == "누락"


def test_a_changed_number_or_hedge_is_a_changed_diff(rows):
    assert rows["fidelity"]["설명02"]["kind"] == "변경"
    assert locate_quote(visible_text(PLAIN_1["html"]), rows["plain"]["설명02"]["quote"]) is not None


def test_the_plain_text_filling_an_original_gap_is_an_added_diff_not_a_fix(rows):
    assert rows["original"]["설명05"]["verdict"] == "부적합"
    assert rows["plain"]["설명05"]["verdict"] == "적합"
    assert rows["fidelity"]["설명05"]["kind"] == "추가"


def test_an_item_both_sides_judged_the_same_way_is_not_in_fidelity(rows):
    untouched = [c for c in rows["original"] if c not in ("설명01", "설명02", "설명05", "설명10")]
    assert untouched
    assert untouched[0] not in rows["fidelity"]


def test_a_retry_reuses_the_original_side_and_recomputes_only_the_plain_side(
    ctx, first_round, rows
):
    previous = first_round["result"]
    ask = FakeExplanationAsk(
        plain={
            "설명01": {
                "verdict": "적합",
                "quote": "금리는 연 15%이고 변동금리이며 중도상환수수료는 없어요.",
                "reason": "금리·변동여부·중도상환수수료가 모두 있음",
            },
            "설명02": {
                "verdict": "적합",
                "quote": "할부 수수료율은 15%예요.",
                "reason": "상환방법별 수수료율이 있음",
            },
        },
        fidelity={
            "설명05": {
                "kind": "판정 불가",
                "reason": "이번 회차 쉬운말 판정이 기본값이라 비교 근거 부족",
            }
        },
    )
    result = judge_explanation(
        PAGE, PLAIN_2, CLASSIFICATION, ctx, previous["original"], previous["items"], ask=ask
    )

    assert result["items"] == previous["items"]
    assert result["original"] == previous["original"]
    assert "ExplanationJudgments" not in ask.calls, (
        "재시도에서는 원문 판정을 다시 호출하지 않아야 함"
    )
    assert "PlainJudgments" in ask.calls

    plain_rows = {row["code"]: row for row in result["plain"]}
    fidelity_rows = {row["code"]: row for row in result["fidelity"]}
    assert plain_rows["설명01"]["verdict"] == "적합"
    assert "설명01" not in fidelity_rows
    assert fidelity_rows["설명05"]["kind"] == "판정 불가"
    assert plain_rows["설명10"] == rows["original"]["설명10"], (
        "조건 불명확 항목은 재시도에서도 재호출 없이 그대로 재사용"
    )
    assert result["plain"] != previous["plain"]


QUOTE_REQUEST = {
    "module": "explanation_duty_check",
    "code": "설명02",
    "source_id": "",
    "reason": (
        "explanation_duty_check.original 설명02: 인용문이 product_page.html에서 발견되지 않습니다"
    ),
    "requested_change": "product_page.html에 실제로 있는 문구로 다시 인용하세요",
    "target": "original",
}


def test_a_first_round_sends_no_feedback_field(first_round):
    """Recorded first-round calls are keyed by what was sent; a new empty field would orphan
    every cassette entry."""
    assert all("previous_feedback" not in data for _, data in first_round["ask"].sent)


def test_a_retry_re_judges_only_the_flagged_original_code_and_tells_the_model_why(ctx, first_round):
    previous = first_round["result"]
    fixed_quote = "일시불 이용시 이자가 없으며, 할부 이용시 수수료율은 정확히 15%입니다."
    ask = FakeExplanationAsk(
        original={
            "설명02": {
                "condition_status": "해당없음",
                "verdict": "적합",
                "quote": fixed_quote,
                "reason": "상환방법별 금액·이자율이 있음(다시 인용)",
            }
        }
    )
    unrelated = {**QUOTE_REQUEST, "module": "plain_language", "code": "설명05"}
    result = judge_explanation(
        PAGE,
        PLAIN_1,
        CLASSIFICATION,
        ctx,
        previous["original"],
        previous["items"],
        ask=ask,
        feedback=[QUOTE_REQUEST, unrelated],
    )

    original_calls = [data for name, data in ask.sent if name == "ExplanationJudgments"]
    assert len(original_calls) == 1
    assert [item["code"] for item in original_calls[0]["items"]] == ["설명02"]
    assert original_calls[0]["previous_feedback"] == [
        {
            "code": "설명02",
            "reason": QUOTE_REQUEST["reason"],
            "requested_change": QUOTE_REQUEST["requested_change"],
        }
    ]
    by_code = {row["code"]: row for row in result["original"]}
    assert by_code["설명02"]["reason"].endswith("(다시 인용)")
    untouched = [row for row in previous["original"] if row["code"] != "설명02"]
    assert all(by_code[row["code"]] == row for row in untouched)
    assert [row["code"] for row in result["items"]] == [row["code"] for row in previous["items"]]


def test_plain_side_feedback_reaches_the_plain_judgment_only(ctx, first_round):
    previous = first_round["result"]
    request = {
        **QUOTE_REQUEST,
        "code": "설명01",
        "target": "plain",
        "requested_change": "plain_language.html에 실제로 있는 문구로 다시 인용하세요",
    }
    ask = FakeExplanationAsk()
    judge_explanation(
        PAGE,
        PLAIN_2,
        CLASSIFICATION,
        ctx,
        previous["original"],
        previous["items"],
        ask=ask,
        feedback=[request],
    )

    assert "ExplanationJudgments" not in ask.calls, "원문 쪽 지적이 없으면 원문은 다시 묻지 않음"
    plain_calls = [data for name, data in ask.sent if name == "PlainJudgments"]
    assert plain_calls and plain_calls[0]["previous_feedback"][0]["code"] == "설명01"
