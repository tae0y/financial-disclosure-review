"""Opening the reference DB with the sqlite-vec extension loaded."""

import sqlite3
from pathlib import Path

import sqlite_vec

# Verified against the installed sqlite-vec 0.1.9 (`SELECT vec_version()` returns 'v0.1.9'):
# vectors go in a `CREATE VIRTUAL TABLE ... USING vec0(key TEXT PRIMARY KEY, col float[N]
# distance_metric=cosine)` table, are written as `sqlite_vec.serialize_float32(list)`, and are
# read back with `WHERE col MATCH ? AND k = ?` — a KNN query without `k` or `LIMIT` is refused.
VECTOR_LOAD_HINT = (
    "sqlite-vec could not be loaded. It needs a Python built with sqlite3"
    " extension support (`enable_load_extension`); the Homebrew 3.12 venv has it."
)


def connect(db_path: str | Path, read_only: bool = False) -> sqlite3.Connection:
    """The DB with sqlite-vec loaded (unloaded right after); RuntimeError if it can't load."""
    path = Path(db_path)
    if read_only:
        conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path, isolation_level=None)
    try:
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
    except (AttributeError, sqlite3.OperationalError) as error:
        conn.close()
        raise RuntimeError(f"{VECTOR_LOAD_HINT} ({error})") from error
    return conn
