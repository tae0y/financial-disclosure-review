"""Stub: verifying the three modules' answers before the report."""

from collections.abc import Mapping
from typing import Any

from ..core.context import Context


def verify(
    display: Mapping[str, Any],
    plain: Mapping[str, Any],
    duty: Mapping[str, Any],
    loop_count: int,
    ctx: Context,
) -> dict:
    """Stub: returns no Verification fields yet. Arguments are provisional."""
    return {}
