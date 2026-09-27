"""Stub: rewriting the page's disclosures in plain language."""

from collections.abc import Mapping
from typing import Any

from ..core.context import Context


def write_plain(
    page: Mapping[str, Any],
    classification: Mapping[str, Any],
    feedback: Any,
    ctx: Context,
) -> dict:
    """Stub: returns no PlainLanguage fields yet. Arguments are provisional."""
    return {}
