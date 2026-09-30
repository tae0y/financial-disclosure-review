"""The downstream nodes wired together: evidence cards (given) -> generate_persona_explanation and
judge_ad_disclosure -> verify_answer -> route_after_verify, with every model call faked."""

from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from langgraph.runtime import Runtime

from financial_disclosure_review.core.context import Context
from financial_disclosure_review.core.state import State
from financial_disclosure_review.domain.ad_disclosure_check.schema import DisclosureJudgments
from financial_disclosure_review.domain.evidence_cards import page_sources
from financial_disclosure_review.domain.persona_explanation.schema import AdviceDraft
from financial_disclosure_review.domain.plain_language.contract import strip_ws
from financial_disclosure_review.graph import nodes
from financial_disclosure_review.graph.nodes import (
    generate_persona_explanation,
    judge_ad_disclosure,
    verify_answer,
)
from financial_disclosure_review.graph.routes import route_after_verify
from financial_disclosure_review.knowledge.build import build_rubric_db
from tests.helpers import state_with

ASSETS = Path(__file__).resolve().parents[2] / "assets"

FIXTURE_HTML = """
<html><body>
<h1>초록카드 신용카드</h1>
<p>연회비는 국내전용 1만원이며 매년 부과됩니다.</p>
<p>연체 시 최고 연 20%의 연체이자율이 적용될 수 있습니다.</p>
<p>중도 해지 시 위약금은 없습니다.</p>
</body></html>
"""
CLASSIFICATION = {"product_type": "신용카드", "page_type": "상품광고", "reason": "통합 확인용"}
PAGE = {
    "url": "https://example.test/integration-card",
    "product": {"product_name": "초록카드"},
    "html": FIXTURE_HTML,
}
SOURCES = page_sources(PAGE)
FEE_LINE = "연회비는 국내전용 1만원이며 매년 부과됩니다."
LATE_LINE = "연체 시 최고 연 20%의 연체이자율이 적용될 수 있습니다."


def source_id_of(text: str) -> str:
    return next(s["source_id"] for s in SOURCES if s["text"] == text)


CARDS = [
    {
        "id": "c1",
        "kind": "fee_claim",
        "subject": "연회비",
        "claim": "국내전용 연회비 1만원",
        "qualifiers": ["매년 부과"],
        "exceptions": [],
        "numbers": ["1만원"],
        "quote": FEE_LINE,
        "source_id": source_id_of(FEE_LINE),
        "visibility": "unresolved",
    },
    {
        "id": "c2",
        "kind": "warning",
        "subject": "연체이자율",
        "claim": "연체 시 최고 연 20%",
        "qualifiers": [],
        "exceptions": [],
        "numbers": ["20%"],
        "quote": LATE_LINE,
        "source_id": source_id_of(LATE_LINE),
        "visibility": "unresolved",
    },
]
EVIDENCE = {"status": "완료", "sources": SOURCES, "cards": CARDS}


@pytest.fixture(scope="module")
def runtime(tmp_path_factory) -> Runtime[Context]:
    path = tmp_path_factory.mktemp("reference") / "reference.sqlite"
    build_rubric_db(ASSETS, path)
    # An empty data dir: no persona dataset, so the node uses the legacy yaml profile.
    data_dir = tmp_path_factory.mktemp("data")
    context = Context(model="fake", db_path=str(path), data_dir=str(data_dir))
    return cast(Runtime[Context], SimpleNamespace(context=context))


def routed(result: dict) -> str:
    return route_after_verify(cast(State, result))


def upstream_display_check(status: str = "완료") -> dict:
    """judge_display_method는 이 확인의 대상이 아니므로 공통 계약을 따르는 가짜 상류 결과를 쓴다."""
    return {
        "items": [],
        "judgments": {
            "status": status,
            "skipped": [],
            "blocks": [],
            "measures": {},
            "reason": "" if status == "완료" else "통합 확인용 판정 불가",
        },
    }


def persona_ask(invent: bool = False, seen: list | None = None):
    """generate_persona_explanation에 주입할 가짜 ask. 설명의무 확인 목록의 앞 두 항목을 권하는
    확인 권고를 돌려준다. invent=True면 원문에 없는 기간을 지어 넣는다."""

    def fake(model, schema, task, effort="low", **data):
        assert schema is AdviceDraft, schema
        if seen is not None:
            seen.append(data.get("previous_feedback") or [])
        advice = "계약 전에 청약 철회 방법과 연회비 반환 조건을 상품설명서에서 확인해 보세요."
        return {
            "advice": advice + (" 철회 기한은 14일입니다." if invent else ""),
            "advice_codes": [item["code"] for item in data["explanation_items"]][:2],
        }

    return fake


def explanation_ask(condition_status: str = "불성립"):
    """judge_disclosure에 주입할 가짜 ask. applies_condition이 없는 항목은 입력 text에서 뽑은
    실제 인용으로 적합 처리하고, 있는 항목은 condition_status('불성립' 정상 제외 또는 '불명확'
    판정 불가)로 남긴다."""

    def fake(model, schema, task, effort="low", **data):
        if schema is DisclosureJudgments:
            quote = strip_ws(data["text"])[:12]
            return {
                "items": [
                    {
                        "code": item["code"],
                        "condition_status": condition_status,
                        "verdict": "판정 불가",
                        "quote": "",
                        "reason": "통합 확인용",
                    }
                    if item.get("applies_condition")
                    else {
                        "code": item["code"],
                        "condition_status": "해당없음",
                        "verdict": "적합",
                        "quote": quote,
                        "reason": "통합 확인용: 기준 충족",
                    }
                    for item in data["items"]
                ]
            }
        raise AssertionError(f"unexpected schema in the chain test: {schema}")

    return fake


def run_chain(
    monkeypatch,
    runtime,
    persona_fake,
    *,
    classification=None,
    evidence=None,
    display_status: str | None = "완료",
    explanation_fake=None,
) -> dict:
    from financial_disclosure_review.domain.ad_disclosure_check import judge_disclosure
    from financial_disclosure_review.domain.persona_explanation import (
        generate_persona_explanation as generate,
    )

    explanation_fake = explanation_fake or explanation_ask("불성립")
    monkeypatch.setattr(
        nodes,
        "generate_persona",
        lambda sources, cards, cls, ctx, feedback, **kw: generate(
            sources, cards, cls, ctx, feedback, ask=persona_fake, **kw
        ),
    )
    monkeypatch.setattr(
        nodes,
        "judge_disclosure",
        lambda page, cls, ctx, previous_original, previous_items, *, feedback=(): judge_disclosure(
            page,
            cls,
            ctx,
            previous_original,
            previous_items,
            ask=explanation_fake,
            feedback=feedback,
        ),
    )
    state = state_with(
        product_page=PAGE,
        classification=CLASSIFICATION if classification is None else classification,
        evidence_cards=EVIDENCE if evidence is None else evidence,
        display_check=upstream_display_check(display_status) if display_status else {},
    )
    state.update(generate_persona_explanation(state, runtime))  # type: ignore[typeddict-item]
    state.update(judge_ad_disclosure(state, runtime))  # type: ignore[typeddict-item]
    state.update(verify_answer(state, runtime))  # type: ignore[typeddict-item]
    return dict(state)


def test_the_happy_path_fills_every_key_and_passes(monkeypatch, runtime):
    result = run_chain(monkeypatch, runtime, persona_ask())

    persona = result["persona_explanation"]
    assert persona["status"] == "완료", persona["reason"]
    assert persona["advice"] and persona["problems"] == []
    assert len(persona["advice_codes"]) == 2
    assert persona["profile"]["status"] == "적용"
    disclosure = result["ad_disclosure_check"]
    assert set(disclosure) == {"items", "original", "deferred"}
    assert not any(row["code"].startswith(("설명", "F")) for row in disclosure["items"])
    excluded = [row for row in disclosure["items"] if not row["applied"]]
    assert excluded, "적용되지 않는 항목이 하나도 없으면 이 시나리오가 의미가 없음"
    assert any(row["code"] == "설명16" for row in disclosure["deferred"])
    assert result["verification"]["passed"] is True, result["verification"]
    assert routed(result) == "end_report"


def test_an_invented_term_holds_the_advice_back_and_asks_for_a_new_one(monkeypatch, runtime):
    """지어낸 기간이 있는 권고는 싣지 않고, 검증이 그 문제를 고쳐 다시 쓰라고 요청합니다."""
    result = run_chain(monkeypatch, runtime, persona_ask(invent=True))

    persona = result["persona_explanation"]
    assert persona["status"] == "원문 대체"
    assert persona["html"] == ""
    assert any("14" in p for p in persona["problems"])
    verification = result["verification"]
    assert "persona_explanation" in verification["failed_modules"]
    request = next(f for f in verification["feedback"] if f["module"] == "persona_explanation")
    assert "14" in request["requested_change"]
    assert routed(result) == "retry_dispatch"


def test_an_unclear_condition_is_never_counted_as_a_pass(monkeypatch, runtime):
    result = run_chain(
        monkeypatch, runtime, persona_ask(), explanation_fake=explanation_ask("불명확")
    )

    assert any(row["verdict"] == "판정 불가" for row in result["ad_disclosure_check"]["original"])
    assert result["verification"]["passed"] is False
    assert "ad_disclosure_check" in result["verification"]["failed_modules"]
    assert routed(result) == "end_report"


def test_a_missing_upstream_result_fails_every_module_and_goes_to_a_person(monkeypatch, runtime):
    result = run_chain(
        monkeypatch, runtime, persona_ask(), classification={}, evidence={}, display_status=None
    )

    assert result["persona_explanation"]["html"] == ""
    assert result["ad_disclosure_check"]["original"] == []
    assert result["verification"]["passed"] is False
    assert result["verification"]["failed_modules"] == [
        "ad_disclosure_check",
        "display_check",
        "persona_explanation",
    ]
    assert routed(result) == "end_report", "고칠 수 있는 피드백이 없으면 재시도하지 않음"


def test_the_retry_round_hands_the_generator_what_verification_asked_for(monkeypatch, runtime):
    """A retry that repeats the same call without the feedback would pay twice for one answer."""
    first = run_chain(monkeypatch, runtime, persona_ask())
    request = {
        "module": "persona_explanation",
        "code": "",
        "source_id": "",
        "reason": "원문에 없는 수치: 14",
        "requested_change": "다음 문제를 고쳐 확인 권고를 다시 쓰세요: 원문에 없는 수치: 14",
        "target": "",
    }
    first["verification"] = {**first["verification"], "feedback": [request]}

    seen: list[list[dict]] = []
    run_chain(monkeypatch, runtime, persona_ask(seen=seen))  # installs the capturing fake
    generate_persona_explanation(cast(State, first), runtime)

    assert seen[-1], "재시도 회차의 설명 생성이 검증 피드백을 받지 못함"
    assert [entry["reason"] for entry in seen[-1]] == ["원문에 없는 수치: 14"]


def test_a_persona_failure_is_routed_back_to_the_generator(monkeypatch, runtime):
    """이름을 바꾼 뒤 재시도 라우팅이 조용히 end_report로 빠지지 않는지 확인합니다."""
    from financial_disclosure_review.graph.retry import plan_retry
    from financial_disclosure_review.graph.routes import route_after_retry

    verification = {
        "passed": False,
        "loop_count": 1,
        "failed_modules": ["persona_explanation"],
        "feedback": [{"module": "persona_explanation", "requested_change": "다시 생성"}],
    }
    state = state_with(verification=verification)
    assert routed(dict(state)) == "retry_dispatch"
    state["verification"] = {**verification, **plan_retry(verification)}  # type: ignore[typeddict-item]
    assert route_after_retry(state) == ["generate_persona_explanation"]


def test_the_reader_is_chosen_from_the_dataset_once_and_kept_on_retry(
    monkeypatch, runtime, tmp_path
):
    from tests.domain.persona_explanation.persona_dataset import write_dataset

    write_dataset(tmp_path)
    ctx = Context(
        model="fake",
        db_path=runtime.context.db_path,
        data_dir=str(tmp_path),
        persona_attributes={"age_min": 70},
    )
    dataset_runtime = cast(Runtime[Context], SimpleNamespace(context=ctx))
    first = run_chain(monkeypatch, dataset_runtime, persona_ask())
    persona = first["persona_explanation"]
    assert persona["profile"]["id"].startswith("nemotron:")
    assert persona["selection"]["decided_by"] == "attributes"
    assert persona["profile"]["attributes"]["reader"]

    # A retry must not pick again, even if the request changed in between.
    retry_ctx = Context(**{**ctx.__dict__, "persona_attributes": {"age_max": 29}})
    retry_runtime = cast(Runtime[Context], SimpleNamespace(context=retry_ctx))
    again = generate_persona_explanation(cast(State, first), retry_runtime)
    assert again["persona_explanation"]["profile"]["id"] == persona["profile"]["id"]
