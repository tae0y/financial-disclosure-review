"""A scripted stand-in for llm.client.ToolChat, so the discovery loop can be driven offline."""


class ScriptedChat:
    """Plays back a fixed script of tool calls, one list of calls per model turn.

    `script` is a list of turns; each turn is a list of `{"name": ..., "args": {...}}` dicts,
    mirroring what the model would call in one turn. Once the script is exhausted, `turn()`
    returns no tool calls (matching how `discover()` nudges a model that goes quiet), so an
    unfinished script drives the loop to `TurnsExhaustedError` instead of raising by itself.
    """

    def __init__(self, script: list[list[dict]]):
        self.script = list(script)
        self.step = 0
        self.system_prompt = ""
        self.messages: list[str] = []
        self.results: list[tuple[str, str]] = []

    def system(self, text: str) -> None:
        self.system_prompt = text

    def user(self, text: str) -> None:
        self.messages.append(text)

    def tool_result(self, call_id: str, body: str) -> None:
        self.results.append((call_id, body))

    def turn(self) -> dict:
        if self.step >= len(self.script):
            return {"tool_calls": [], "tokens": 0}
        calls = self.script[self.step]
        self.step += 1
        return {
            "tool_calls": [
                {"id": f"call-{self.step}-{i}", "name": c["name"], "args": c["args"]}
                for i, c in enumerate(calls)
            ],
            "tokens": 0,
        }
