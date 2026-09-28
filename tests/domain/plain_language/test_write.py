"""generate_plain with the model faked: every block it keeps has to survive the contract checks."""

from html import escape

import pytest

from financial_disclosure_review.core.context import Context
from financial_disclosure_review.core.text import locate_quote, visible_text
from financial_disclosure_review.domain.plain_language.blocks import plain_blocks
from financial_disclosure_review.domain.plain_language.contract import (
    verify_source_quote,
    verify_terms,
)
from financial_disclosure_review.domain.plain_language.write import generate_plain
from financial_disclosure_review.knowledge.build import build_rubric_db
from tests.helpers import FIXTURE_DIR

# plain_blocks splits at block elements and at newlines, so each line here is one block.
FIXTURE_LINES = (
    "연회비는 국내전용 1만원입니다.",
    "연 이자율은 최저 연 15%에서 최대 연 20%까지 적용되며,"
    " 신용도 심사 결과에 따라 달라질 수 있습니다.",
    "전월 실적 30만원 이상 이용 시에만 5% 할인이 적용되며, 일부 가맹점은 할인 대상에서 제외됩니다.",
    "연체 시 최대 연 20% 연체이자가 부과되며, 신용점수가 하락할 수 있습니다.",
    "계약을 체결하기 전에 금융상품 설명서와 약관을 확인하시기 바랍니다.",
)
FIXTURE_HTML = (
    "<html><body><h1>초록카드 신용카드</h1>"
    + "".join(f"<p>{line}</p>" for line in FIXTURE_LINES)
    + "</body></html>"
)
INVENTED_RATE = (
    "연 이자율은 최저 연 15%에서 최대 연 30%까지 적용되며, 심사 결과에 따라 달라질 수 있습니다."
)
CLASSIFICATION = {"product_type": "신용카드", "page_type": "상품광고", "reason": "확인용"}
PAGE = {
    "url": "https://example.test/card",
    "product": {"product_name": "초록카드"},
    "html": FIXTURE_HTML,
}


@pytest.fixture(scope="module")
def ctx(tmp_path_factory) -> Context:
    path = tmp_path_factory.mktemp("reference") / "reference.sqlite"
    build_rubric_db(FIXTURE_DIR / "rubric", path)
    return Context(model="fake", db_path=str(path))


@pytest.fixture(scope="module")
def blocks() -> list[dict]:
    rows = plain_blocks(FIXTURE_HTML)
    assert len(rows) == 6, rows
    return rows


@pytest.fixture(scope="module")
def block_ids(blocks) -> dict[str, str]:
    return {
        "rate": next(b["id"] for b in blocks if "이자율" in b["quote"]),
        "discount": next(b["id"] for b in blocks if "할인" in b["quote"]),
        "fee": next(b["id"] for b in blocks if "연회비" in b["quote"]),
    }


def quote_of(blocks: list[dict], block_id: str) -> str:
    return next(b["quote"] for b in blocks if b["id"] == block_id)


def fake_ask(
    overrides: dict | None = None, terms: dict | None = None, conditions: dict | None = None
):
    """블록별 quote를 그대로 되돌려 주는 기본 가짜 ask. overrides[id]로 특정 블록 답을 바꾸고,
    conditions[id]로 조건 보존 판정(기본 유지)을 바꾼다."""
    overrides, terms, conditions = overrides or {}, terms or {}, conditions or {}

    def fake(model, schema, task, effort="low", **data):
        if "blocks" in data:
            return {
                "items": [
                    {
                        "id": b["id"],
                        "text": overrides.get(b["id"], b["quote"]),
                        "terms": terms.get(b["id"], []),
                    }
                    for b in data["blocks"]
                ]
            }
        return {
            "items": [
                {
                    "id": e["id"],
                    "verdict": conditions.get(e["id"], "유지"),
                    "reason": "테스트 판정",
                }
                for e in data["items"]
            ]
        }

    return fake


def errors_of(result: dict) -> dict[str, str]:
    return {e["source_id"]: e["reason"] for e in result["contract_errors"]}


def test_a_faithful_rewrite_keeps_every_block(ctx, blocks):
    result = generate_plain(PAGE, CLASSIFICATION, [], ctx, ask=fake_ask())

    assert len(result["accepted_blocks"]) == 6, result["accepted_blocks"]
    assert result["contract_errors"] == []
    assert len(result["draft"]) == 6
    page_text = visible_text(FIXTURE_HTML)
    for block in result["accepted_blocks"]:
        assert locate_quote(page_text, block["source_quote"]) is not None
    assert any(row["code"] == "쉬운말02" and row["verdict"] == "적용" for row in result["items"])


def test_a_number_the_original_never_had_sends_that_block_back_to_the_original(
    ctx, blocks, block_ids
):
    rate = block_ids["rate"]
    fake = fake_ask({rate: INVENTED_RATE})
    result = generate_plain(PAGE, CLASSIFICATION, [], ctx, ask=fake)

    errors = errors_of(result)
    assert rate in errors and "수치" in errors[rate], errors
    assert rate not in {b["source_id"] for b in result["accepted_blocks"]}
    kept = escape(quote_of(blocks, rate))
    assert f'<p data-source-id="{rate}">{kept}</p>' in result["html"]


def test_dropping_the_original_conditions_is_rejected(ctx, block_ids):
    discount = block_ids["discount"]
    fake = fake_ask({discount: "전월 실적과 관계없이 모든 가맹점에서 5% 할인이 적용됩니다."})
    result = generate_plain(PAGE, CLASSIFICATION, [], ctx, ask=fake)

    errors = errors_of(result)
    assert discount in errors
    assert "누락" in errors[discount] or "수치" in errors[discount], errors


def test_a_synonym_for_a_condition_word_is_not_rejected(ctx, blocks):
    """'하락'을 '떨어짐'으로 바꾸는 것처럼 뜻은 같고 글자만 다른 쉬운말은 통과해야 한다.
    조건 보존 여부는 이제 글자 대조가 아니라 judge_condition_preservation의 정성 판단이므로,
    기본 판정(유지)인 가짜 ask에서는 이 블록이 거부되지 않는다."""
    late = next(b["id"] for b in blocks if "연체" in b["quote"])
    fake = fake_ask(
        {late: "연체하면 최대 연 20% 연체이자가 붙고, 신용점수가 떨어질 수 있습니다."}
    )
    result = generate_plain(PAGE, CLASSIFICATION, [], ctx, ask=fake)

    assert late in {b["source_id"] for b in result["accepted_blocks"]}, errors_of(result)


def test_a_condition_the_judge_flags_as_dropped_is_rejected_even_with_matching_numbers(
    ctx, block_ids
):
    """숫자는 그대로 두고 '~ 이상이면'과 '일부 가맹점 제외'라는 조건·예외의 뜻만 빠진 경우.
    기계적 검사(수치)는 통과하므로, 이건 judge_condition_preservation이 잡아야 한다."""
    discount = block_ids["discount"]
    fake = fake_ask(
        {discount: "전월 실적 30만원이면 모든 가맹점에서 5% 할인이 적용됩니다."},
        conditions={discount: "누락 가능"},
    )
    result = generate_plain(PAGE, CLASSIFICATION, [], ctx, ask=fake)

    errors = errors_of(result)
    assert discount in errors and "조건·불이익" in errors[discount], errors
    assert discount not in {b["source_id"] for b in result["accepted_blocks"]}


def test_turning_a_hedge_into_a_certainty_is_rejected(ctx, block_ids):
    rate = block_ids["rate"]
    fake = fake_ask({rate: "연 이자율은 무조건 연 15%부터 연 20%까지입니다."})
    result = generate_plain(PAGE, CLASSIFICATION, [], ctx, ask=fake)

    errors = errors_of(result)
    assert rate in errors
    assert "가능성" in errors[rate] or "단정" in errors[rate], errors


def test_an_added_superlative_is_rejected(ctx, block_ids):
    fee = block_ids["fee"]
    fake = fake_ask({fee: "업계 최고의 조건으로 연회비는 국내전용 1만원입니다."})
    result = generate_plain(PAGE, CLASSIFICATION, [], ctx, ask=fake)

    errors = errors_of(result)
    assert fee in errors and "단정" in errors[fee], errors


def test_the_source_quote_guard_judges_a_quote_that_is_not_in_the_page(blocks):
    """plain_blocks가 이미 위치를 확인한 줄만 블록으로 만들기 때문에 정상 경로에서는 이 방어 코드가
    걸릴 일이 없다. 그래서 그 판단 자체를 직접 확인한다."""
    page_text = visible_text(FIXTURE_HTML)
    assert verify_source_quote(page_text, blocks[0]["quote"]) == ""
    assert verify_source_quote(page_text, "이 문장은 원문 어디에도 없습니다") != ""


def feedback_aware_ask(model, schema, task, effort="low", **data):
    if "blocks" not in data:
        return {
            "items": [
                {"id": e["id"], "verdict": "유지", "reason": "테스트"} for e in data["items"]
            ]
        }
    wanted = {f["source_id"]: f["requested_change"] for f in data.get("previous_feedback") or []}
    return {
        "items": [
            {"id": b["id"], "text": wanted.get(b["id"], b["quote"]), "terms": []}
            for b in data["blocks"]
        ]
    }


def test_the_previous_rounds_feedback_reaches_the_next_draft(ctx, block_ids):
    fee = block_ids["fee"]
    wanted = "연회비는 카드를 쓰는 동안 해마다 내는 돈으로, 국내전용 1만원입니다."
    feedback = [
        {
            "module": "plain_language",
            "code": "쉬운말10",
            "source_id": fee,
            "reason": "용어 설명 부족",
            "requested_change": wanted,
        }
    ]
    result = generate_plain(PAGE, CLASSIFICATION, feedback, ctx, ask=feedback_aware_ask)
    accepted = {b["source_id"]: b["text"] for b in result["accepted_blocks"]}
    assert accepted.get(fee) == wanted, accepted


def test_feedback_addressed_to_another_module_is_filtered_out(ctx, blocks, block_ids):
    fee = block_ids["fee"]
    other = [
        {
            "module": "explanation_duty_check",
            "code": "X",
            "source_id": fee,
            "reason": "n/a",
            "requested_change": "무시되어야 함",
        }
    ]
    result = generate_plain(PAGE, CLASSIFICATION, other, ctx, ask=feedback_aware_ask)
    accepted = {b["source_id"]: b["text"] for b in result["accepted_blocks"]}
    assert accepted.get(fee) == quote_of(blocks, fee), accepted


def test_only_terms_the_original_really_uses_are_kept(ctx, blocks, block_ids):
    rate = block_ids["rate"]
    assert verify_terms(quote_of(blocks, rate), ["이자율", "없는용어"]) == ["이자율"]

    fake = fake_ask(terms={rate: ["이자율", "없는용어"]})
    result = generate_plain(PAGE, CLASSIFICATION, [], ctx, ask=fake)
    assert result["term_refs"] == [{"source_id": rate, "term": "이자율"}], result["term_refs"]


def test_a_page_with_no_usable_block_reports_that_instead_of_an_empty_success(ctx):
    result = generate_plain({**PAGE, "html": "<html><body></body></html>"}, CLASSIFICATION, [], ctx)
    assert result["accepted_blocks"] == []
    assert result["contract_errors"][0]["reason"].startswith("원문에서 나눌 수 있는")
