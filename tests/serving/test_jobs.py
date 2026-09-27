"""The job store: the row is the API contract, so no path may leave it mid-flight."""

from datetime import UTC, datetime, timedelta

import pytest

from financial_disclosure_review.serving.api.jobs import JobStore
from financial_disclosure_review.serving.schemas import JobStatus, RunResult


@pytest.fixture
def store(tmp_path) -> JobStore:
    opened = JobStore(str(tmp_path / "jobs.sqlite"))
    yield opened
    opened.close()


def test_create_starts_queued(store: JobStore) -> None:
    job = store.create(url="https://example.test/card", model="gpt-5-mini")
    assert job.status is JobStatus.queued
    assert job.started_at is None and job.finished_at is None
    assert store.get(job.job_id) == job


def test_success_records_the_result_and_the_thread(store: JobStore) -> None:
    job = store.create(url="https://example.test/card")
    store.mark_running(job.job_id)
    store.mark_succeeded(
        job.job_id,
        RunResult(thread_id="review-260927-101500", status="검토 완료", report={"markdown": "# r"}),
    )
    done = store.get(job.job_id)
    assert done is not None
    assert done.status is JobStatus.succeeded
    assert done.thread_id == "review-260927-101500"
    assert done.result is not None and done.result.report["markdown"] == "# r"
    assert done.started_at is not None and done.finished_at is not None


def test_failure_keeps_the_message_and_clears_no_result(store: JobStore) -> None:
    job = store.create(url="https://example.test/card")
    store.mark_running(job.job_id)
    store.mark_failed(job.job_id, "BudgetExceeded: run budget $1.0 reached")
    failed = store.get(job.job_id)
    assert failed is not None
    assert failed.status is JobStatus.failed
    assert failed.result is None
    assert "BudgetExceeded" in (failed.error or "")


def test_close_out_marks_rows_a_restart_abandoned(tmp_path) -> None:
    path = str(tmp_path / "jobs.sqlite")
    first = JobStore(path)
    queued = first.create(url="https://example.test/a")
    running = first.create(url="https://example.test/b")
    first.mark_running(running.job_id)
    first.close()

    second = JobStore(path)
    assert (
        second.close_out_in_flight(
            "the gateway restarted while this job was in flight; submit it again"
        )
        == 2
    )
    for job_id in (queued.job_id, running.job_id):
        row = second.get(job_id)
        assert row is not None and row.status is JobStatus.interrupted
        assert "restarted" in (row.error or "")
    second.close()


def test_close_out_leaves_finished_rows_alone(store: JobStore) -> None:
    job = store.create(url="https://example.test/card")
    store.mark_succeeded(job.job_id, RunResult(thread_id="t"))
    assert store.close_out_in_flight("restarted") == 0
    row = store.get(job.job_id)
    assert row is not None and row.status is JobStatus.succeeded


def test_list_filters_by_status_and_is_newest_first(store: JobStore) -> None:
    first = store.create(url="https://example.test/1")
    second = store.create(url="https://example.test/2")
    store.mark_succeeded(second.job_id, RunResult(thread_id="t"))
    assert [job.job_id for job in store.list()] == [second.job_id, first.job_id]
    assert [job.job_id for job in store.list(status=JobStatus.queued)] == [first.job_id]


def test_purge_drops_finished_rows_past_the_window_only(store: JobStore) -> None:
    old_done = store.create(url="https://example.test/old-done")
    old_queued = store.create(url="https://example.test/old-queued")
    store.mark_succeeded(old_done.job_id, RunResult(thread_id="t"))
    stale = (datetime.now(UTC) - timedelta(days=40)).isoformat()
    store._db.execute("UPDATE jobs SET created_at = ?", (stale,))
    store._db.commit()

    assert store.purge_older_than(30) == 1
    assert store.get(old_done.job_id) is None
    assert store.get(old_queued.job_id) is not None
    assert store.purge_older_than(0) == 0
