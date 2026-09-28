"""평가 하네스: 카세트 재생, 결함 주입, 지표 집계를 모델 호출 없이 확인한다."""

import json

import pytest
from pydantic import BaseModel

from financial_disclosure_review.core.context import Context
from financial_disclosure_review.core.text import locate_quote, visible_text
from financial_disclosure_review.evaluation.cassette import Cassette, CassetteMissError, call_key
from financial_disclosure_review.evaluation.defects import longest_unused_sentence, remove_quote
from financial_disclosure_review.evaluation.metrics import metrics_for
from financial_disclosure_review.evaluation.suites import run_duty_flip, run_plain_contract

HTML = """<!doctype html><html lang="ko"><body><main>
<p>연회비는 국내전용 20,000원이며 해외겸용은 25,000원입니다.</p>
<p>전월 실적 30만원 이상이면 커피 전문점에서 10% 할인을 받을 수 있습니다.</p>
<p>카드 대금을 연체하면 개인신용평점이 하락할 수 있고 금융거래에 불이익이 생길 수 있습니다.</p>
<p>이 카드는 여행을 자주 가는 고객을 위해 만든 상품이며 다양한 제휴처에서 편하게 쓸 수 있습니다.</p>
</main></body></html>"""


class Answer(BaseModel):
    value: str


# ---------------------------------------------------------------- cassette


def test_the_key_changes_when_the_input_changes():
    first = call_key("gpt-5-mini", "Answer", "task", {"text": "가"})
    assert first == call_key("gpt-5-mini", "Answer", "task", {"text": "가"})
    assert first != call_key("gpt-5-mini", "Answer", "task", {"text": "나"})
    assert first != call_key("gpt-5-mini", "Answer", "다른 task", {"text": "가"})


def test_recording_then_replaying_gives_the_same_answer_without_calling_again(tmp_path):
    calls = []

    def fake(model, schema, task, effort="low", **data):
        calls.append(data)
        return {"value": "녹음됨"}

    path = tmp_path / "cassette.json"
    recorder = Cassette(path, mode="record", ask=fake)
    assert recorder.ask("gpt-5-mini", Answer, "task", "low", text="가")["value"] == "녹음됨"
    recorder.save()
    assert json.loads(path.read_text(encoding="utf-8"))["entries"]

    player = Cassette(path, mode="replay")
    assert player.ask("gpt-5-mini", Answer, "task", "low", text="가")["value"] == "녹음됨"
    assert len(calls) == 1, "재생은 모델을 다시 부르지 않아야 함"
    assert player.stats()["hits"] == 1


def test_replaying_an_input_that_was_never_recorded_fails_loudly(tmp_path):
    player = Cassette(tmp_path / "none.json", mode="replay")
    with pytest.raises(CassetteMissError, match="Re-run with --live --record"):
        player.ask("gpt-5-mini", Answer, "task", "low", text="가")


# ---------------------------------------------------------------- defects


def test_removing_a_quote_really_removes_it_from_the_rendered_text():
    quote = "연회비는 국내전용 20,000원이며 해외겸용은 25,000원입니다."
    result, gone = remove_quote(HTML, quote)
    assert gone is True
    assert locate_quote(visible_text(result), quote) is None
    assert "전월 실적 30만원" in visible_text(result), "다른 문장은 남아야 함"


def test_a_quote_that_is_not_on_the_page_reports_that_the_edit_did_not_land():
    _, gone = remove_quote(HTML, "이 문장은 페이지에 없습니다.")
    assert gone is False


def test_the_neutral_sentence_is_one_no_judgment_cited():
    used = ["연회비는 국내전용 20,000원이며 해외겸용은 25,000원입니다."]
    neutral = longest_unused_sentence(HTML, used)
    assert neutral
    assert "연회비" not in neutral


# ---------------------------------------------------------------- duty flip


class FakeDutyAsk:
    """인용한 문장이 본문에 남아 있으면 적합, 사라지면 부적합으로 답하는 가짜 모델."""

    QUOTES = {
        "F11": "연회비는 국내전용 20,000원이며 해외겸용은 25,000원입니다.",
        "설명11": "연회비는 국내전용 20,000원이며 해외겸용은 25,000원입니다.",
        "F15": "전월 실적 30만원 이상이면 커피 전문점에서 10% 할인을 받을 수 있습니다.",
        "설명15": "전월 실적 30만원 이상이면 커피 전문점에서 10% 할인을 받을 수 있습니다.",
        "F07": "카드 대금을 연체하면 개인신용평점이 하락할 수 있고"
        " 금융거래에 불이익이 생길 수 있습니다.",
    }

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, model, schema, task, effort="low", **data):
        self.calls.append(schema.__name__)
        text = data["text"]
        items = []
        for item in data["items"]:
            code = item["code"]
            quote = self.QUOTES.get(code, "")
            if quote and locate_quote(text, quote) is not None:
                items.append(
                    {"code": code, "condition_status": "해당없음", "verdict": "적합",
                     "quote": quote, "reason": "본문에 있음"}
                )
            else:
                items.append(
                    {"code": code, "condition_status": "해당없음", "verdict": "부적합",
                     "quote": "", "reason": "본문에서 확인되지 않음"}
                )
        return {"items": items}


def fake_cassette(tmp_path) -> Cassette:
    return Cassette(tmp_path / "fake.json", mode="live", ask=FakeDutyAsk())


def test_a_deleted_disclosure_is_detected_and_a_neutral_delete_flips_nothing(
    tmp_path, monkeypatch
):
    from financial_disclosure_review.evaluation import suites

    items = [
        {"code": code, "criterion": f"{code} 기준", "applies_condition": None, "rubric": "r"}
        for code in FakeDutyAsk.QUOTES
    ]
    monkeypatch.setattr(suites, "_in_scope_items", lambda db_path, product_type: items)
    html_path = tmp_path / "page.html"
    html_path.write_text(HTML, encoding="utf-8")
    config = {
        "base_html": str(html_path),
        "classification": {"product_type": "신용카드", "page_type": "상품광고"},
        "prefer_codes": ["F11", "F15"],
    }

    result = run_duty_flip(Context(model="fake"), fake_cassette(tmp_path), config, max_flips=2)
    metrics = metrics_for(result)

    assert metrics["injected"] == 2
    assert metrics["detected"] == 2
    assert metrics["detection_rate"] == 1.0
    assert metrics["false_flips"] == []
    assert metrics["quote_groundedness"]["rate"] == 1.0
    assert [row["case"] for row in result["rows"]][-1] == "neutral-delete"


# ---------------------------------------------------------------- plain contract


class FakeConditionCassette:
    """조건 보존 판정을 항상 '유지'로 답하는 가짜 카세트. 기계적 검사를 통과한 케이스만
    judge_condition_preservation을 거치므로, 이 스텁이 실제로 불려야 recall이 맞게 나온다."""

    def ask(self, model, schema, task, effort="low", **data):
        return {
            "items": [{"id": e["id"], "verdict": "유지", "reason": "테스트"} for e in data["items"]]
        }


def test_the_plain_contract_suite_counts_a_clean_pair_and_a_defective_one():
    result = run_plain_contract(
        Context(),
        FakeConditionCassette(),
        [
            {"id": "clean", "defect": None, "source_quote": "연회비는 20,000원입니다.",
             "rewrite": "1년에 20,000원을 냅니다."},
            {"id": "invented", "defect": "invented_number",
             "expect_marker": "원문에 없는 수치 포함",
             "source_quote": "연회비는 20,000원입니다.", "rewrite": "연회비는 12,000원입니다."},
        ],
    )
    metrics = metrics_for(result)
    assert metrics["recall"] == 1.0
    assert metrics["false_alarm_rate"] == 0.0
    assert metrics["by_defect"]["invented_number"]["marker_hit"] == 1


def test_the_plain_contract_suite_catches_a_condition_the_judge_flags():
    """수치는 그대로인데 조건의 뜻만 빠진 경우 — judge_condition_preservation이 잡아야 한다."""

    class DropCassette:
        def ask(self, model, schema, task, effort="low", **data):
            return {
                "items": [
                    {"id": e["id"], "verdict": "누락 가능", "reason": "이상 조건이 사라짐"}
                    for e in data["items"]
                ]
            }

    result = run_plain_contract(
        Context(),
        DropCassette(),
        [
            {
                "id": "condition-drop",
                "defect": "condition_dropped",
                "expect_marker": "조건·불이익 관련 뜻 누락 가능",
                "source_quote": "전월 실적 30만원 이상이면 5천원이 적립됩니다.",
                "rewrite": "전월 실적 30만원일 때 5천원이 적립됩니다.",
            }
        ],
    )
    row = result["rows"][0]
    assert row["flagged"] is True
    assert row["correct"] is True
    assert row["marker_hit"] is True
