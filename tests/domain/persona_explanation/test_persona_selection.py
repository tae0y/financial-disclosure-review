"""select_persona and choose_profile with the model scripted: code validates every proposal."""

import json
from pathlib import Path

import pytest

from financial_disclosure_review.core.context import Context
from financial_disclosure_review.core.usage import BudgetError
from financial_disclosure_review.domain.persona_explanation.dataset import (
    SHARDS,
    PersonaStore,
    dataset_dir,
)
from financial_disclosure_review.domain.persona_explanation.selection import (
    DEFAULT_SEED,
    MAX_TURNS,
    choose_profile,
    select_persona,
)
from tests.domain.persona_explanation.persona_dataset import (
    uuid_of,
    write_dataset,
    write_store,
)
from tests.domain.persona_explanation.persona_fixtures import FIRSTCARD, LOWFIN
from tests.domain.product_page.fake_chat import ScriptedChat

ASSETS = Path(__file__).resolve().parents[3] / "assets"
CARDS = [
    {"id": "c1", "kind": "rate_claim", "subject": "카드론 금리", "claim": "연 5.9%~19.9%"},
    {"id": "c2", "kind": "warning", "subject": "연체", "claim": "연체 시 불이익"},
]
REQUEST = "70대 은퇴자, 카드론을 처음 알아보는 사람"


def ctx(**kwargs) -> Context:
    return Context(model="fake", rubric_dir=str(ASSETS), **kwargs)


@pytest.fixture
def store(tmp_path) -> PersonaStore:
    return PersonaStore(write_store(tmp_path / "set"))


def select(
    store, request="", chat=None, product_type: str | None = "신용카드", ask=None, **ctx_kwargs
):
    return select_persona(
        request,
        ctx(**ctx_kwargs),
        product_type=product_type,
        cards_summary=["rate_claim: 카드론 금리"],
        store=store,
        chat=chat,
        ask=ask,
    )


class BudgetChat(ScriptedChat):
    def __init__(self):
        super().__init__([])

    def turn(self) -> dict:
        raise BudgetError("model call cap 60 reached before persona_select")


def test_the_result_has_the_documented_shape(store):
    result = select(store)
    assert set(result) == {
        "uuid",
        "decided_by",
        "filters",
        "match_count",
        "seed",
        "stop_reason",
        "trace",
        "reason",
    }
    assert result["seed"] == DEFAULT_SEED


def test_a_given_uuid_wins(store):
    result = select(store, persona_uuid=uuid_of("05"), persona_attributes={"sex": "남자"})
    assert result["uuid"] == uuid_of("05")
    assert result["decided_by"] == "uuid" and result["match_count"] == 1


def test_an_unknown_uuid_falls_back_to_the_defaults_with_a_reason(store):
    result = select(store, persona_uuid="f" * 32)
    assert result["decided_by"] == "fallback"
    assert "f" * 32 in result["reason"]
    assert result["uuid"] and result["filters"] == {"age_min": 20}


def test_attributes_are_validated_then_picked_by_code(store):
    result = select(store, persona_attributes={"occupation_contains": ["보험"]})
    assert result["decided_by"] == "attributes"
    assert result["uuid"] == uuid_of("04")
    assert result["filters"] == {"occupation_contains": ["보험"]}
    assert result["match_count"] == 1


@pytest.mark.parametrize(
    ("attributes", "needle"),
    [({"province": ["화성"]}, "화성"), ({"income": "high"}, "income")],
)
def test_invalid_attributes_fall_back_to_the_defaults(store, attributes, needle):
    result = select(store, persona_attributes=attributes)
    assert result["decided_by"] == "fallback"
    assert needle in result["reason"]
    assert result["filters"] == {"age_min": 20}


def test_attributes_without_a_match_are_relaxed_in_a_fixed_order(store):
    result = select(store, persona_attributes={"province": ["서울"], "age_min": 80})
    assert result["decided_by"] == "fallback"
    assert result["filters"] == {"age_min": 80}
    assert result["uuid"] == uuid_of("06")
    relaxed = [t for t in result["trace"] if t.get("step") == "relax"]
    assert [t["dropped"] for t in relaxed] == ["province"]
    assert "province" in result["reason"]


def test_no_request_uses_the_product_type_defaults(store):
    result = select(store, product_type="장기카드대출")
    assert result["decided_by"] == "default"
    assert result["filters"] == {"age_min": 30, "age_max": 59}
    assert result["match_count"] == 6
    again = select(store, product_type="장기카드대출")
    assert again["uuid"] == result["uuid"]
    unknown = select(store, product_type=None)
    assert unknown["filters"] == {"age_min": 20}


def test_the_agent_chooses_filters_and_code_picks_the_row(store):
    chat = ScriptedChat(
        [
            [{"name": "list_values", "args": {"field": "education_level"}}],
            [{"name": "count_matches", "args": {"filters": {"age_min": 70}}}],
            [
                {
                    "name": "choose",
                    "args": {
                        "filters": {"age_min": 70, "education_level": ["초등학교"]},
                        "rationale": "70대, 학력이 낮은 독자",
                    },
                }
            ],
        ]
    )
    result = select(store, REQUEST, chat=chat, product_type="장기카드대출")
    assert result["decided_by"] == "agent" and result["stop_reason"] == "chosen"
    assert result["uuid"] == uuid_of("01")
    assert result["filters"] == {"age_min": 70, "education_level": ["초등학교"]}
    assert [t["tool"] for t in result["trace"]] == ["list_values", "count_matches", "choose"]
    assert json.loads(chat.results[1][1])["count"] == 2
    assert REQUEST in chat.messages[0] and "카드론 금리" in chat.messages[0]
    assert "choose" in chat.system_prompt


def test_values_outside_the_vocabulary_and_malformed_calls_are_refused(store):
    chat = ScriptedChat(
        [
            [
                {"name": "count_matches", "args": {"filters": {"province": ["화성"]}}},
                {"name": "count_matches", "args": {"filters": {"income": "high"}}},
                {"name": "list_values", "args": {"field": "persona"}},
                {"name": "delete_rows", "args": {}},
            ],
            [
                {
                    "name": "choose",
                    "args": {"filters": {"province": ["서울"]}, "rationale": "서울 거주"},
                }
            ],
        ]
    )
    result = select(store, REQUEST, chat=chat)
    refused = [t for t in result["trace"] if t["refused"]]
    assert len(refused) == 4
    assert "화성" in refused[0]["reason"]
    assert result["decided_by"] == "agent" and result["filters"] == {"province": ["서울"]}


def test_two_empty_choices_stop_with_no_match_and_relax(store):
    empty = {"name": "choose", "args": {"filters": {"age_min": 90}, "rationale": "90대"}}
    chat = ScriptedChat([[empty], [empty]])
    result = select(store, REQUEST, chat=chat)
    assert result["stop_reason"] == "no_match"
    assert result["decided_by"] == "fallback"
    assert result["filters"] == {}
    assert result["match_count"] == 9
    assert chat.step == 2


def test_a_quiet_model_runs_out_of_turns_and_falls_back_to_the_defaults(store):
    chat = ScriptedChat([])
    result = select(store, REQUEST, chat=chat, product_type="리볼빙")
    assert result["stop_reason"] == "max_turns"
    assert result["decided_by"] == "fallback"
    assert result["filters"] == {"age_min": 30, "age_max": 59}
    assert len([t for t in result["trace"] if t.get("tool_calls") == 0]) == MAX_TURNS


def test_the_last_counted_filters_are_relaxed_when_turns_run_out(store):
    count = {"name": "count_matches", "args": {"filters": {"occupation_contains": ["교수"]}}}
    chat = ScriptedChat([[count]] * MAX_TURNS)
    result = select(store, REQUEST, chat=chat)
    assert result["stop_reason"] == "max_turns"
    assert result["filters"] == {"occupation_contains": ["교수"]}
    assert result["uuid"] == uuid_of("05")


def test_an_exhausted_budget_never_propagates(store):
    result = select(store, REQUEST, chat=BudgetChat())
    assert result["stop_reason"] == "budget_exhausted"
    assert result["decided_by"] == "fallback" and result["uuid"]


def test_a_model_failure_falls_back_instead_of_stopping_the_review(store):
    class BrokenChat(BudgetChat):
        def turn(self) -> dict:
            raise ConnectionError("network down")

    result = select(store, REQUEST, chat=BrokenChat())
    assert result["stop_reason"] == "model_error"
    assert result["decided_by"] == "fallback" and result["uuid"]


def test_an_offline_ask_without_a_chat_makes_no_model_call(store):
    result = select(store, REQUEST, ask=lambda *a, **k: {})
    assert result["stop_reason"] == "no_model"
    assert result["decided_by"] == "fallback" and result["uuid"]


def choose(tmp_path, chat=None, **ctx_kwargs) -> dict:
    return choose_profile(
        ctx(**ctx_kwargs),
        product_type="장기카드대출",
        cards=CARDS,
        data_dir=tmp_path,
        rubric_dir=ASSETS,
        chat=chat,
    )


def test_without_the_dataset_the_legacy_profile_is_used(tmp_path):
    result = choose(tmp_path)
    assert result["profile"]["id"] == LOWFIN and result["profile"]["status"] == "적용"
    assert result["selection"]["decided_by"] == "fallback"
    assert result["selection"]["reason"].startswith("페르소나 데이터셋 없음")
    assert choose(tmp_path, persona_profile=FIRSTCARD)["profile"]["id"] == FIRSTCARD


def test_with_the_dataset_the_profile_comes_from_the_selected_row(tmp_path):
    write_dataset(tmp_path)
    result = choose(tmp_path, persona_attributes={"occupation_contains": ["은행"]})
    assert result["selection"]["decided_by"] == "attributes"
    assert result["profile"]["id"] == f"nemotron:{uuid_of('02')}"
    assert result["profile"]["status"] == "적용"
    assert result["profile"]["attributes"]["financial_familiarity"] == "높음"
    assert "은행 사무원" in result["profile"]["attributes"]["reader"]


def test_the_agent_sees_a_summary_of_the_page_cards(tmp_path):
    write_dataset(tmp_path)
    chat = ScriptedChat(
        [[{"name": "choose", "args": {"filters": {"age_min": 70}, "rationale": "고령"}}]]
    )
    result = choose(tmp_path, chat=chat, persona_request=REQUEST)
    assert result["selection"]["decided_by"] == "agent"
    assert "카드론 금리" in chat.messages[0] and REQUEST in chat.messages[0]


def test_a_broken_dataset_falls_back_to_the_legacy_profile(tmp_path):
    folder = dataset_dir(tmp_path)
    folder.mkdir(parents=True)
    for shard in SHARDS:
        (folder / shard).write_bytes(b"not parquet")
    result = choose(tmp_path)
    assert result["profile"]["id"] == LOWFIN
    assert result["selection"]["decided_by"] == "fallback"
    assert "읽을 수 없음" in result["selection"]["reason"]
