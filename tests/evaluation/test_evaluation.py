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
                    {
                        "code": code,
                        "condition_status": "해당없음",
                        "verdict": "적합",
                        "quote": quote,
                        "reason": "본문에 있음",
                    }
                )
            else:
                items.append(
                    {
                        "code": code,
                        "condition_status": "해당없음",
                        "verdict": "부적합",
                        "quote": "",
                        "reason": "본문에서 확인되지 않음",
                    }
                )
        return {"items": items}


def fake_cassette(tmp_path) -> Cassette:
    return Cassette(tmp_path / "fake.json", mode="live", ask=FakeDutyAsk())


def test_a_deleted_disclosure_is_detected_and_a_neutral_delete_flips_nothing(tmp_path, monkeypatch):
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


class SplitAsk(FakeDutyAsk):
    """FakeDutyAsk, except the one-call ablation arm never finds the F11 sentence."""

    def __call__(self, model, schema, task, effort="low", **data):
        answer = super().__call__(model, schema, task, effort, **data)
        if schema.__name__ == "AblationJudgments":
            for row in answer["items"]:
                if row["code"] == "F11":
                    row.update(verdict="부적합", quote="", reason="찾지 못함")
        return answer


def test_both_arms_judge_the_same_deletions_chosen_from_what_both_passed(tmp_path, monkeypatch):
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
    cassette = Cassette(tmp_path / "split.json", mode="live", ask=SplitAsk())

    deletions = {
        arm: [
            (row["case"], row["removed_quote"])
            for row in run_duty_flip(Context(model="fake"), cassette, config, arm=arm)["rows"]
        ]
        for arm in ("pipeline", "ablation")
    }

    assert deletions["pipeline"] == deletions["ablation"]
    # F11 is out because the ablation arm did not pass it; 설명15 is out because it would delete
    # the F15 sentence a second time.
    assert [case for case, _ in deletions["pipeline"]] == [
        "drop-F15",
        "drop-F07",
        "drop-설명11",
        "neutral-delete",
    ]


class FallbackAsk(FakeDutyAsk):
    """FakeDutyAsk, except F15 stays 적합 on another sentence once its own sentence is gone."""

    OTHER = (
        "이 카드는 여행을 자주 가는 고객을 위해 만든 상품이며"
        " 다양한 제휴처에서 편하게 쓸 수 있습니다."
    )

    def __call__(self, model, schema, task, effort="low", **data):
        answer = super().__call__(model, schema, task, effort, **data)
        for row in answer["items"]:
            if row["code"] == "F15" and row["verdict"] == "부적합" and self.OTHER in data["text"]:
                row.update(verdict="적합", quote=self.OTHER, reason="다른 문장에 있음")
        return answer


def test_a_miss_resting_on_another_sentence_on_the_page_is_named(tmp_path, monkeypatch):
    from financial_disclosure_review.evaluation import suites

    items = [
        {"code": code, "criterion": f"{code} 기준", "applies_condition": None, "rubric": "r"}
        for code in ("F11", "F15")
    ]
    monkeypatch.setattr(suites, "_in_scope_items", lambda db_path, product_type: items)
    html_path = tmp_path / "page.html"
    html_path.write_text(HTML, encoding="utf-8")
    config = {
        "base_html": str(html_path),
        "classification": {"product_type": "신용카드", "page_type": "상품광고"},
        "prefer_codes": ["F11", "F15"],
    }
    cassette = Cassette(tmp_path / "fallback.json", mode="live", ask=FallbackAsk())

    metrics = metrics_for(run_duty_flip(Context(model="fake"), cassette, config, max_flips=2))

    assert metrics["missed"] == ["F15"]
    assert metrics["missed_with_evidence_on_page"] == ["F15"]


class ForgetfulAsk(FakeDutyAsk):
    """FakeDutyAsk, except the pipeline answers one item only once the neutral sentence is gone."""

    NEUTRAL = "이 카드는 여행을 자주 가는 고객을 위해 만든 상품이며"

    def __call__(self, model, schema, task, effort="low", **data):
        answer = super().__call__(model, schema, task, effort, **data)
        if schema.__name__ == "ExplanationJudgments" and self.NEUTRAL not in data["text"]:
            answer["items"] = answer["items"][:1]
        return answer


def test_a_variant_the_arm_cannot_judge_is_recorded_as_a_failure_not_a_crash(tmp_path, monkeypatch):
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
    cassette = Cassette(tmp_path / "forgetful.json", mode="live", ask=ForgetfulAsk())

    result = run_duty_flip(Context(model="fake"), cassette, config, max_flips=2)
    metrics = metrics_for(result)

    neutral = result["rows"][-1]
    assert neutral["case"] == "neutral-delete" and neutral["after_verdict"] == "판정 실패"
    assert metrics["failed"] == ["neutral-delete"]
    assert metrics["detected"] == 2


def test_the_cassette_is_saved_even_when_a_suite_stops_halfway(tmp_path, monkeypatch):
    import financial_disclosure_review.evaluation as evaluation

    def stop_after_one_answer(ctx, suites, root, cassette, *rest):
        cassette.entries["paid-key"] = {"answer": {"value": "kept"}}
        raise RuntimeError("stopped halfway")

    monkeypatch.setattr(evaluation, "_run_suites", stop_after_one_answer)

    with pytest.raises(RuntimeError, match="stopped halfway"):
        evaluation.run_evaluation(Context(model="fake"), mode="record", eval_dir=tmp_path)

    saved = json.loads((tmp_path / "cassettes" / "fake.json").read_text(encoding="utf-8"))
    assert saved["entries"]["paid-key"]["answer"]["value"] == "kept"


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
            {
                "id": "clean",
                "defect": None,
                "source_quote": "연회비는 20,000원입니다.",
                "rewrite": "1년에 20,000원을 냅니다.",
            },
            {
                "id": "invented",
                "defect": "invented_number",
                "expect_marker": "원문에 없는 수치 포함",
                "source_quote": "연회비는 20,000원입니다.",
                "rewrite": "연회비는 12,000원입니다.",
            },
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


# ---------------------------------------------------------------- salted repeats


def test_a_salt_keeps_a_repeat_apart_and_no_salt_keeps_the_old_key():
    plain = call_key("gpt-5-mini", "Answer", "task", {"text": "가"})
    assert plain == call_key("gpt-5-mini", "Answer", "task", {"text": "가"}, "")
    assert plain != call_key("gpt-5-mini", "Answer", "task", {"text": "가"}, "repeat-2")


def test_a_salted_ask_records_its_own_answer_and_replays_it(tmp_path):
    answers = iter(["첫 답", "두 번째 답"])

    def fake(model, schema, task, effort="low", **data):
        assert "salt" not in data, "the salt must never reach the model"
        return {"value": next(answers)}

    path = tmp_path / "cassette.json"
    recorder = Cassette(path, mode="record", ask=fake)
    assert recorder.ask("m", Answer, "task", text="가")["value"] == "첫 답"
    assert recorder.salted("repeat-2")("m", Answer, "task", text="가")["value"] == "두 번째 답"
    recorder.save()

    player = Cassette(path, mode="replay")
    assert player.ask("m", Answer, "task", text="가")["value"] == "첫 답"
    assert player.salted("repeat-2")("m", Answer, "task", text="가")["value"] == "두 번째 답"
    with pytest.raises(CassetteMissError):
        player.salted("repeat-3")("m", Answer, "task", text="가")


# ---------------------------------------------------------------- keyword baseline


def test_the_keyword_arm_counts_product_words_and_calls_no_model():
    from financial_disclosure_review.evaluation.suites import keyword_classify

    loan = {"product": {"product_name": "카드론"}, "html": "<p>카드론 금리 안내. 카드론 한도.</p>"}
    insurance = {
        "product": {"product_name": "자동차보험"},
        "html": "<p>보험료 할인 특약. 보장 내용. 신용카드로 보험료 결제.</p>",
    }
    assert keyword_classify(loan)["product_type"] == "장기카드대출"
    assert keyword_classify(loan)["page_type"] == "상품광고"
    assert keyword_classify(insurance)["product_type"] == "범위 밖"


# ---------------------------------------------------------------- stability


class DriftingAsk:
    """Answers F11 적합 on the first round and 판정 불가 afterwards; everything else steady."""

    def __init__(self) -> None:
        self.round = 0

    def __call__(self, model, schema, task, effort="low", **data):
        self.round += 1
        items = []
        for item in data["items"]:
            drift = item["code"] == "F11" and self.round > 1
            items.append(
                {
                    "code": item["code"],
                    "condition_status": "불명확" if drift else "해당없음",
                    "verdict": "판정 불가" if drift else "부적합",
                    "quote": "",
                    "reason": "테스트",
                }
            )
            if item["code"] == "F11" and not drift:
                items[-1].update(
                    verdict="적합", quote=FakeDutyAsk.QUOTES["F11"], reason="본문에 있음"
                )
        return {"items": items}


def test_the_stability_suite_names_an_item_whose_answer_moves_between_rounds(tmp_path, monkeypatch):
    from financial_disclosure_review.evaluation import suites

    items = [
        {"code": code, "criterion": f"{code} 기준", "applies_condition": None, "rubric": "r"}
        for code in ("F11", "F07")
    ]
    monkeypatch.setattr(suites, "_in_scope_items", lambda db_path, product_type: items)
    monkeypatch.setattr(
        suites, "classify_page", lambda page, model, ask: {"product_type": "신용카드"}
    )
    html_path = tmp_path / "page.html"
    html_path.write_text(HTML, encoding="utf-8")
    fixtures = tmp_path / "classify"
    fixtures.mkdir()
    (fixtures / "one.json").write_text(
        json.dumps({"url": "u", "product": {}, "html": HTML, "expected": {}}), encoding="utf-8"
    )
    config = {"base_html": str(html_path), "classification": {"product_type": "신용카드"}}
    cassette = Cassette(tmp_path / "c.json", mode="live", ask=DriftingAsk())

    result = suites.run_stability(Context(model="fake"), cassette, fixtures, config, repeats=3)
    metrics = metrics_for(result)

    assert metrics["classification_stable"] == 1
    assert metrics["duty_items"] == 2 and metrics["duty_stable"] == 1
    assert metrics["duty_pass_flips"] == ["F11"]
    assert metrics["duty_unstable"] == [
        {"code": "F11", "verdicts": ["적합", "판정 불가", "판정 불가"]}
    ]


class SteadyPipelineDriftingAblation:
    """The pipeline answers the same every round; the one-call arm moves F11 after round one."""

    def __init__(self) -> None:
        self.ablation_rounds = 0

    def __call__(self, model, schema, task, effort="low", **data):
        drifting = schema.__name__ == "AblationJudgments"
        self.ablation_rounds += int(drifting)
        moved = drifting and self.ablation_rounds > 1
        return {
            "items": [
                {
                    "code": item["code"],
                    "condition_status": "해당없음",
                    "verdict": "판정 불가" if moved and item["code"] == "F11" else "부적합",
                    "quote": "",
                    "reason": "테스트",
                }
                for item in data["items"]
            ]
        }


def test_the_stability_suite_repeats_the_ablation_arm_as_a_baseline(tmp_path, monkeypatch):
    from financial_disclosure_review.evaluation import suites

    items = [
        {"code": code, "criterion": f"{code} 기준", "applies_condition": None, "rubric": "r"}
        for code in ("F11", "F07")
    ]
    monkeypatch.setattr(suites, "_in_scope_items", lambda db_path, product_type: items)
    monkeypatch.setattr(
        suites, "classify_page", lambda page, model, ask: {"product_type": "신용카드"}
    )
    html_path = tmp_path / "page.html"
    html_path.write_text(HTML, encoding="utf-8")
    fixtures = tmp_path / "classify"
    fixtures.mkdir()
    config = {"base_html": str(html_path), "classification": {"product_type": "신용카드"}}
    cassette = Cassette(tmp_path / "c.json", mode="live", ask=SteadyPipelineDriftingAblation())

    result = suites.run_stability(
        Context(model="fake"), cassette, fixtures, config, repeats=3, arms=("pipeline", "ablation")
    )
    metrics = metrics_for(result)

    assert metrics["duty_stable"] == 2
    baseline = metrics["baseline"]["ablation"]
    assert baseline["duty_items"] == 2 and baseline["duty_stable"] == 1
    assert baseline["duty_unstable"] == [
        {"code": "F11", "verdicts": ["부적합", "판정 불가", "판정 불가"]}
    ]
    assert baseline["duty_unstable_kinds"] == {"부적합↔판정 불가": 1}
    assert metrics["duty_unstable_kinds"] == {}
