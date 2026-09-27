"""The job store: one SQLite file, one row per submitted review.

A review takes minutes and Cloudflare cuts an idle HTTP response off long before that, so the
gateway answers 202 and the caller polls. That makes the job row the contract, which means it has
to survive a container restart — hence a file rather than a dict in memory.

Every method is blocking SQLite. Callers are async, so they go through
`starlette.concurrency.run_in_threadpool`; the helpers here stay plain functions so tests can
drive them directly.
"""

import json
import sqlite3
import threading
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ..schemas import Job, JobStatus, RunResult

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id      TEXT PRIMARY KEY,
    status      TEXT NOT NULL,
    kind        TEXT NOT NULL DEFAULT 'review',
    url         TEXT,
    thread_id   TEXT,
    model       TEXT,
    created_at  TEXT NOT NULL,
    started_at  TEXT,
    finished_at TEXT,
    error       TEXT,
    result      TEXT
);
CREATE INDEX IF NOT EXISTS jobs_created_at ON jobs (created_at DESC);
CREATE INDEX IF NOT EXISTS jobs_status ON jobs (status);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _parse(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


class JobStore:
    """Thread-safe enough for one uvicorn process: WAL plus a lock around each statement."""

    def __init__(self, path: str) -> None:
        self.path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        with self._lock:
            if path != ":memory:":
                self._db.execute("PRAGMA journal_mode=WAL")
            self._db.executescript(SCHEMA)
            self._db.commit()

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def create(
        self,
        *,
        kind: str = "review",
        url: str | None = None,
        thread_id: str | None = None,
        model: str | None = None,
    ) -> Job:
        job_id = uuid.uuid4().hex
        created = _now()
        with self._lock:
            self._db.execute(
                "INSERT INTO jobs (job_id, status, kind, url, thread_id, model, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (job_id, JobStatus.queued.value, kind, url, thread_id, model, created),
            )
            self._db.commit()
        return Job(
            job_id=job_id,
            status=JobStatus.queued,
            kind=kind,  # type: ignore[arg-type]
            url=url,
            thread_id=thread_id,
            model=model,
            created_at=datetime.fromisoformat(created),
        )

    def mark_running(self, job_id: str) -> None:
        with self._lock:
            self._db.execute(
                "UPDATE jobs SET status = ?, started_at = ? WHERE job_id = ?",
                (JobStatus.running.value, _now(), job_id),
            )
            self._db.commit()

    def mark_succeeded(self, job_id: str, result: RunResult) -> None:
        with self._lock:
            self._db.execute(
                "UPDATE jobs SET status = ?, finished_at = ?, thread_id = ?, result = ?,"
                " error = NULL WHERE job_id = ?",
                (
                    JobStatus.succeeded.value,
                    _now(),
                    result.thread_id,
                    result.model_dump_json(),
                    job_id,
                ),
            )
            self._db.commit()

    def mark_failed(self, job_id: str, error: str, status: JobStatus = JobStatus.failed) -> None:
        with self._lock:
            self._db.execute(
                "UPDATE jobs SET status = ?, finished_at = ?, error = ? WHERE job_id = ?",
                (status.value, _now(), error[:4000], job_id),
            )
            self._db.commit()

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            row = self._db.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return self._job(row) if row else None

    def list(self, *, limit: int = 50, status: JobStatus | None = None) -> list[Job]:
        query = "SELECT * FROM jobs"
        params: list[Any] = []
        if status is not None:
            query += " WHERE status = ?"
            params.append(status.value)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._lock:
            rows = self._db.execute(query, params).fetchall()
        return [self._job(row) for row in rows]

    def close_out_in_flight(self, reason: str) -> int:
        """Give every queued or running row a terminal status, and say why.

        A `running` row with no process behind it would make a caller poll for ever. Both ends of
        the process lifetime call this: shutdown closes out what it cancelled, and boot closes out
        whatever a crash left behind. It is never called from inside the cancelled task itself —
        a cancelled coroutine cannot reach another await point to write the row.
        """
        with self._lock:
            cursor = self._db.execute(
                "UPDATE jobs SET status = ?, finished_at = ?, error = ? WHERE status IN (?, ?)",
                (
                    JobStatus.interrupted.value,
                    _now(),
                    reason,
                    JobStatus.queued.value,
                    JobStatus.running.value,
                ),
            )
            self._db.commit()
        return cursor.rowcount

    def purge_older_than(self, days: int) -> int:
        """Finished rows past the retention window. Checkpoints under `data/` are untouched."""
        if days <= 0:
            return 0
        cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
        with self._lock:
            cursor = self._db.execute(
                "DELETE FROM jobs WHERE created_at < ? AND status IN (?, ?, ?)",
                (
                    cutoff,
                    JobStatus.succeeded.value,
                    JobStatus.failed.value,
                    JobStatus.interrupted.value,
                ),
            )
            self._db.commit()
        return cursor.rowcount

    @staticmethod
    def _job(row: sqlite3.Row) -> Job:
        raw = row["result"]
        return Job(
            job_id=row["job_id"],
            status=JobStatus(row["status"]),
            kind=row["kind"],
            url=row["url"],
            thread_id=row["thread_id"],
            model=row["model"],
            created_at=datetime.fromisoformat(row["created_at"]),
            started_at=_parse(row["started_at"]),
            finished_at=_parse(row["finished_at"]),
            error=row["error"],
            result=RunResult.model_validate(json.loads(raw)) if raw else None,
        )
