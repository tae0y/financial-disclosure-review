"""Recording model answers so a paid evaluation can be replayed for free.

An evaluation whose numbers cannot be re-derived is worth little, and re-deriving them by paying
again is worth little too. Every call made during a live run is written to a cassette keyed by
what was sent, so a later run replays the same answers and produces the same table.

The key is a hash of (model, schema, task, data). Any change to a prompt or to the input html
changes the key, so a replay cannot silently answer a different question than the one recorded.
"""

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class CassetteMissError(RuntimeError):
    """Replay was asked for a call the cassette does not hold."""


def call_key(model: str, schema_name: str, task: str, data: dict) -> str:
    payload = json.dumps(
        {"model": model, "schema": schema_name, "task": task, "data": data},
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )
    return sha256(payload.encode("utf-8")).hexdigest()[:32]


class Cassette:
    """A recorded set of model answers, used in place of `llm.client.ask`.

    `mode="replay"` answers only from the file and raises on a miss. `mode="record"` calls the
    real model and stores the answer. `mode="live"` calls the model and stores nothing.
    """

    def __init__(self, path: str | Path, mode: str = "replay", ask=None) -> None:
        self.path = Path(path)
        self.mode = mode
        self.entries: dict[str, dict] = {}
        self.hits = 0
        self.misses = 0
        if self.path.exists():
            self.entries = json.loads(self.path.read_text(encoding="utf-8")).get("entries", {})
        if mode in ("record", "live") and ask is None:
            from ..llm.client import ask as real_ask

            ask = real_ask
        self._ask = ask

    def ask(self, model: str, schema: type[BaseModel], task: str, effort: str = "low", **data):
        key = call_key(model, schema.__name__, task, data)
        if self.mode == "replay" or (self.mode == "record" and key in self.entries):
            entry = self.entries.get(key)
            if entry is None:
                self.misses += 1
                raise CassetteMissError(
                    f"cassette {self.path.name} has no {schema.__name__} call for this input."
                    " Re-run with --live --record to add it."
                )
            self.hits += 1
            return schema.model_validate(entry["answer"]).model_dump()
        if self._ask is None:
            raise RuntimeError("no ask function to call")
        answer = self._ask(model, schema, task, effort, **data)
        if self.mode == "record":
            self.entries[key] = {
                "schema": schema.__name__,
                "model": model,
                "label": task.strip().splitlines()[0][:80],
                "answer": answer,
            }
        return answer

    def save(self) -> str:
        if self.mode != "record":
            return ""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                {"note": "recorded model answers; replayed by financial_disclosure_review evaluate",
                 "entries": self.entries},
                ensure_ascii=False,
                indent=1,
            ),
            encoding="utf-8",
        )
        return str(self.path)

    def stats(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "entries": len(self.entries),
            "hits": self.hits,
            "misses": self.misses,
        }
