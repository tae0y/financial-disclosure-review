"""Supplementary explanations of the page's facts for one reviewed reader profile."""

from .generate import generate_persona_explanation
from .ledger import build_fact_ledger
from .profiles import PROFILE_ALLOWLIST, resolve_profile

__all__ = [
    "PROFILE_ALLOWLIST",
    "build_fact_ledger",
    "generate_persona_explanation",
    "resolve_profile",
]
