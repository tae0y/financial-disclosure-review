"""tool_spec builds the OpenAI function schema; ask is only exercised with --m use_llm."""

import pytest
from pydantic import BaseModel

from financial_disclosure_review.llm.client import ask, tool_spec


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
