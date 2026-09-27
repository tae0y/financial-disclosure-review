"""Stub: vector search over the reference DB."""

from pathlib import Path


def search(db_path: str | Path, query: str, kind: str = "", k: int = 5) -> list[dict]:
    """Stub: returns no hits until vector search is built."""
    return []
