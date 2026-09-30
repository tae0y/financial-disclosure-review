"""judge_disclosure with the model faked: what code rules out, what the model decides, what the
retry path is allowed to recompute, and which explanation-duty items are only listed."""

from pathlib import Path

import pytest

from financial_disclosure_review.core.context import Context
from financial_disclosure_review.core.text import locate_quote, visible_text
from financial_disclosure_review.domain.ad_disclosure_check.check import (
    judge_disclosure,
    judge_original,
)
from financial_disclosure_review.domain.ad_disclosure_check.rubric import load_disclosure_items
from financial_disclosure_review.domain.ad_disclosure_check.schema import DisclosureJudgments
from financial_disclosure_review.knowledge.build import build_rubric_db

ASSETS = Path(__file__).resolve().parents[3] / "assets"
CLASSIFICATION = {"product_type": "신용카드", "page_type": "상품광고", "reason": "테스트"}
PAGE = {
    "html": """
<html><body>
<p>본 상품은 신한카드가 발행하는 신용카드입니다.</p>
<p>연회비는 국내전용 1만원, 해외겸용 1만2천원입니다.</p>
<p>할부 이용시 수수료율은 연 15%이며 연체이자율은 최고 연 19.9%입니다.</p>
<p>전월 이용실적 30만원 이상 시 커피 10% 할인</p>
</body></html>
"""
}


class FakeDisclosureAsk:
    """공통 계약을 따르는 가짜 ask. data['items']로 넘어온 코드에 맞춰 기본값(판정 불가/조건
    불명확)을 채우고, overrides로 지정한 코드만 원하는 답으로 바꾼다."""

    def __init__(self, original=None):
        self.original = original or {}
        self.calls: list[str] = []
        self.sent: list[tuple[str, dict]] = []

    def __call__(self, model, schema, task, effort="low", **data):
        self.calls.append(schema.__name__)
        self.sent.append((schema.__name__, data))
        if schema is DisclosureJudgments:
            return {"items": [self._original_row(item) for item in data["items"]]}
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


FIRST_ROUND = {
    "C01": {
        "condition_status": "해당없음",
        "verdict": "적합",
        "quote": "연회비는 국내전용 1만원, 해외겸용 1만2천원입니다.",
        "reason": "연회비를 국내전용·해외겸용으로 구분해 표시함",
    },
    "A04": {
        "condition_status": "성립",
        "verdict": "적합",
        "quote": "할부 이용시 수수료율은 연 15%이며 연체이자율은 최고 연 19.9%입니다.",
        "reason": "상품광고라 적용되고 이자율·연체이자율이 있음",
    },
    "A11": {
        "condition_status": "해당없음",
        "verdict": "부적합",
        "quote": "",
        "reason": "신용평점 하락 경고문구가 없음",
    },
    "A10": {
        "condition_status": "불명확",
        "verdict": "판정 불가",
        "quote": "",
        "reason": "부가서비스를 광고하는지 이 테스트에서는 불명확으로 둠",
    },
}


@pytest.fixture(scope="module")
def ctx(tmp_path_factory) -> Context:
    path = tmp_path_factory.mktemp("reference") / "reference.sqlite"
    build_rubric_db(ASSETS, path)
    return Context(model="fake", db_path=str(path))


@pytest.fixture(scope="module")
def first_round(ctx) -> dict:
    ask = FakeDisclosureAsk(FIRST_ROUND)
    result = judge_disclosure(PAGE, CLASSIFICATION, ctx, None, None, ask=ask)
    return {"result": result, "ask": ask}


@pytest.fixture(scope="module")
def rows(first_round) -> dict:
    result = first_round["result"]
    return {
        "items": {row["code"]: row for row in result["items"]},
        "original": {row["code"]: row for row in result["original"]},
    }


def test_the_judged_items_are_the_mandatory_ad_disclosures_only(ctx, first_round):
    items = load_disclosure_items(ctx.db_path)
    assert {item["group"][0] for item in items} == {"A", "B", "C"}
    assert len(first_round["result"]["items"]) == len(items)
    judged = [data for name, data in first_round["ask"].sent if name == "DisclosureJudgments"]
    assert len(judged) == 1
    sent_codes = {item["code"] for item in judged[0]["items"]}
    assert not any(code.startswith(("설명", "F")) for code in sent_codes)
    assert set(first_round["result"]) == {"items", "original", "deferred"}


@pytest.mark.parametrize("code", ["C03", "C05", "C06"])
def test_another_products_disclosure_is_ruled_out_without_a_model_call(code, rows):
    assert rows["items"][code]["applied"] is False
    assert "applies_to" in rows["items"][code]["reason"]
    assert code not in rows["original"]


def test_explanation_duty_items_are_listed_for_the_product_documents_not_judged(first_round):
    deferred = {row["code"]: row for row in first_round["result"]["deferred"]}
    assert "설명11" in deferred and deferred["설명11"]["question"].endswith("?")
    # 신용카드에는 중도상환수수료가 없으므로 설명01은 신용카드 확인 목록에 없다.
    assert "설명01" not in deferred
    # 청약철회는 신용카드에도 걸리는 의무라 목록에 남는다.
    assert "설명16" in deferred
    assert not any(code.startswith("F") for code in deferred)
    # 신청·발급 화면에서만 성립하는 항목은 상품설명서 확인 목록에 넣지 않는다.
    assert not {"설명19", "설명25", "설명26", "설명27", "설명28"} & set(deferred)


def test_an_unclear_condition_stays_unjudged(rows):
    assert rows["items"]["A10"]["applied"] is True
    assert rows["items"]["A10"]["condition_status"] == "불명확"
    assert rows["original"]["A10"]["verdict"] == "판정 불가"
    assert rows["original"]["A10"]["quote"] == ""


def test_a_pass_cites_the_page_and_a_missing_disclosure_cites_nothing(rows):
    assert locate_quote(visible_text(PAGE["html"]), rows["original"]["C01"]["quote"]) is not None
    assert rows["original"]["A11"]["verdict"] == "부적합" and rows["original"]["A11"]["quote"] == ""


QUOTE_REQUEST = {
    "module": "ad_disclosure_check",
    "code": "A04",
    "source_id": "",
    "reason": "ad_disclosure_check A04: 인용문이 product_page.html에서 발견되지 않습니다",
    "requested_change": "product_page.html에 실제로 있는 문구로 다시 인용하세요",
    "target": "original",
}


def test_a_first_round_sends_no_feedback_field(first_round):
    """Recorded first-round calls are keyed by what was sent; a new empty field would orphan
    every cassette entry."""
    assert all("previous_feedback" not in data for _, data in first_round["ask"].sent)


def test_a_retry_re_judges_only_the_flagged_code_and_tells_the_model_why(ctx, first_round):
    previous = first_round["result"]
    fixed_quote = "할부 이용시 수수료율은 연 15%이며 연체이자율은 최고 연 19.9%입니다."
    ask = FakeDisclosureAsk(
        {
            "A04": {
                "condition_status": "성립",
                "verdict": "적합",
                "quote": fixed_quote,
                "reason": "이자율이 있음(다시 인용)",
            }
        }
    )
    unrelated = {**QUOTE_REQUEST, "module": "persona_explanation", "code": "C01"}
    result = judge_disclosure(
        PAGE,
        CLASSIFICATION,
        ctx,
        previous["original"],
        previous["items"],
        ask=ask,
        feedback=[QUOTE_REQUEST, unrelated],
    )

    calls = [data for name, data in ask.sent if name == "DisclosureJudgments"]
    assert len(calls) == 1
    assert [item["code"] for item in calls[0]["items"]] == ["A04"]
    assert calls[0]["previous_feedback"] == [
        {
            "code": "A04",
            "reason": QUOTE_REQUEST["reason"],
            "requested_change": QUOTE_REQUEST["requested_change"],
        }
    ]
    by_code = {row["code"]: row for row in result["original"]}
    assert by_code["A04"]["reason"].endswith("(다시 인용)")
    untouched = [row for row in previous["original"] if row["code"] != "A04"]
    assert all(by_code[row["code"]] == row for row in untouched)
    assert [row["code"] for row in result["items"]] == [row["code"] for row in previous["items"]]
    assert "deferred" not in result, "확인 목록은 첫 회차 값을 State에 그대로 둔다"


def test_a_retry_with_nothing_flagged_makes_no_call(ctx, first_round):
    previous = first_round["result"]
    ask = FakeDisclosureAsk()
    result = judge_disclosure(
        PAGE, CLASSIFICATION, ctx, previous["original"], previous["items"], ask=ask
    )
    assert ask.calls == []
    assert result == {"items": previous["items"], "original": previous["original"]}


def test_the_first_round_is_judge_original(ctx, first_round):
    ask = FakeDisclosureAsk(FIRST_ROUND)
    assert judge_original(PAGE, CLASSIFICATION, ctx, ask=ask) == first_round["result"]
