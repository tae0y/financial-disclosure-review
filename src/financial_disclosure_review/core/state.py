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


class EvidenceCards(TypedDict, total=False):
    status: Any
    reason: Any
    sources: Any
    cards: Any
    rejected: Any
    coverage_gaps: Any
    model_calls: Any


class DisplayCheck(TypedDict, total=False):
    items: Any
    judgments: Any


class PersonaExplanation(TypedDict, total=False):
    """A reader-tailored plain overview shown beside the page; never a rewrite or a verdict."""

    status: Any
    reason: Any
    profile: Any
    # How the reader was chosen (uuid / attributes / agent / default / fallback) and the
    # selection agent's trace; kept so a retry writes for the same reader.
    selection: Any
    overview: Any  # [summary paragraph, advice paragraph]
    advice_codes: Any  # the explanation-duty codes the advice paragraph recommends checking
    problems: Any
    html: Any
    controls: Any


class AdDisclosureCheck(TypedDict, total=False):
    items: Any
    original: Any
    overview: Any
    fidelity: Any
    # Explanation-duty items for the product type, left to the product documents; not judged.
    deferred: Any


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
    evidence_cards: EvidenceCards
    display_check: DisplayCheck
    persona_explanation: PersonaExplanation
    ad_disclosure_check: AdDisclosureCheck
    verification: Verification
    report: Report


def empty_state() -> State:
    """Every module key set to an empty dict, as the graph expects at invoke time."""
    return {key: {} for key in State.__annotations__}  # type: ignore[return-value]
