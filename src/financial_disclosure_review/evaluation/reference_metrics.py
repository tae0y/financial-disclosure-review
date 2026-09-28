"""Metrics for `knowledge.reference.retrieve_reference_cases` against a gold file.

A pure function over already-computed results: it never calls `retrieve_reference_cases`
itself, so it stays offline and cheap to run from a test or a small script. The caller runs
retrieval (or reads recorded results) and hands both sides in, positionally paired.
"""

from collections.abc import Mapping, Sequence
from typing import Any

PARTIAL_DETECTABILITY = ("partial", "review_required", "out_of_scope")


def _linked_case_ids(result: Mapping[str, Any]) -> set[str]:
    return {link["case_id"] for link in result.get("links", [])}


def _has_page_only_partial(result: Mapping[str, Any]) -> bool:
    return any(
        link.get("page_only_detectability") in PARTIAL_DETECTABILITY
        for link in result.get("links", [])
    )


def compute_reference_metrics(
    gold: Sequence[Mapping[str, Any]], results: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """`gold[i]` and `results[i]` are the same entry: entry `i`'s expectation and the retrieval
    output for it (`retrieve_reference_cases`'s return value, or just its `links`-bearing dict).

    `gold[i]` fields used: `expected_case_ids` (list, may be empty) and
    `expected_page_only_partial` (bool).

    Returns:
        recall: of every expected case_id across the gold set, the fraction that appears in the
            matching result's `links`.
        false_link_rate: of every case_id a result linked, the fraction that was not expected
            for that entry (0.0 when nothing was linked).
        partial_accuracy: fraction of entries where whether any kept link carries a
            partial/review_required/out_of_scope `page_only_detectability` matches
            `expected_page_only_partial`.
        n: number of gold entries scored.
    """
    if len(gold) != len(results):
        raise ValueError(f"gold has {len(gold)} entries, results has {len(results)}")

    total_expected = 0
    hits = 0
    total_linked = 0
    false_links = 0
    partial_correct = 0

    for entry, result in zip(gold, results):
        expected = set(entry.get("expected_case_ids") or [])
        linked = _linked_case_ids(result)
        total_expected += len(expected)
        hits += len(expected & linked)
        total_linked += len(linked)
        false_links += len(linked - expected)
        if bool(entry.get("expected_page_only_partial")) == _has_page_only_partial(result):
            partial_correct += 1

    return {
        "recall": round(hits / total_expected, 4) if total_expected else 1.0,
        "false_link_rate": round(false_links / total_linked, 4) if total_linked else 0.0,
        "partial_accuracy": round(partial_correct / len(gold), 4) if gold else 1.0,
        "n": len(gold),
    }
