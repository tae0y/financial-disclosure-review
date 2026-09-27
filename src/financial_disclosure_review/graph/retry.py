"""Stub: deciding which modules a failed verification sends the graph back to."""

from collections.abc import Mapping
from typing import Any


def plan_retry(verification: Mapping[str, Any]) -> dict:
    """Stub: returns no state changes yet."""
    return {}
