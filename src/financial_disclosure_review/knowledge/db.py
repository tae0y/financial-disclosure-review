"""Stub: opening the reference DB with the sqlite-vec extension loaded."""

import sqlite3
from pathlib import Path


def connect(db_path: str | Path) -> sqlite3.Connection | None:
    """Stub: returns None until vector search is built. Callers must handle None."""
    return None
