"""Every model call goes through here: structured output, image input, and tool-calling turns."""

import json
from typing import Any, cast

from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from openai import OpenAI
from pydantic import BaseModel

from ..core.usage import current


def ask(model: str, schema: type[BaseModel], task: str, effort: str = "low", **data) -> dict:
    prompt = task + "".join(
        f"\n{key}={json.dumps(value, ensure_ascii=False)}" for key, value in data.items()
    )
    meter = current()
    meter.check(schema.__name__)
    llm = ChatOpenAI(
        model=model, use_responses_api=True, max_retries=3, reasoning={"effort": effort}
    )
    usage = UsageMetadataCallbackHandler()
    result = llm.with_structured_output(schema, strict=True).invoke(
        prompt, config={"callbacks": [usage]}
    )
    for tokens in usage.usage_metadata.values():
        entry = meter.record(
            model, schema.__name__, tokens["input_tokens"], tokens["output_tokens"]
        )
        print(
            f"    {schema.__name__}: in={entry['input_tokens']} out={entry['output_tokens']}"
            f" ${entry['usd']:.5f}"
        )
    return schema.model_validate(result).model_dump()


def ask_images(
    model: str,
    prompt: str,
    images: list[str],
    effort: str = "low",
    max_output_tokens: int = 1200,
    timeout: int = 90,
) -> tuple[str, dict | None]:
    """One image call. images are base64 PNGs, shown in the given order. Returns (text, usage)."""
    meter = current()
    meter.check("vision")
    content = [{"type": "input_text", "text": prompt}] + [
        {"type": "input_image", "image_url": "data:image/png;base64," + png, "detail": "high"}
        for png in images
    ]
    response = OpenAI(max_retries=0, timeout=timeout).responses.create(
        model=model,
        reasoning=cast(Any, {"effort": effort}),
        max_output_tokens=max_output_tokens,
        input=cast(Any, [{"role": "user", "content": content}]),
    )
    tokens = response.usage.model_dump() if response.usage else None
    if tokens:
        meter.record(model, "vision", tokens.get("input_tokens", 0), tokens.get("output_tokens", 0))
    return response.output_text, tokens


def call_ask(
    ask_fn,
    model: str,
    schema: type[BaseModel],
    task: str,
    check,
    effort: str,
    salvage=None,
    *,
    by_code: bool = False,
    **data,
) -> dict:
    """One model step: 2 attempts max, then salvage(answer, problems) or raise; ask_fn stubs ask.

    With by_code, `data["items"]` and the answer's `items` are rows keyed by `code`, and problems
    read `"<code>: ..."`: when every problem names one of the asked codes, the second attempt asks
    for those codes only and merges its rows into the first answer.
    """
    answer = ask_fn(model, schema, task, effort, **data)
    problems = check(answer)
    if not problems:
        return answer
    print(f"    {schema.__name__} attempt 1 rejected: {'; '.join(problems)[:300]}")
    answer = _second_attempt(ask_fn, model, schema, task, effort, data, answer, problems, by_code)
    problems = check(answer)
    if not problems:
        return answer
    print(f"    {schema.__name__} attempt 2 rejected: {'; '.join(problems)[:300]}")
    if salvage:
        return salvage(answer, problems)
    raise RuntimeError(f"model call failed twice: {'; '.join(problems)[:400]}")


def _second_attempt(ask_fn, model, schema, task, effort, data, answer, problems, by_code) -> dict:
    payload = {**data, "previous_problems": problems}
    if by_code:
        asked = [item.get("code") for item in data.get("items") or []]
        rows = answer.get("items") or []
        bad = {str(problem).split(":", 1)[0].strip() for problem in problems}
        if bad <= set(asked) and sorted(row.get("code") for row in rows) == sorted(asked):
            items = [item for item in data["items"] if item.get("code") in bad]
            retry = ask_fn(model, schema, task, effort, **{**payload, "items": items})
            redone = {r.get("code"): r for r in retry.get("items") or [] if r.get("code") in bad}
            # A code the retry left out keeps its rejected row, so check() still reports it.
            return {**answer, "items": [redone.get(row.get("code"), row) for row in rows]}
    return ask_fn(model, schema, task, effort, **payload)


def tool_spec(name: str, model: type[BaseModel]) -> dict:
    schema = model.model_json_schema()
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": " ".join((model.__doc__ or "").split()),
            "parameters": schema,
        },
    }


class ToolChat:
    """One tool-calling conversation. Holds the message list so callers only pass and read dicts."""

    def __init__(
        self,
        model: str,
        tools: list[dict],
        effort: str = "low",
        max_retries: int = 3,
        label: str = "discover",
    ) -> None:
        self.model, self.label = model, label
        self.llm = ChatOpenAI(
            model=model, reasoning_effort=effort, max_retries=max_retries
        ).bind_tools(tools)
        self.messages: list = []

    def system(self, text: str) -> None:
        self.messages.append(SystemMessage(text))

    def user(self, text: str) -> None:
        self.messages.append(HumanMessage(text))

    def tool_result(self, call_id: str, body: str) -> None:
        self.messages.append(ToolMessage(content=body, tool_call_id=call_id))

    def turn(self) -> dict:
        """One model turn. Returns the requested tool calls and the turn's token total."""
        meter = current()
        meter.check(self.label)
        reply = self.llm.invoke(self.messages)
        self.messages.append(reply)
        usage = reply.usage_metadata or {}
        meter.record(
            self.model, self.label, usage.get("input_tokens", 0), usage.get("output_tokens", 0)
        )
        return {
            "tool_calls": [dict(call) for call in reply.tool_calls],
            "tokens": usage.get("total_tokens"),
        }
