"""tool_spec builds the OpenAI function schema, call_ask holds the retry contract;
ask itself is only exercised with -m use_llm."""

import pytest
from pydantic import BaseModel

from financial_disclosure_review.core.text import locate_quote
from financial_disclosure_review.llm.client import ask, call_ask, tool_spec


class Probe(BaseModel):
    """Probe   the   page."""

    selectors: list[str]


def test_tool_spec_names_the_tool_and_flattens_the_docstring():
    spec = tool_spec("probe_selector", Probe)
    assert spec["type"] == "function"
    assert spec["function"]["name"] == "probe_selector"
    assert spec["function"]["description"] == "Probe the page."
    assert spec["function"]["parameters"]["properties"]["selectors"]["type"] == "array"


def test_tool_spec_leaves_an_undocumented_model_with_an_empty_description():
    class Bare(BaseModel):
        pass

    assert tool_spec("bare", Bare)["function"]["description"] == ""


@pytest.mark.use_llm
def test_ask_returns_the_schema_it_was_given():
    class Answer(BaseModel):
        city: str

    result = ask("gpt-5-nano", Answer, "대한민국의 수도는 어디입니까? city에 도시 이름만 씁니다.")
    assert "서울" in result["city"]


class Judgments(BaseModel):
    """A stand-in answer shape: one row per code."""

    items: list[dict]


def reasons_missing(answer: dict) -> list[str]:
    return [f"{row['code']}: 근거 없음" for row in answer["items"] if not row["reason"].strip()]


def test_call_ask_tells_the_second_attempt_what_went_wrong():
    attempts: list[dict] = []

    def flaky(model, schema, task, effort="low", **data):
        attempts.append(data)
        reason = "" if len(attempts) == 1 else "재시도 후 정상"
        return {"items": [{"code": "X", "reason": reason}]}

    answer = call_ask(flaky, "fake", Judgments, "테스트", reasons_missing, "low")
    assert answer["items"][0]["reason"] == "재시도 후 정상"
    assert len(attempts) == 2
    assert "previous_problems" not in attempts[0]
    assert attempts[1]["previous_problems"] == ["X: 근거 없음"]


def test_call_ask_hands_a_still_bad_answer_to_salvage():
    def always_bad_quote(model, schema, task, effort="low", **data):
        return {"items": [{"code": "Y", "verdict": "적합", "quote": "이 페이지에 없는 문장"}]}

    def check_quote(answer: dict) -> list[str]:
        text = "실제 페이지 텍스트입니다"
        return [
            f"{row['code']}: quote 없음"
            for row in answer["items"]
            if row["quote"] and not locate_quote(text, row["quote"])
        ]

    def salvage(answer: dict, problems: list[str]) -> dict:
        bad = {p.split(":", 1)[0].strip() for p in problems}
        return {
            "items": [
                {**row, "verdict": "판정 불가", "quote": "", "reason": "salvage"}
                if row["code"] in bad
                else row
                for row in answer["items"]
            ]
        }

    salvaged = call_ask(always_bad_quote, "fake", Judgments, "테스트", check_quote, "low", salvage)
    assert salvaged["items"][0]["verdict"] == "판정 불가"
    assert salvaged["items"][0]["reason"] == "salvage"


def test_call_ask_raises_when_salvage_refuses_the_answer():
    def wrong_codes(model, schema, task, effort="low", **data):
        return {"items": [{"code": "Z", "reason": "근거"}]}

    def check_wanted(answer: dict) -> list[str]:
        seen = [row["code"] for row in answer["items"]]
        return [] if seen == ["W"] else [f"codes {seen} != ['W']"]

    def salvage_strict(answer: dict, problems: list[str]) -> dict:
        bad = {p.split(":", 1)[0].strip() for p in problems}
        if not bad <= {"W"}:
            raise RuntimeError(f"model call failed twice: {'; '.join(problems)}")
        return answer

    with pytest.raises(RuntimeError, match="failed twice"):
        call_ask(wrong_codes, "fake", Judgments, "테스트", check_wanted, "low", salvage_strict)


def test_call_ask_raises_without_a_salvage():
    def always_fails(model, schema, task, effort="low", **data):
        return {"items": [{"code": "X", "reason": ""}]}

    with pytest.raises(RuntimeError, match="failed twice"):
        call_ask(always_fails, "fake", Judgments, "테스트", reasons_missing, "low")


def test_call_ask_prints_why_an_attempt_was_rejected(capsys):
    def flaky(model, schema, task, effort="low", **data):
        return {"items": [{"code": "X", "reason": "" if "previous_problems" not in data else "ok"}]}

    call_ask(flaky, "fake", Judgments, "테스트", reasons_missing, "low")
    assert "Judgments attempt 1 rejected: X: 근거 없음" in capsys.readouterr().out


ITEMS = [{"code": "A"}, {"code": "B"}, {"code": "C"}]


def test_call_ask_by_code_re_asks_only_the_rejected_codes():
    asked: list[list[str]] = []

    def one_bad(model, schema, task, effort="low", **data):
        codes = [item["code"] for item in data["items"]]
        asked.append(codes)
        if len(asked) == 1:
            return {"items": [{"code": c, "reason": "" if c == "B" else c} for c in codes]}
        return {"items": [{"code": c, "reason": f"{c} 재판정"} for c in codes]}

    answer = call_ask(
        one_bad, "fake", Judgments, "t", reasons_missing, "low", by_code=True, items=ITEMS
    )
    assert asked == [["A", "B", "C"], ["B"]]
    assert [row["code"] for row in answer["items"]] == ["A", "B", "C"]
    assert answer["items"][1]["reason"] == "B 재판정"


def test_call_ask_by_code_re_asks_everything_when_a_problem_names_no_code():
    asked: list[list[str]] = []

    def drops_a_code(model, schema, task, effort="low", **data):
        codes = [item["code"] for item in data["items"]]
        asked.append(codes)
        keep = codes if len(asked) > 1 else codes[:2]
        return {"items": [{"code": c, "reason": c} for c in keep]}

    def all_codes(answer: dict) -> list[str]:
        seen = sorted(row["code"] for row in answer["items"])
        return [] if seen == ["A", "B", "C"] else [f"codes {seen} != ['A', 'B', 'C']"]

    answer = call_ask(
        drops_a_code, "fake", Judgments, "t", all_codes, "low", by_code=True, items=ITEMS
    )
    assert asked == [["A", "B", "C"], ["A", "B", "C"]]
    assert len(answer["items"]) == 3
