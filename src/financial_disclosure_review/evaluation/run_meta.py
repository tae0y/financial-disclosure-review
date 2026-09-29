"""What an eval result measured: implementation, code revision, prompts and gold (audit R3).

A result file written without this cannot be told apart from one of an earlier generation of
the same component (e.g. two prompts of the same judging node).
"""

import hashlib
import json
import subprocess
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]


def _git(repo: Path, *args: str) -> str:
    try:
        done = subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, text=True, timeout=10, check=True
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout.strip()


def _gold(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"path": str(path), "missing": True}
    data = path.read_bytes()
    version = ""
    try:
        parsed = json.loads(data)
        if isinstance(parsed, Mapping):
            version = str(parsed.get("version") or parsed.get("updated") or "")
    except ValueError:
        pass
    return {"path": str(path), "sha256": _sha(data), "version": version}


def run_meta(
    implementation: str,
    *,
    prompts: Mapping[str, str] | None = None,
    gold: str | Path | None = None,
    repo: str | Path = REPO,
) -> dict[str, Any]:
    """`{implementation, commit, dirty, prompt_sha256, gold, recorded_at}` for one result.

    `dirty` is true when src/, eval/ or assets/ have uncommitted changes, since then the commit
    alone does not identify the code that ran.
    """
    repo = Path(repo)
    commit = _git(repo, "rev-parse", "--short=12", "HEAD") or "unknown"
    dirty = bool(_git(repo, "status", "--porcelain", "--", "src", "eval", "assets"))
    return {
        "implementation": implementation,
        "commit": commit,
        "dirty": dirty,
        "prompt_sha256": {
            name: _sha(text.encode("utf-8")) for name, text in (prompts or {}).items()
        },
        "gold": _gold(Path(gold)) if gold else None,
        "recorded_at": datetime.now().isoformat(timespec="seconds"),
    }
