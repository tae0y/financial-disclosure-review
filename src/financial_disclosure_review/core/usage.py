"""Token metering and run budget cap — instrumentation, not judgment data, so never in State."""

import threading
import time
from dataclasses import dataclass, field

# USD per 1M tokens, (input, output). Assumption, dated 2026-09-27, from the OpenAI price page.
PRICES: dict[str, tuple[float, float]] = {
    "gpt-5": (1.25, 10.00),
    "gpt-5-mini": (0.25, 2.00),
    "gpt-5-nano": (0.05, 0.40),
    "text-embedding-3-small": (0.02, 0.00),
}
UNKNOWN_MODEL_PRICE = (0.25, 2.00)
USD_KRW = 1400.0


class BudgetError(RuntimeError):
    """A run asked for one model call more than its cap allows."""


def price_of(model: str) -> tuple[float, float]:
    """The longest matching prefix wins, so `gpt-5-mini` is not priced as `gpt-5`."""
    for name in sorted(PRICES, key=len, reverse=True):
        if model.startswith(name):
            return PRICES[name]
    return UNKNOWN_MODEL_PRICE


@dataclass
class Meter:
    """One run's model calls; check() raises once max_calls or max_usd (0 disables) is reached."""

    max_calls: int = 60
    max_usd: float = 1.0
    calls: list[dict] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record(self, model: str, step: str, input_tokens: int, output_tokens: int) -> dict:
        price_in, price_out = price_of(model)
        entry = {
            "model": model,
            "step": step,
            "input_tokens": int(input_tokens or 0),
            "output_tokens": int(output_tokens or 0),
            "usd": round(
                (input_tokens or 0) * price_in / 1e6 + (output_tokens or 0) * price_out / 1e6, 6
            ),
        }
        with self._lock:
            self.calls.append(entry)
        return entry

    @property
    def usd(self) -> float:
        return round(sum(call["usd"] for call in self.calls), 6)

    def check(self, step: str = "") -> None:
        """Raise before the next call when a cap is already reached."""
        if self.max_calls and len(self.calls) >= self.max_calls:
            raise BudgetError(
                f"model call cap {self.max_calls} reached before {step or 'the next call'}"
            )
        if self.max_usd and self.usd >= self.max_usd:
            raise BudgetError(
                f"run budget ${self.max_usd} reached (${self.usd}) before {step or 'the next call'}"
            )

    def summary(self) -> dict:
        input_tokens = sum(call["input_tokens"] for call in self.calls)
        output_tokens = sum(call["output_tokens"] for call in self.calls)
        by_step: dict[str, dict] = {}
        for call in self.calls:
            row = by_step.setdefault(
                call["step"], {"calls": 0, "input": 0, "output": 0, "usd": 0.0}
            )
            row["calls"] += 1
            row["input"] += call["input_tokens"]
            row["output"] += call["output_tokens"]
            row["usd"] = round(row["usd"] + call["usd"], 6)
        return {
            "calls": len(self.calls),
            "elapsed_seconds": round(time.time() - self.started_at, 1),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "usd": self.usd,
            "krw": round(self.usd * USD_KRW, 1),
            "usd_krw": USD_KRW,
            "by_step": by_step,
            "caps": {"max_calls": self.max_calls, "max_usd": self.max_usd},
        }


_current = Meter()


def start_run(max_calls: int = 60, max_usd: float = 1.0) -> Meter:
    """Begin metering a run and return its meter. The CLI calls this once per invoke."""
    global _current
    _current = Meter(max_calls=max_calls, max_usd=max_usd)
    return _current


def current() -> Meter:
    return _current
