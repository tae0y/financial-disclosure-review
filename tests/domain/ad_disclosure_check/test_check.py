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
from financial_disclosure_review.domain.ad_disclosure_check.rubric import (
    OVERVIEW_REQUIRED,
    load_disclosure_items,
)
from financial_disclosure_review.domain.ad_disclosure_check.schema import (
    DisclosureJudgments,
    FidelityDiffs,
    OverviewJudgments,
)
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
OVERVIEW_1 = {
    "html": """<section data-role="overview">
<p>이 카드는 신한카드의 신용카드예요. 할부 수수료율은 최대 연 15%예요.</p>
<p>상환능력에 비해 카드를 많이 쓰면 개인신용평점이 떨어질 수 있어요.</p>
</section>"""
}
OVERVIEW_2 = {
    "html": """<section data-role="overview">
<p>이 카드는 신한카드의 신용카드예요. 연회비는 국내전용 1만원, 해외겸용 1만2천원이에요.</p>
<p>할부 수수료율은 연 15%예요.</p>
</section>"""
}


class FakeDisclosureAsk:
    """공통 계약을 따르는 가짜 ask. data['items']로 넘어온 코드에 맞춰 기본값(판정 불가/조건
    불명확/변화없음)을 채우고, overrides로 지정한 코드만 원하는 답으로 바꾼다."""

    def __init__(self, original=None, overview=None, fidelity=None):
        self.original = original or {}
        self.overview = overview or {}
        self.fidelity = fidelity or {}
        self.calls: list[str] = []
        self.sent: list[tuple[str, dict]] = []

    def __call__(self, model, schema, task, effort="low", **data):
        self.calls.append(schema.__name__)
        self.sent.append((schema.__name__, data))
        if schema is DisclosureJudgments:
            return {"items": [self._original_row(item) for item in data["items"]]}
        if schema is OverviewJudgments:
            return {
                "items": [
                    {"code": item["code"], **self.overview[item["code"]]}
                    if item["code"] in self.overview
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
    },
    overview={
        "C01": {"verdict": "부적합", "quote": "", "reason": "연회비 언급이 없음"},
        "A04": {
            "verdict": "적합",
            "quote": "할부 수수료율은 최대 연 15%예요.",
            "reason": "할부 수수료율이 있음",
        },
        "A11": {
            "verdict": "적합",
            "quote": "상환능력에 비해 카드를 많이 쓰면 개인신용평점이 떨어질 수 있어요.",
            "reason": "경고문구가 있음",
        },
    },
    fidelity={
        "C01": {"kind": "누락", "reason": "연회비가 개요에서 빠짐"},
        "A04": {"kind": "변경", "reason": "확정 표현 연 15%가 최대라는 가능성 표현으로 바뀜"},
        "A11": {
            "kind": "추가",
            "reason": "원문에 없던 경고문구를 개요가 새로 채움; 원문 결함 해결로 보지 않음",
        },
    },
)


@pytest.fixture(scope="module")
def ctx(tmp_path_factory) -> Context:
    path = tmp_path_factory.mktemp("reference") / "reference.sqlite"
    build_rubric_db(ASSETS, path)
    return Context(model="fake", db_path=str(path))


@pytest.fixture(scope="module")
def first_round(ctx) -> dict:
    ask = FakeDisclosureAsk(**FIRST_ROUND_ASK)
    result = judge_disclosure(PAGE, OVERVIEW_1, CLASSIFICATION, ctx, None, None, ask=ask)
    return {"result": result, "ask": ask}


@pytest.fixture(scope="module")
def rows(first_round) -> dict:
    result = first_round["result"]
    return {
        "items": {row["code"]: row for row in result["items"]},
        "original": {row["code"]: row for row in result["original"]},
        "overview": {row["code"]: row for row in result["overview"]},
        "fidelity": {row["code"]: row for row in result["fidelity"]},
    }


def test_the_judged_items_are_the_mandatory_ad_disclosures_only(ctx, first_round):
    items = load_disclosure_items(ctx.db_path)
    assert {item["group"][0] for item in items} == {"A", "B", "C"}
    assert len(first_round["result"]["items"]) == len(items)
    judged = [data for name, data in first_round["ask"].sent if name == "DisclosureJudgments"]
    assert len(judged) == 1
    sent_codes = {item["code"] for item in judged[0]["items"]}
    assert not any(code.startswith(("설명", "F")) for code in sent_codes)


@pytest.mark.parametrize("code", ["C03", "C05", "C06"])
def test_another_products_disclosure_is_ruled_out_without_a_model_call(code, rows):
    assert rows["items"][code]["applied"] is False
    assert "applies_to" in rows["items"][code]["reason"]
    assert code not in rows["original"] and code not in rows["overview"]


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


def test_an_unclear_condition_stays_unjudged_and_is_reused_on_the_overview_side(rows):
    assert rows["items"]["A10"]["applied"] is True
    assert rows["items"]["A10"]["condition_status"] == "불명확"
    assert rows["original"]["A10"]["verdict"] == "판정 불가"
    assert rows["overview"]["A10"] == rows["original"]["A10"]
    assert "A10" not in rows["fidelity"]


def test_something_the_overview_dropped_is_a_missing_diff_that_can_be_retried(rows):
    assert rows["original"]["C01"]["verdict"] == "적합"
    assert locate_quote(visible_text(PAGE["html"]), rows["original"]["C01"]["quote"]) is not None
    assert rows["overview"]["C01"]["verdict"] == "부적합"
    assert rows["fidelity"]["C01"]["kind"] == "누락"
    assert rows["fidelity"]["C01"]["informational"] is False


def test_a_changed_number_or_hedge_is_a_changed_diff(rows):
    assert rows["fidelity"]["A04"]["kind"] == "변경"
    overview_text = visible_text(OVERVIEW_1["html"])
    assert locate_quote(overview_text, rows["overview"]["A04"]["quote"]) is not None


def test_the_overview_filling_an_original_gap_is_an_added_diff_not_a_fix(rows):
    assert rows["original"]["A11"]["verdict"] == "부적합"
    assert rows["overview"]["A11"]["verdict"] == "적합"
    assert rows["fidelity"]["A11"]["kind"] == "추가"


def test_a_retry_reuses_the_original_side_and_recomputes_only_the_overview_side(
    ctx, first_round, rows
):
    previous = first_round["result"]
    ask = FakeDisclosureAsk(
        overview={
            "C01": {
                "verdict": "적합",
                "quote": "연회비는 국내전용 1만원, 해외겸용 1만2천원이에요.",
                "reason": "연회비가 있음",
            },
        },
        fidelity={"A11": {"kind": "판정 불가", "reason": "이번 회차 개요 판정이 기본값"}},
    )
    result = judge_disclosure(
        PAGE, OVERVIEW_2, CLASSIFICATION, ctx, previous["original"], previous["items"], ask=ask
    )

    assert result["items"] == previous["items"]
    assert result["original"] == previous["original"]
    assert "DisclosureJudgments" not in ask.calls, "재시도에서 원문 판정을 다시 부르면 안 됨"
    assert "OverviewJudgments" in ask.calls
    assert "deferred" not in result, "확인 목록은 첫 회차 값을 State에 그대로 둔다"

    overview_rows = {row["code"]: row for row in result["overview"]}
    fidelity_rows = {row["code"]: row for row in result["fidelity"]}
    assert overview_rows["C01"]["verdict"] == "적합"
    assert "C01" not in fidelity_rows
    assert fidelity_rows["A11"]["kind"] == "판정 불가"
    assert fidelity_rows["A11"]["informational"] is True
    assert overview_rows["A10"] == rows["original"]["A10"]


QUOTE_REQUEST = {
    "module": "ad_disclosure_check",
    "code": "A04",
    "source_id": "",
    "reason": "ad_disclosure_check.original A04: 인용문이 product_page.html에서 발견되지 않습니다",
    "requested_change": "product_page.html에 실제로 있는 문구로 다시 인용하세요",
    "target": "original",
}


def test_a_first_round_sends_no_feedback_field(first_round):
    """Recorded first-round calls are keyed by what was sent; a new empty field would orphan
    every cassette entry."""
    assert all("previous_feedback" not in data for _, data in first_round["ask"].sent)


def test_a_retry_re_judges_only_the_flagged_original_code_and_tells_the_model_why(ctx, first_round):
    previous = first_round["result"]
    fixed_quote = "할부 이용시 수수료율은 연 15%이며 연체이자율은 최고 연 19.9%입니다."
    ask = FakeDisclosureAsk(
        original={
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
        OVERVIEW_1,
        CLASSIFICATION,
        ctx,
        previous["original"],
        previous["items"],
        ask=ask,
        feedback=[QUOTE_REQUEST, unrelated],
    )

    original_calls = [data for name, data in ask.sent if name == "DisclosureJudgments"]
    assert len(original_calls) == 1
    assert [item["code"] for item in original_calls[0]["items"]] == ["A04"]
    assert original_calls[0]["previous_feedback"] == [
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


def test_overview_side_feedback_reaches_the_overview_judgment_only(ctx, first_round):
    previous = first_round["result"]
    request = {
        **QUOTE_REQUEST,
        "code": "C01",
        "target": "overview",
        "requested_change": "persona_explanation.html에 실제로 있는 문구로 다시 인용하세요",
    }
    ask = FakeDisclosureAsk()
    judge_disclosure(
        PAGE,
        OVERVIEW_2,
        CLASSIFICATION,
        ctx,
        previous["original"],
        previous["items"],
        ask=ask,
        feedback=[request],
    )

    assert "DisclosureJudgments" not in ask.calls, "원문 쪽 지적이 없으면 원문은 다시 묻지 않음"
    overview_calls = [data for name, data in ask.sent if name == "OverviewJudgments"]
    assert overview_calls and overview_calls[0]["previous_feedback"][0]["code"] == "C01"


def test_the_original_side_alone_matches_the_first_round(ctx, first_round):
    """judge_original runs beside the persona overview; its rows are the first round's."""
    ask = FakeDisclosureAsk(**FIRST_ROUND_ASK)
    alone = judge_original(PAGE, CLASSIFICATION, ctx, ask=ask)
    assert alone == {
        "items": first_round["result"]["items"],
        "original": first_round["result"]["original"],
        "deferred": first_round["result"]["deferred"],
    }
    assert set(ask.calls) == {"DisclosureJudgments"}


def test_an_empty_original_side_from_judge_original_is_not_judged_again(ctx, first_round):
    items = [{**row, "applied": False} for row in first_round["result"]["items"]]
    ask = FakeDisclosureAsk()
    judge_disclosure(PAGE, OVERVIEW_1, CLASSIFICATION, ctx, [], items, ask=ask)
    assert "DisclosureJudgments" not in ask.calls


def test_the_overview_is_asked_only_for_what_it_must_carry(first_round):
    """페이지 정보(심의필 번호, 회사명 등)는 옆의 원문에 남으므로 개요에 요구하지 않는다."""
    sent = [data for name, data in first_round["ask"].sent if name == "OverviewJudgments"]
    codes = {item["code"] for item in sent[0]["items"]}
    assert codes <= OVERVIEW_REQUIRED
    assert not codes & {"A01", "A02", "A03", "A06", "A07", "A08", "B01"}
    overview_codes = {row["code"] for row in first_round["result"]["overview"]}
    assert "A07" not in overview_codes and "A04" in overview_codes


def test_the_difference_is_judged_against_the_criterion(first_round):
    sent = [data for name, data in first_round["ask"].sent if name == "FidelityDiffs"]
    by_code = {item["code"]: item for item in sent[0]["items"]}
    assert "연회비" in by_code["C01"]["criterion"]


def test_lost_detail_on_an_item_the_overview_still_carries_is_informational(ctx, first_round):
    """개요가 연회비를 담았지만 세부(기본·제휴 구분)가 줄었다는 누락은 재작성 사유가 아니다."""
    previous = first_round["result"]
    ask = FakeDisclosureAsk(
        overview={
            "C01": {
                "verdict": "적합",
                "quote": "연회비는 국내전용 1만원, 해외겸용 1만2천원이에요.",
                "reason": "연회비가 있음",
            }
        },
        fidelity={"C01": {"kind": "누락", "reason": "구성 내역이 줄었음"}},
    )
    result = judge_disclosure(
        PAGE, OVERVIEW_2, CLASSIFICATION, ctx, previous["original"], previous["items"], ask=ask
    )
    row = next(r for r in result["fidelity"] if r["code"] == "C01")
    assert row["informational"] is True
