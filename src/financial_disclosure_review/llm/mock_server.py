"""A zero-cost stand-in for the OpenAI API, for end-to-end runs of the review service.

Point the worker at it with `OPENAI_BASE_URL=http://<host>:9000/v1` and any fake key. It answers
the three shapes `llm.client` sends — Responses structured output, Chat Completions tool calls,
and embeddings — with schema-valid content, and never reaches the real API.

It is a plumbing check, not a model: answers are the smallest valid instance of each schema, with
quote fields copied from the page text, one item per code the caller asked about, and "판정 불가"
wherever a verdict enum allows it. Two calls get a meaningful answer:

- classification says "a single 신용카드 product", so the graph runs every node;
- the persona selection loop gets a `choose` built from the reader's free text by simple rules
  (age decade, 사회초년생, a few provinces, "처음"/"금융권" for familiarity).

The page agent gets no tool call, so a review under the mock needs a stored site rule for its URL.

Run: `python -m financial_disclosure_review.llm.mock_server --port 9000 [--log calls.jsonl]`.
"""

import argparse
import json
import re
import time
import uuid
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

EMBED_DIMENSIONS = 1536
UNDECIDED = "판정 불가"


def resolve(schema: dict, root: dict) -> dict:
    while "$ref" in schema:
        name = schema["$ref"].split("/")[-1]
        schema = (root.get("$defs") or root.get("definitions") or {})[name]
    return schema


def synth(schema: dict, root: dict) -> Any:
    """The smallest instance that satisfies the schema; strings are non-empty."""
    schema = resolve(schema, root)
    if "const" in schema:
        return schema["const"]
    if "enum" in schema:
        return UNDECIDED if UNDECIDED in schema["enum"] else schema["enum"][0]
    for key in ("anyOf", "oneOf"):
        if key in schema:
            options = [resolve(o, root) for o in schema[key]]
            if any(o.get("type") == "null" for o in options):
                return None
            return synth(options[0], root)
    if "allOf" in schema:
        return synth(schema["allOf"][0], root)
    kind = schema.get("type")
    if isinstance(kind, list):
        if "null" in kind:
            return None
        kind = kind[0]
    if kind == "object" or "properties" in schema:
        return {name: synth(sub, root) for name, sub in schema.get("properties", {}).items()}
    if kind == "array":
        return [synth(schema.get("items", {}), root) for _ in range(schema.get("minItems", 0))]
    if kind == "string":
        return "mock".ljust(schema.get("minLength", 0), "x")
    if kind == "integer":
        return int(schema.get("minimum", 0))
    if kind == "number":
        return float(schema.get("minimum", 0))
    if kind == "boolean":
        return False
    return None


def prompt_of(body: dict) -> str:
    raw = body.get("input")
    if isinstance(raw, str):
        return raw
    parts: list[str] = []
    for message in raw or []:
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            parts += [c.get("text", "") for c in content if isinstance(c, dict)]
    return "\n".join(parts)


def prompt_data(prompt: str) -> dict:
    """The `key=json` lines `llm.client.ask` appends after the task."""
    data = {}
    for line in prompt.splitlines():
        found = re.match(r"^([A-Za-z_]\w*)=(.*)$", line)
        if found:
            try:
                data[found.group(1)] = json.loads(found.group(2))
            except ValueError:
                pass
    return data


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.chunks: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs) -> None:
        if tag in ("script", "style"):
            self.skip += 1

    def handle_endtag(self, tag) -> None:
        if tag in ("script", "style") and self.skip:
            self.skip -= 1

    def handle_data(self, data) -> None:
        if not self.skip and data.strip():
            self.chunks.append(" ".join(data.split()))


def snippet(data: dict) -> str:
    """A short run of visible page text, so quote checks find it on the page."""
    html = data.get("html")
    if isinstance(html, str) and html:
        parser = _Text()
        parser.feed(html)
        chunks = parser.chunks
    else:
        chunks = [v for v in data.values() if isinstance(v, str)]
    for chunk in chunks:
        if 6 <= len(chunk) <= 40 and re.search(r"[가-힣]", chunk):
            return chunk
    return chunks[0][:20] if chunks else "mock"


def fill_quotes(value: Any, quote: str, key: str = "") -> Any:
    if isinstance(value, dict):
        return {k: fill_quotes(v, quote, k) for k, v in value.items()}
    if isinstance(value, list):
        return [fill_quotes(v, quote, key) for v in value]
    if isinstance(value, str) and ("quote" in key or key == "evidence"):
        return quote
    return value


def mirror_items(answer: Any, schema: dict, data: dict) -> Any:
    """One output item per input item, carrying its code or id, when both sides have `items`."""
    given = data.get("items")
    if isinstance(given, dict):  # keyed by code, as the display evidence is
        given = [{"code": code, "id": code} for code in given]
    prop = (schema.get("properties") or {}).get("items")
    if not isinstance(answer, dict) or not isinstance(given, list) or not prop:
        return answer
    item_schema = resolve(resolve(prop, schema).get("items", {}), schema)
    keys = [k for k in ("code", "id") if k in (item_schema.get("properties") or {})]
    if not keys:
        return answer
    items = []
    for row in given:
        if isinstance(row, dict):
            item = synth(item_schema, schema)
            item.update({k: row[k] for k in keys if k in row})
            items.append(item)
    return {**answer, "items": items}


def structured_answer(name: str, schema: dict, data: dict) -> Any:
    quote = snippet(data)
    if name == "ClassifyAnswer":  # a single card product, so every later node runs
        return {
            "single_product_quote": quote,
            "single_product_reason": "mock",
            "single_product": True,
            "loan_product_quote": quote,
            "loan_product_reason": "mock",
            "loan_product": True,
            "evidence": quote,
            "product_type_reason": "mock",
            "product_type": "신용카드",
            "page_subject": "mock",
            "confidence": "high",
        }
    return fill_quotes(mirror_items(synth(schema, schema), schema, data), quote)


def reader_request(messages: list) -> str:
    for message in messages:
        content = message.get("content")
        text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
        found = re.search(r'"reader_request"\s*:\s*"((?:[^"\\]|\\.)*)"', text or "")
        if found:
            return json.loads(f'"{found.group(1)}"')
    return ""


PROVINCES = ("서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "제주")


def choose_from_text(text: str) -> dict:
    """What a model would plausibly read out of the reader's free text; rules, not a model."""
    filters: dict = {}
    decade = re.search(r"(\d)0\s*대", text)
    if decade:
        low = int(decade.group(1)) * 10
        filters.update(age_min=low, age_max=low + 9)
    if "사회초년생" in text:
        filters.update(age_min=20, age_max=29)
    for province in PROVINCES:
        if province in text:
            filters["province"] = [province]
            break
    hint = "낮음" if "처음" in text else "높음" if "금융권" in text else ""
    return {
        "filters": filters,
        "rationale": f"mock: {text[:80]}",
        "familiarity_hint": hint,
    }


def tool_calls_for(tools: list, messages: list) -> list[tuple[str, dict]]:
    names = [t["function"]["name"] for t in tools]
    if "choose" in names:
        return [("choose", choose_from_text(reader_request(messages)))]
    if "finish" in names:
        params = next(t for t in tools if t["function"]["name"] == "finish")["function"][
            "parameters"
        ]
        return [("finish", synth(params, params))]
    return []


def _response(body: dict, text: str) -> dict:
    return {
        "id": f"resp_{uuid.uuid4().hex}",
        "object": "response",
        "created_at": int(time.time()),
        "status": "completed",
        "model": body.get("model"),
        "output": [
            {
                "type": "message",
                "id": f"msg_{uuid.uuid4().hex}",
                "status": "completed",
                "role": "assistant",
                "content": [{"type": "output_text", "text": text, "annotations": []}],
            }
        ],
        "parallel_tool_calls": True,
        "tool_choice": "auto",
        "tools": [],
        "usage": {
            "input_tokens": 1,
            "output_tokens": 1,
            "total_tokens": 2,
            "input_tokens_details": {"cached_tokens": 0},
            "output_tokens_details": {"reasoning_tokens": 0},
        },
    }


def _completion(body: dict, calls: list[tuple[str, dict]]) -> dict:
    message: dict = {"role": "assistant", "content": None if calls else "no tool call"}
    if calls:
        message["tool_calls"] = [
            {
                "id": f"call_{uuid.uuid4().hex[:12]}",
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)},
            }
            for name, args in calls
        ]
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": body.get("model"),
        "choices": [
            {"index": 0, "message": message, "finish_reason": "tool_calls" if calls else "stop"}
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


def make_handler(log_path: Path | None) -> type[BaseHTTPRequestHandler]:
    def log(entry: dict) -> None:
        if log_path is not None:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            pass

        def _send(self, body: dict, status: int = 200) -> None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            self._send({"status": "ok", "service": "mock-openai"})

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            if self.path.endswith("/responses"):
                fmt = (body.get("text") or {}).get("format") or {}
                if fmt.get("type") == "json_schema":
                    name = fmt.get("name") or ""
                    answer = structured_answer(name, fmt["schema"], prompt_data(prompt_of(body)))
                    text = json.dumps(answer, ensure_ascii=False)
                else:  # an image call wants plain text
                    name, text = "", "{}"
                log({"api": "responses", "schema": name or None, "answer": text[:300]})
                self._send(_response(body, text))
            elif self.path.endswith("/chat/completions"):
                tools, messages = body.get("tools") or [], body.get("messages") or []
                calls = tool_calls_for(tools, messages)
                log(
                    {
                        "api": "chat",
                        "tools": [t["function"]["name"] for t in tools],
                        "reader_request": reader_request(messages) or None,
                        "calls": calls,
                    }
                )
                self._send(_completion(body, calls))
            elif self.path.endswith("/embeddings"):
                inputs = body.get("input") or []
                inputs = [inputs] if isinstance(inputs, str) else inputs
                log({"api": "embeddings", "n": len(inputs)})
                data = [
                    {"object": "embedding", "index": i, "embedding": [0.0] * EMBED_DIMENSIONS}
                    for i in range(len(inputs))
                ]
                usage = {"prompt_tokens": 1, "total_tokens": 1}
                self._send(
                    {"object": "list", "data": data, "model": body.get("model"), "usage": usage}
                )
            else:
                self._send({"error": {"message": f"mock has no route {self.path}"}}, 404)

    return Handler


def serve(host: str = "127.0.0.1", port: int = 9000, log_path: str | Path | None = None):
    """A bound, not yet serving, server; call `serve_forever()` on it."""
    return ThreadingHTTPServer((host, port), make_handler(Path(log_path) if log_path else None))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Zero-cost stand-in for the OpenAI API.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--log", default=None, help="append every call to this JSONL file")
    args = parser.parse_args(argv)
    server = serve(args.host, args.port, args.log)
    print(f"mock OpenAI API on http://{args.host}:{args.port}/v1", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
