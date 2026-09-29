"""토큰 계량과 예산 상한: 상한은 호출 전에 막고, 토큰과 금액을 함께 보고한다."""

import pytest

from financial_disclosure_review.core.usage import (
    USD_KRW,
    BudgetError,
    Meter,
    current,
    price_of,
    start_run,
)


def test_a_known_model_uses_its_own_price_and_an_unknown_one_falls_back():
    assert price_of("gpt-5-mini") == (0.25, 2.00)
    assert price_of("gpt-5-mini-2026-01-01") == (0.25, 2.00)
    assert price_of("some-new-model") == (0.25, 2.00)
    assert price_of("gpt-5-nano") == (0.05, 0.40)


def test_the_cost_of_one_call_is_derived_from_the_token_counts():
    meter = Meter()
    entry = meter.record("gpt-5-mini", "DisplayVerdicts", 1_000_000, 1_000_000)
    assert entry["usd"] == 2.25
    assert meter.usd == 2.25
    assert meter.summary()["krw"] == round(2.25 * USD_KRW, 1)


def test_the_summary_groups_the_calls_by_step():
    meter = Meter()
    meter.record("gpt-5-mini", "ClassifyAnswer", 1000, 100)
    meter.record("gpt-5-mini", "ClassifyAnswer", 1000, 100)
    meter.record("gpt-5-mini", "vision", 2000, 50)
    summary = meter.summary()
    assert summary["calls"] == 3
    assert summary["input_tokens"] == 4000
    assert summary["by_step"]["ClassifyAnswer"]["calls"] == 2
    assert summary["by_step"]["vision"]["input"] == 2000
    assert summary["elapsed_seconds"] >= 0


def test_the_call_cap_raises_before_the_next_call():
    meter = Meter(max_calls=2, max_usd=0)
    meter.record("gpt-5-mini", "a", 10, 10)
    meter.check("still fine")
    meter.record("gpt-5-mini", "b", 10, 10)
    with pytest.raises(BudgetError, match="model call cap 2"):
        meter.check("the third call")


def test_the_money_cap_raises_before_the_next_call():
    meter = Meter(max_calls=0, max_usd=0.01)
    meter.record("gpt-5-mini", "a", 100_000, 0)
    with pytest.raises(BudgetError, match=r"budget \$0.01"):
        meter.check("the next call")


def test_a_zero_cap_means_no_cap():
    meter = Meter(max_calls=0, max_usd=0)
    for _ in range(5):
        meter.record("gpt-5", "a", 1_000_000, 1_000_000)
    meter.check("nothing stops this")


def test_start_run_replaces_the_current_meter_so_a_run_starts_from_zero():
    first = start_run(max_calls=3, max_usd=0.1)
    first.record("gpt-5-mini", "a", 10, 10)
    assert current() is first
    second = start_run()
    assert current() is second
    assert second.calls == []
    assert second.max_calls == 60


def test_runs_on_separate_threads_keep_separate_meters():
    import threading

    seen: dict[str, float] = {}
    both_started = threading.Barrier(2)

    def run(name: str, tokens: int) -> None:
        meter = start_run(max_calls=0, max_usd=0)
        both_started.wait()
        current().record("gpt-5-mini", name, tokens, 0)
        seen[name] = meter.usd
        assert current() is meter

    threads = [threading.Thread(target=run, args=(n, t)) for n, t in (("a", 1_000_000), ("b", 0))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert seen == {"a": 0.25, "b": 0.0}


def test_parallel_graph_branches_record_to_the_meter_of_their_run():
    from typing import TypedDict

    from langgraph.graph import END, START, StateGraph

    class S(TypedDict, total=False):
        a: int
        b: int

    def branch(key: str):
        def node(state: S) -> dict:
            current().record("gpt-5-mini", key, 10, 0)
            return {key: 1}

        return node

    builder = StateGraph(S)
    builder.add_node("a", branch("a"))
    builder.add_node("b", branch("b"))
    builder.add_edge(START, "a")
    builder.add_edge(START, "b")
    builder.add_edge("a", END)
    builder.add_edge("b", END)
    meter = start_run(max_calls=0, max_usd=0)
    builder.compile().invoke({})
    assert sorted(call["step"] for call in meter.calls) == ["a", "b"]


def test_work_moved_off_the_thread_records_to_the_callers_meter():
    """The page agent runs its model turns through run_in_thread (sync Playwright)."""
    from financial_disclosure_review.core.threads import run_in_thread

    meter = start_run(max_calls=0, max_usd=0)
    run_in_thread(lambda: current().record("gpt-5-mini", "page_agent", 10, 0))
    assert [call["step"] for call in meter.calls] == ["page_agent"]
