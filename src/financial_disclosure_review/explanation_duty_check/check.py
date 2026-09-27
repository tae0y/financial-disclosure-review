"""Stub: judging the original and plain-language text against the explanation-duty items."""

from collections.abc import Mapping
from typing import Any

from ..core.context import Context


def check_duty(
    page: Mapping[str, Any],
    classification: Mapping[str, Any],
    plain: Mapping[str, Any],
    previous: Mapping[str, Any] | None,
    ctx: Context,
) -> dict:
    """Stub: returns no ExplanationDutyCheck fields yet. Arguments are provisional."""
    return {}
