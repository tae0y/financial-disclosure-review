"""Environment-driven settings for both serving processes.

The graph's own settings still travel as `core.context.Context` at invoke time. What lives here is
only deployment shape: ports, paths, the agent's address, credentials and caps.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    return int(raw) if raw else default


def _float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    return float(raw) if raw else default


def _str(name: str, default: str) -> str:
    return os.environ.get(name, "").strip() or default


def _tokens(name: str) -> tuple[str, ...]:
    """Comma-separated so an old and a new token can both be live during a rotation."""
    raw = os.environ.get(name, "")
    return tuple(token.strip() for token in raw.split(",") if token.strip())


@dataclass(frozen=True)
class AgentSettings:
    """The worker process: where its data lives and how much one run may spend."""

    data_dir: str = field(default_factory=lambda: _str("FDR_DATA_DIR", "/app/data"))
    db_path: str = field(default_factory=lambda: _str("FDR_DB_PATH", ""))
    checkpoints: str = field(default_factory=lambda: _str("FDR_CHECKPOINTS", ""))
    rubric_dir: str = field(default_factory=lambda: _str("FDR_RUBRIC_DIR", "/app/rubrics"))
    model: str = field(default_factory=lambda: _str("FDR_MODEL", "gpt-5-mini"))
    max_calls: int = field(default_factory=lambda: _int("FDR_MAX_CALLS", 60))
    max_usd: float = field(default_factory=lambda: _float("FDR_MAX_USD", 1.0))
    concurrency: int = field(default_factory=lambda: _int("FDR_AGENT_CONCURRENCY", 1))

    def resolved_db_path(self) -> str:
        return self.db_path or str(Path(self.data_dir) / "reference.sqlite")

    def resolved_checkpoints(self) -> str:
        return self.checkpoints or str(Path(self.data_dir) / "checkpoints.sqlite")


@dataclass(frozen=True)
class ApiSettings:
    """The gateway process: the agent's address, the job store, and who may call in."""

    agent_url: str = field(default_factory=lambda: _str("FDR_AGENT_URL", "http://agent:8100"))
    jobs_db: str = field(default_factory=lambda: _str("FDR_JOBS_DB", "/app/data/jobs.sqlite"))
    # The issued bearer token. Required: the gateway refuses to start without one, so forgetting
    # it cannot quietly publish an unauthenticated API. Several values allow a rotation.
    api_tokens: tuple[str, ...] = field(default_factory=lambda: _tokens("FDR_API_TOKEN"))
    # Domains a review may be submitted for (a subdomain counts). Empty means any public host;
    # a non-public address is refused either way (`core.urls.url_problem`).
    allowed_hosts: tuple[str, ...] = field(default_factory=lambda: _tokens("FDR_ALLOWED_HOSTS"))
    run_timeout_seconds: float = field(default_factory=lambda: _float("FDR_RUN_TIMEOUT", 1800.0))
    concurrency: int = field(default_factory=lambda: _int("FDR_AGENT_CONCURRENCY", 1))
    job_retention_days: int = field(default_factory=lambda: _int("FDR_JOB_RETENTION_DAYS", 30))
