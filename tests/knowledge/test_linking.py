"""The bounded reference-case linking agent: `knowledge.linking.link_reference_cases`.

Offline: the model is a `ScriptedChat`, the cases come straight from a small corpus yaml written
to a tmp dir (the DB is absent, so `load_case_source` falls back to the yaml), and no embedding
is called unless a test turns `case_rerank` on against that absent DB.
"""

import hashlib
import json

import pytest
import yaml

from financial_disclosure_review.core.context import Context
from financial_disclosure_review.core.usage import BudgetError
from financial_disclosure_review.knowledge import linking
from financial_disclosure_review.knowledge.linking import link_reference_cases
from tests.domain.product_page.fake_chat import ScriptedChat

ANALOG_TEXT = (
    "최대 할인율만 강조하고 할인 조건을 표기하지 않았습니다. "
    "조건 없이 모든 거래에 할인되는 것처럼 광고했습니다."
)
DIRECT_TEXT = (
    "무이자할부 이용금액은 포인트 적립 대상에서 제외됩니다. "
    "제외 조건을 광고에 표기하지 않아 소비자가 오인할 우려가 있습니다."
)
UNVERIFIED_TEXT = "리볼빙 수수료 안내가 부족하다는 민원이 접수되었습니다."


def _case(case_id, text, product_types=("신용카드",), **overrides) -> dict:
    item = {
        "case_id": case_id,
        "record_type": "지적사례",
        "institution": "금융감독원",
        "firm": "not_disclosed",
        "official_date": "2024-01-01",
        "official_primary_url": f"https://example.test/{case_id}",
        "source_tier": 1,
        "product_types": list(product_types),
        "product_basis": "직접",
        "product_subtype": "테스트 카드",
        "legal_basis": "금융소비자보호법 제22조",
        "issue": text.split(".")[0],
        "outcome": "개선 요구",
        "mvp_signal": "광고 문구와 조건 표기",
        "page_only_detectability": "full",
        "related_checklist": ["A01"],
        "text": text + "\n",
        "text_sha256": hashlib.sha256(text.strip().encode("utf-8")).hexdigest(),
        "retrieved_at": "2026-09-27",
    }
    item.update(overrides)
    return item


CASES = [
    _case(
        "case.link_analog",
        ANALOG_TEXT,
        product_basis="유추",
        page_only_detectability="partial",
    ),
    _case("case.link_direct", DIRECT_TEXT, record_type="위반사례"),
    _case("case.link_unverified", UNVERIFIED_TEXT, record_type="민원사례"),
    _case("case.link_other_type", ANALOG_TEXT, product_types=("리볼빙",)),
]
RISK_KINDS = {
    "cases": {
        "case.link_analog": {"risk_kinds": ["benefit_condition"], "text_verified": True},
        "case.link_direct": {"risk_kinds": ["benefit_condition"], "text_verified": True},
        "case.link_unverified": {"risk_kinds": ["rate_fee"], "text_verified": False},
        "case.link_other_type": {"risk_kinds": ["benefit_condition"], "text_verified": True},
    }
}


def _card(card_id, kind, claim, quote, **extra) -> dict:
    return {
        "id": card_id,
        "kind": kind,
        "subject": claim,
        "claim": claim,
        "qualifiers": [],
        "exceptions": [],
        "numbers": [],
        "quote": quote,
        "source_id": f"dom-{card_id}",
        "visibility": "visible",
        **extra,
    }


DISCOUNT = _card(
    "c1", "benefit_claim", "최대 1% 할인", "국내외 가맹점에서 최대 1% 할인 혜택을 드립니다"
)
EXCLUSION = _card(
    "c2",
    "exception",
    "무이자할부 이용금액 할인 제외",
    "모든 무이자할부 이용금액은 할인 대상에서 제외됩니다",
)
FEE = _card("c3", "fee_claim", "리볼빙 수수료율", "리볼빙 수수료율 연 5.9%~19.9%")
CARDS = [DISCOUNT, EXCLUSION, FEE]
CLASSIFICATION = {"product_type": "신용카드"}


@pytest.fixture
def paths(tmp_path) -> dict:
    corpus = tmp_path / "case_corpus.yaml"
    corpus.write_bytes(yaml.safe_dump({"items": CASES}, allow_unicode=True).encode("utf-8"))
    risk = tmp_path / "case_risk_kinds.yaml"
    risk.write_bytes(yaml.safe_dump(RISK_KINDS).encode("utf-8"))
    return {
        "db_path": tmp_path / "absent.sqlite",
        "corpus_path": corpus,
        "risk_kinds_path": risk,
    }


def _ctx(**overrides) -> Context:
    ctx = Context()
    for key, value in overrides.items():
        setattr(ctx, key, value)
    return ctx


def _run(paths, script, cards=CARDS, classification=CLASSIFICATION, ctx=None, chat=None):
    chat = chat if chat is not None else ScriptedChat(script)
    result = link_reference_cases(
        cards,
        classification,
        paths["db_path"],
        ctx=ctx or _ctx(),
        risk_kinds_path=paths["risk_kinds_path"],
        corpus_path=paths["corpus_path"],
        chat=chat,
    )
    return result, chat


def _call(name, **args) -> dict:
    return {"name": name, "args": args}


SEARCH_DISCOUNT = _call(
    "search_cases", query="최대 할인율만 강조하고 할인 조건 미표기", card_ids=["c1"]
)
READ_ANALOG = _call("read_case", case_id="case.link_analog")
PROPOSE_ANALOG = _call(
    "propose_link",
    case_id="case.link_analog",
    card_ids=["c1"],
    page_quote="최대 1% 할인",
    case_quote="최대 할인율만 강조하고 할인 조건을 표기하지 않았습니다.",
    same_pattern="최대 할인율을 앞세우고 할인 조건은 함께 적지 않은 광고 방식",
    material_difference=["페이지는 조건을 다른 영역에 적었을 수 있음"],
)
FINISH = _call("finish", reason="done")


# ---------------------------------------------------------------------------------------------
# no model call: 건너뜀 / 해당 사례 없음 / 판정 불가
# ---------------------------------------------------------------------------------------------


def test_no_cards_skips_without_a_model_turn(paths):
    result, chat = _run(paths, [[FINISH]], cards=[])
    assert result["status"] == "건너뜀"
    assert result["links"] == [] and result["agent_trace"] == []
    assert chat.step == 0


def test_a_product_type_without_cases_makes_no_model_turn(paths):
    result, chat = _run(paths, [[FINISH]], classification={"product_type": "할부금융·리스"})
    assert result["status"] == "해당 사례 없음"
    assert "할부금융·리스" in result["reason"]
    assert chat.step == 0


def test_an_unavailable_case_source_is_unjudgeable(paths, tmp_path):
    paths = {**paths, "corpus_path": tmp_path / "absent.yaml"}
    result, chat = _run(paths, [[FINISH]])
    assert result["status"] == "판정 불가"
    assert chat.step == 0


# ---------------------------------------------------------------------------------------------
# happy path
# ---------------------------------------------------------------------------------------------


def test_search_read_propose_finish_yields_a_validated_link(paths):
    # c2/c3 were never searched, so the first finish is sent back once; the second one stops.
    result, chat = _run(
        paths, [[SEARCH_DISCOUNT], [READ_ANALOG], [PROPOSE_ANALOG], [FINISH], [FINISH]]
    )
    assert result["status"] == "완료"
    assert result["stop_reason"] == "finished"
    assert "case_link" not in chat.system_prompt  # the prompt is prose, not the meter label
    assert chat.system_prompt
    [link] = result["links"]
    assert link["case_id"] == "case.link_analog"
    assert link["card_ids"] == ["c1"]
    assert link["page_quote"] == "최대 1% 할인"
    assert link["case_quote"] == "최대 할인율만 강조하고 할인 조건을 표기하지 않았습니다."
    assert link["case_quote_note"] == ""
    assert link["decided_by"] == "agent"
    assert link["page_only_detectability"] == "partial"
    assert link["page_only_note"] == "페이지 단독 판단 불가"
    assert link["official_url"] == "https://example.test/case.link_analog"
    diffs = link["material_difference"]
    assert diffs[0] == "페이지는 조건을 다른 영역에 적었을 수 있음"
    assert any(d.startswith("product_basis 유추") for d in diffs)
    assert any(d.startswith("record_type 지적사례") for d in diffs)
    assert len(diffs) == len(set(diffs))

    method = result["method"]
    assert method["linking"] == "agent"
    assert method["searches"] == 1 and method["reads"] == 1
    assert method["cases_from"] == "corpus:case_corpus.yaml"
    assert method["rerank"] == "off"
    candidate_ids = [c["case_id"] for c in result["candidates"]]
    assert "case.link_analog" in candidate_ids
    assert "case.link_other_type" not in candidate_ids  # product-type hard filter
    analog = next(c for c in result["candidates"] if c["case_id"] == "case.link_analog")
    assert analog["card_ids"] == ["c1"] and analog["score"] > 0

    trace = result["agent_trace"]
    assert [t["tool"] for t in trace] == [
        "search_cases",
        "read_case",
        "propose_link",
        "finish",
        "finish",
    ]
    assert not any(t["blocked"] for t in trace)
    assert all(len(t["result"]) <= 12_001 for t in trace)


def test_search_never_returns_the_full_text_and_read_numbers_sentences(paths):
    result, _ = _run(paths, [[SEARCH_DISCOUNT], [READ_ANALOG], [FINISH]])
    search, read = result["agent_trace"][0]["result"], result["agent_trace"][1]["result"]
    assert "조건 없이 모든 거래에 할인되는 것처럼" not in search
    assert '"n": 2' in read and "조건 없이 모든 거래에 할인되는 것처럼" in read


def test_reading_an_unverified_case_says_it_may_not_be_quoted(paths):
    search = _call("search_cases", query="리볼빙 수수료 안내 부족", card_ids=["c3"])
    read = _call("read_case", case_id="case.link_unverified")
    propose = _call(
        "propose_link",
        case_id="case.link_unverified",
        card_ids=["c3"],
        page_quote="리볼빙 수수료율",
        case_quote="",
        same_pattern="수수료 안내가 짧게만 적힌 방식",
        material_difference=[],
    )
    result, _ = _run(paths, [[search], [read], [propose], [FINISH]])
    assert "may not be quoted" in result["agent_trace"][1]["result"]
    [link] = result["links"]
    assert link["case_quote"] == "" and link["case_quote_note"] == "원문 재확인 필요"
    assert link["page_only_note"] == ""


# ---------------------------------------------------------------------------------------------
# refusals: code validates every proposal
# ---------------------------------------------------------------------------------------------


def _propose(**changes) -> dict:
    return {"name": "propose_link", "args": {**PROPOSE_ANALOG["args"], **changes}}


@pytest.mark.parametrize(
    ("script", "reason_part"),
    [
        ([[SEARCH_DISCOUNT], [PROPOSE_ANALOG]], "read_case"),
        ([[READ_ANALOG], [PROPOSE_ANALOG]], "search_cases"),
        ([[SEARCH_DISCOUNT], [READ_ANALOG], [_propose(page_quote="연회비 면제")]], "page_quote"),
        (
            [[SEARCH_DISCOUNT], [READ_ANALOG], [_propose(case_quote="사례에 없는 문장입니다")]],
            "case_quote",
        ),
        (
            [[SEARCH_DISCOUNT], [READ_ANALOG], [_propose(same_pattern="같은 위반 광고")]],
            "verdict",
        ),
        ([[SEARCH_DISCOUNT], [READ_ANALOG], [_propose(same_pattern="  ")]], "same_pattern"),
        ([[SEARCH_DISCOUNT], [READ_ANALOG], [_propose(card_ids=["c9"])]], "c9"),
    ],
    ids=[
        "before_read",
        "not_searched",
        "page_quote_not_in_card",
        "case_quote_not_in_case",
        "verdict_word",
        "empty_same_pattern",
        "unknown_card",
    ],
)
def test_an_invalid_proposal_is_refused_with_its_reason(paths, script, reason_part):
    # The first finish is sent back (concrete cards unsearched); the second one ends the run.
    result, _ = _run(paths, script + [[FINISH], [FINISH]])
    refused = next(t for t in result["agent_trace"] if t["tool"] == "propose_link")
    assert refused["tool"] == "propose_link"
    assert refused["blocked"] is True
    assert reason_part in refused["blocked_reason"]
    assert result["links"] == []
    assert result["status"] == "해당 사례 없음"


def test_a_case_quote_for_an_unverified_case_is_refused(paths):
    search = _call("search_cases", query="리볼빙 수수료 안내 부족", card_ids=["c3"])
    read = _call("read_case", case_id="case.link_unverified")
    propose = _call(
        "propose_link",
        case_id="case.link_unverified",
        card_ids=["c3"],
        page_quote="리볼빙 수수료율",
        case_quote=UNVERIFIED_TEXT,
        same_pattern="수수료 안내가 짧게만 적힌 방식",
        material_difference=[],
    )
    result, _ = _run(paths, [[search], [read], [propose], [FINISH]])
    refused = result["agent_trace"][2]
    assert refused["blocked"] and "text_verified" in refused["blocked_reason"]
    assert result["links"] == []


def test_a_second_link_to_the_same_case_is_refused(paths):
    again = _propose(card_ids=["c2"], page_quote="무이자할부 이용금액")
    result, _ = _run(paths, [[SEARCH_DISCOUNT], [READ_ANALOG], [PROPOSE_ANALOG], [again], [FINISH]])
    assert len(result["links"]) == 1
    refused = result["agent_trace"][3]
    assert refused["blocked"] and "already linked" in refused["blocked_reason"]


def test_an_unknown_tool_and_bad_arguments_are_refused(paths):
    result, _ = _run(paths, [[_call("judge_page", verdict="위반")], [_call("read_case")], [FINISH]])
    assert result["agent_trace"][0]["blocked"]
    assert "unknown tool" in result["agent_trace"][0]["blocked_reason"]
    assert result["agent_trace"][1]["blocked"]
    assert "case_id" in result["agent_trace"][1]["blocked_reason"]


# ---------------------------------------------------------------------------------------------
# budget and stop reasons
# ---------------------------------------------------------------------------------------------


def test_max_turns_without_finish_keeps_the_links_accepted_so_far(paths):
    result, chat = _run(
        paths,
        [[SEARCH_DISCOUNT], [READ_ANALOG], [PROPOSE_ANALOG], [FINISH]],
        ctx=_ctx(case_link_max_turns=3),
    )
    assert result["stop_reason"] == "max_turns"
    assert chat.step == 3
    assert [link["case_id"] for link in result["links"]] == ["case.link_analog"]
    # Audit 2026-09-29 R5: links from a run that never finished are partial, not complete.
    assert result["status"] == "부분 완료"
    assert result["method"]["max_turns"] == 3


def test_max_turns_without_any_link_is_not_read_as_no_case(paths):
    result, _ = _run(paths, [[SEARCH_DISCOUNT], [READ_ANALOG]], ctx=_ctx(case_link_max_turns=2))
    assert result["stop_reason"] == "max_turns"
    assert result["links"] == []
    assert result["status"] == "판정 불가"
    assert "턴 한도" in result["reason"]


def test_the_link_cap_ends_the_loop(paths, monkeypatch):
    monkeypatch.setattr(linking, "MAX_LINKS", 1)
    result, chat = _run(paths, [[SEARCH_DISCOUNT], [READ_ANALOG], [PROPOSE_ANALOG], [FINISH]])
    assert result["stop_reason"] == "link_cap"
    assert chat.step == 3
    assert len(result["links"]) == 1


class BudgetChat(ScriptedChat):
    """Answers the first turns from its script, then hits the run's call cap."""

    def __init__(self, script, fail_at: int):
        super().__init__(script)
        self.fail_at = fail_at

    def turn(self) -> dict:
        if self.step + 1 >= self.fail_at:
            raise BudgetError("model call cap 60 reached before case_link")
        return super().turn()


def test_a_budget_error_stops_the_loop_without_raising(paths):
    chat = BudgetChat([[SEARCH_DISCOUNT]], fail_at=2)
    result, _ = _run(paths, [], chat=chat)
    assert result["stop_reason"] == "budget_exhausted"
    assert result["status"] == "판정 불가"
    assert "call cap" in result["reason"]
    assert [t["tool"] for t in result["agent_trace"]] == ["search_cases"]


def test_a_budget_error_after_a_link_keeps_the_link(paths):
    chat = BudgetChat([[SEARCH_DISCOUNT], [READ_ANALOG], [PROPOSE_ANALOG]], fail_at=4)
    result, _ = _run(paths, [], chat=chat)
    assert result["stop_reason"] == "budget_exhausted"
    assert result["status"] == "부분 완료"
    assert len(result["links"]) == 1


def test_rerank_without_case_vectors_falls_back_to_bm25_order(paths):
    result, _ = _run(paths, [[SEARCH_DISCOUNT], [FINISH]], ctx=_ctx(case_rerank=True))
    assert "unavailable" in result["method"]["rerank"]
    assert result["candidates"]


def test_the_same_script_gives_the_same_trace(paths):
    script = [[SEARCH_DISCOUNT, READ_ANALOG], [PROPOSE_ANALOG], [_propose(same_pattern="위반")]]
    first, _ = _run(paths, script)
    second, _ = _run(paths, script)
    assert first["agent_trace"] == second["agent_trace"]
    assert first == second


def test_a_first_finish_with_unsearched_concrete_cards_is_sent_back_once(paths):
    """B4 1회차(2026-09-29): 검색 1회·읽기 0회로 끝낸 페이지가 있어 재현율이 3/14였습니다."""
    result, chat = _run(paths, [[SEARCH_DISCOUNT], [FINISH], [FINISH]])
    first, second = [t for t in result["agent_trace"] if t["tool"] == "finish"]
    nudge = json.loads(first["result"])
    assert nudge["finished"] is False
    assert set(nudge["unsearched_card_ids"]) == {"c2", "c3"}
    assert nudge["cases_read"] == 0
    assert json.loads(second["result"])["finished"] is True
    assert result["stop_reason"] == "finished"


# ---------------------------------------------------------------------------------------------
# batched tools (audit 2026-09-29 R6: one tool call per turn ran 3 of 4 pages out of turns)
# ---------------------------------------------------------------------------------------------


def test_one_search_call_can_run_several_card_groups(paths):
    batch = _call(
        "search_cases",
        queries=[
            {"query": "최대 할인율만 강조", "card_ids": ["c1"], "risk_kind": "benefit_condition"},
            {"query": "수수료율 범위만 표기", "card_ids": ["c3"], "risk_kind": "rate_fee"},
        ],
    )
    result, chat = _run(paths, [[batch], [FINISH], [FINISH]])
    first = json.loads(chat.results[0][1])
    assert [s["query"] for s in first["searches"]] == ["최대 할인율만 강조", "수수료율 범위만 표기"]
    assert all("results" in s for s in first["searches"])
    assert result["method"]["searches"] == 2
    assert not result["agent_trace"][0]["blocked"]


def test_the_single_query_form_still_answers_as_before(paths):
    _, chat = _run(paths, [[SEARCH_DISCOUNT], [FINISH], [FINISH]])
    assert "results" in json.loads(chat.results[0][1])


def test_one_read_call_can_read_several_cases_and_each_can_be_linked(paths):
    both = _call("read_case", case_ids=["case.link_analog", "case.link_direct"])
    result, chat = _run(paths, [[SEARCH_DISCOUNT], [both], [PROPOSE_ANALOG], [FINISH]])
    read = json.loads(chat.results[1][1])
    assert [c["case_id"] for c in read["cases"]] == ["case.link_analog", "case.link_direct"]
    assert result["method"]["reads"] == 2
    assert [link["case_id"] for link in result["links"]] == ["case.link_analog"]


@pytest.mark.parametrize(
    ("call", "reason_part"),
    [
        (_call("read_case", case_ids=["a", "b", "c", "d"]), "at most"),
        (_call("read_case"), "case_id"),
        (_call("search_cases", queries=[{"query": f"q{n}"} for n in range(5)]), "at most"),
        (_call("search_cases"), "query"),
    ],
)
def test_batches_have_a_size_limit_and_need_something_to_do(paths, call, reason_part):
    result, _ = _run(paths, [[call], [FINISH], [FINISH]])
    assert result["agent_trace"][0]["blocked"]
    assert reason_part in result["agent_trace"][0]["blocked_reason"]
