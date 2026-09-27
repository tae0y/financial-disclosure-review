"""Every model call goes through here: structured output, image input, and tool-calling turns."""

import json
from typing import Any, cast

from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from openai import OpenAI
from pydantic import BaseModel


def ask(model: str, schema: type[BaseModel], task: str, effort: str = "low", **data) -> dict:
    prompt = task + "".join(
        f"\n{key}={json.dumps(value, ensure_ascii=False)}" for key, value in data.items()
    )
    llm = ChatOpenAI(
        model=model, use_responses_api=True, max_retries=3, reasoning={"effort": effort}
    )
    usage = UsageMetadataCallbackHandler()
    result = llm.with_structured_output(schema, strict=True).invoke(
        prompt, config={"callbacks": [usage]}
    )
    for tokens in usage.usage_metadata.values():
        print(f"    {schema.__name__}: in={tokens['input_tokens']} out={tokens['output_tokens']}")
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
    return response.output_text, (response.usage.model_dump() if response.usage else None)


def call_ask(
    ask_fn, model: str, schema: type[BaseModel], task: str, check, effort: str, salvage=None, **data
) -> dict:
    """One model step with the retry contract: at most 2 attempts, the second one told what went
    wrong. A second answer that still fails check goes to salvage(answer, problems) when given
    (it may downgrade single rows); otherwise it raises. ask_fn is the call to make, so a caller
    can hand in a stand-in instead of `ask`."""
    problems: list[str] = []
    answer = None
    for _ in range(2):
        payload = {**data, "previous_problems": problems} if problems else data
        answer = ask_fn(model, schema, task, effort, **payload)
        problems = check(answer)
        if not problems:
            return answer
    if salvage:
        return salvage(answer, problems)
    raise RuntimeError(f"model call failed twice: {'; '.join(problems)[:400]}")


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
        self, model: str, tools: list[dict], effort: str = "low", max_retries: int = 3
    ) -> None:
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
        reply = self.llm.invoke(self.messages)
        self.messages.append(reply)
        usage = reply.usage_metadata or {}
        return {
            "tool_calls": [dict(call) for call in reply.tool_calls],
            "tokens": usage.get("total_tokens"),
        }
