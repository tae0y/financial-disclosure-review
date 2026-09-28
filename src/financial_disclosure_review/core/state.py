"""Graph State: one top-level key per module. A node writes only its own module's key."""

from typing import Any, TypedDict


class Product(TypedDict, total=False):
    product_name: Any
    summary: Any
    evidence: Any


class ProductPage(TypedDict, total=False):
    url: Any
    product: Product
    actions: Any
    snapshots: Any
    html: Any
    # 완료 | 조사 불충분 | 수집 실패, and the machine-readable reason the agent loop stopped.
    status: Any
    stop_reason: Any
    error: Any
    coverage: Any
    agent_trace: Any


class Classification(TypedDict, total=False):
    product_type: Any
    page_type: Any
    reason: Any


class CaseSearch(TypedDict, total=False):
    queries: Any
    hits: Any
    status: Any
    reason: Any


class DisplayCheck(TypedDict, total=False):
    items: Any
    judgments: Any


class PlainLanguage(TypedDict, total=False):
    items: Any
    draft: Any
    html: Any
    term_refs: Any
    accepted_blocks: Any
    contract_errors: Any


class ExplanationDutyCheck(TypedDict, total=False):
    items: Any
    original: Any
    plain: Any
    fidelity: Any


class Verification(TypedDict, total=False):
    passed: Any
    reasons: Any
    failed_modules: Any
    feedback: Any
    loop_count: Any
    retry_target: Any
    retry_modules: Any
    retry_history: Any


class Report(TypedDict, total=False):
    status: Any
    decision: Any
    actions: Any
    summary: Any
    findings: Any
    limits: Any
    cost: Any
    markdown: Any


class State(TypedDict):
    product_page: ProductPage
    classification: Classification
    case_search: CaseSearch
    display_check: DisplayCheck
    plain_language: PlainLanguage
    explanation_duty_check: ExplanationDutyCheck
    verification: Verification
    report: Report


def empty_state() -> State:
    """Every module key set to an empty dict, as the graph expects at invoke time."""
    return {key: {} for key in State.__annotations__}  # type: ignore[return-value]
