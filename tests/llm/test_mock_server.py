"""The mock OpenAI server, driven through the real client code: ask, ToolChat and embeddings.

Nothing here reaches the real API; the base URL points at an in-process mock and the key is fake.
"""

import json
import threading

import pytest
from pydantic import BaseModel

from financial_disclosure_review.core.text import locate_quote, visible_text
from financial_disclosure_review.core.usage import start_run
from financial_disclosure_review.domain.classification.schema import ClassifyAnswer
from financial_disclosure_review.domain.classification.stages import check_answer
from financial_disclosure_review.domain.persona_explanation import selection
from financial_disclosure_review.domain.product_page.tools import TOOLS as PAGE_TOOLS
from financial_disclosure_review.llm import mock_server
from financial_disclosure_review.llm.client import ToolChat, ask

HTML = "<html><body><h1>라스베가스 카드</h1><p>연회비 국내전용 10,000원 안내</p></body></html>"


@pytest.fixture
def mock_api(monkeypatch, tmp_path):
    server = mock_server.serve(port=0, log_path=tmp_path / "calls.jsonl")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("OPENAI_BASE_URL", f"http://127.0.0.1:{server.server_address[1]}/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-mock-not-a-real-key")
    start_run(max_calls=60, max_usd=1.0)
    yield tmp_path / "calls.jsonl"
    server.shutdown()
    server.server_close()


def test_ask_gets_a_schema_valid_answer(mock_api) -> None:
    class Verdict(BaseModel):
        reason: str
        verdict: str
        level: int
        tags: list[str]
        note: str | None

    answer = ask("gpt-5-mini", Verdict, "판정합니다.", html=HTML)
    assert Verdict.model_validate(answer)
    assert answer["reason"]  # non-empty, so "empty reason" checks pass
    calls = [json.loads(line) for line in mock_api.read_text(encoding="utf-8").splitlines()]
    assert calls[0]["schema"] == "Verdict"


def test_quote_fields_are_copied_from_the_page_text(mock_api) -> None:
    class Quoted(BaseModel):
        quote: str
        evidence: str

    answer = ask("gpt-5-mini", Quoted, "인용합니다.", html=HTML)
    text = visible_text(HTML)
    assert locate_quote(text, answer["quote"]) is not None
    assert locate_quote(text, answer["evidence"]) is not None


def test_items_mirror_the_codes_the_caller_asked_about(mock_api) -> None:
    class Item(BaseModel):
        code: str
        verdict: str
        reason: str

    class Items(BaseModel):
        items: list[Item]

    answer = ask("gpt-5-mini", Items, "판정합니다.", items={"E07": {}, "E08": {}})
    assert [i["code"] for i in answer["items"]] == ["E07", "E08"]


def test_a_verdict_enum_answers_undecided() -> None:
    enum = {"type": "string", "enum": ["적합", "부적합", "판정 불가"]}
    assert mock_server.synth(enum, {}) == "판정 불가"


def test_classification_passes_its_own_checks_as_a_single_card_product(mock_api) -> None:
    page = {"html": HTML, "url": "https://example.test", "product": ""}
    answer = ask("gpt-5-mini", ClassifyAnswer, "분류합니다.", **page)
    assert answer["product_type"] == "신용카드"
    assert check_answer(answer, visible_text(HTML)) == []


def test_persona_selection_turns_the_free_text_into_a_choose_call(mock_api) -> None:
    chat = ToolChat("gpt-5-mini", selection.TOOLS, label="persona_select")
    chat.system(selection.SELECT_TASK)
    chat.user(json.dumps({"reader_request": "서울 사는 70대 은퇴자, 카드론을 처음 알아봄"}))
    calls = chat.turn()["tool_calls"]
    assert [c["name"] for c in calls] == ["choose"]
    chosen = selection.Choose.model_validate(calls[0]["args"])
    assert (chosen.filters.age_min, chosen.filters.age_max) == (70, 79)
    assert chosen.filters.province == ["서울"]
    assert chosen.familiarity_hint == "낮음"


def test_the_page_agent_gets_no_tool_call(mock_api) -> None:
    """Discovery is not mocked: a review under the mock needs a stored site rule."""
    chat = ToolChat("gpt-5-mini", PAGE_TOOLS)
    chat.user("Product page: https://example.test")
    assert chat.turn()["tool_calls"] == []
