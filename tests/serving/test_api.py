"""The gateway, driven with a stub worker: no graph, no model call, no browser.

What is under test is the job protocol — 202 then poll — and the auth gate, not the review itself.
"""

import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from financial_disclosure_review.serving.api.app import agent_of, create_app
from financial_disclosure_review.serving.api.client import AgentError
from financial_disclosure_review.serving.api.jobs import JobStore
from financial_disclosure_review.serving.schemas import JobStatus, RunResult
from financial_disclosure_review.serving.settings import ApiSettings

URL = "https://example.test/card/apply"


class StubAgent:
    """Answers like the worker would: a slow success, a refusal, or a crash."""

    def __init__(self, result: RunResult | None = None, error: Exception | None = None) -> None:
        self.result = result or RunResult(
            thread_id="review-260927-101500",
            url=URL,
            status="검토 완료",
            decision="담당자 확인 후 쉬운말 게시 가능",
            report={"markdown": "# 검토 보고서\n\n본문"},
            cost={"calls": 12, "usd": 0.031},
            elapsed_seconds=94.2,
        )
        self.error = error
        self.calls: list[dict] = []

    async def run(self, request) -> RunResult:
        self.calls.append({"kind": "review", "url": str(request.url)})
        if self.error:
            raise self.error
        return self.result

    async def rerun(self, request) -> RunResult:
        self.calls.append({"kind": "rerun", "thread_id": request.thread_id})
        if self.error:
            raise self.error
        return self.result

    async def readyz(self) -> dict:
        return {"status": "ok", "service": "agent"}


def build(tmp_path, agent: StubAgent, **overrides) -> tuple[TestClient, StubAgent]:
    settings = ApiSettings(jobs_db=str(tmp_path / "jobs.sqlite"), **overrides)
    app = create_app(settings)
    app.dependency_overrides[agent_of] = lambda: agent
    return TestClient(app), agent


def wait_for(client: TestClient, job_id: str, *, headers=None, timeout: float = 5.0) -> dict:
    """Poll the way a caller does, until the job leaves queued/running."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get(f"/v1/reviews/{job_id}", headers=headers or {}).json()
        if body["status"] not in ("queued", "running"):
            return body
        time.sleep(0.02)
    raise AssertionError(f"job {job_id} never finished: {body}")


@pytest.fixture
def stub() -> StubAgent:
    return StubAgent()


def test_healthz_needs_no_key_and_no_worker(tmp_path, stub) -> None:
    client, _ = build(tmp_path, stub, api_keys=("secret",))
    with client:
        body = client.get("/healthz").json()
    assert body == {"status": "ok", "service": "api", "detail": {}}


def test_readyz_reports_the_worker(tmp_path, stub) -> None:
    client, _ = build(tmp_path, stub)
    with client:
        body = client.get("/readyz").json()
    assert body["status"] == "ok"
    assert body["detail"]["agent"]["status"] == "ok"


def test_readyz_is_degraded_when_the_worker_is_unreachable(tmp_path) -> None:
    class Down(StubAgent):
        async def readyz(self) -> dict:
            raise AgentError("connection refused")

    client, _ = build(tmp_path, Down())
    with client:
        body = client.get("/readyz").json()
    assert body["status"] == "degraded"
    assert body["detail"]["agent"]["status"] == "unreachable"


def test_submit_returns_202_and_the_run_finishes_in_the_background(tmp_path, stub) -> None:
    client, agent = build(tmp_path, stub)
    with client:
        accepted = client.post("/v1/reviews", json={"url": URL})
        assert accepted.status_code == 202
        body = accepted.json()
        assert body["status"] == "queued"
        assert body["poll"] == f"/v1/reviews/{body['job_id']}"

        done = wait_for(client, body["job_id"])

    assert done["status"] == "succeeded"
    assert done["thread_id"] == "review-260927-101500"
    assert done["result"]["status"] == "검토 완료"
    assert done["result"]["cost"]["usd"] == 0.031
    assert agent.calls == [{"kind": "review", "url": URL}]


def test_a_worker_refusal_lands_on_the_job_not_the_submission(tmp_path) -> None:
    client, _ = build(tmp_path, StubAgent(error=AgentError("worker returned 500: BudgetExceeded")))
    with client:
        job_id = client.post("/v1/reviews", json={"url": URL}).json()["job_id"]
        done = wait_for(client, job_id)
    assert done["status"] == "failed"
    assert "BudgetExceeded" in done["error"]
    assert done["result"] is None


def test_an_unexpected_crash_still_closes_the_job(tmp_path) -> None:
    client, _ = build(tmp_path, StubAgent(error=RuntimeError("boom")))
    with client:
        job_id = client.post("/v1/reviews", json={"url": URL}).json()["job_id"]
        done = wait_for(client, job_id)
    assert done["status"] == "failed"
    assert done["error"] == "RuntimeError: boom"


def test_report_markdown_is_409_until_the_job_succeeds(tmp_path, stub) -> None:
    client, _ = build(tmp_path, stub)
    with client:
        job_id = client.post("/v1/reviews", json={"url": URL}).json()["job_id"]
        wait_for(client, job_id)
        ok = client.get(f"/v1/reviews/{job_id}/report.md")
        assert ok.status_code == 200
        assert ok.text.startswith("# 검토 보고서")
        assert "text/markdown" in ok.headers["content-type"]

        client.post("/v1/reviews", json={"url": URL})
        missing = client.get("/v1/reviews/nope/report.md")
    assert missing.status_code == 404


def test_rerun_takes_a_thread_and_a_node(tmp_path, stub) -> None:
    client, agent = build(tmp_path, stub)
    with client:
        accepted = client.post(
            "/v1/reruns",
            json={"thread_id": "review-260927-101500", "from_node": "judge_display_method"},
        )
        assert accepted.status_code == 202
        done = wait_for(client, accepted.json()["job_id"])
    assert done["status"] == "succeeded"
    assert done["kind"] == "rerun"
    assert agent.calls == [{"kind": "rerun", "thread_id": "review-260927-101500"}]


def test_a_bad_url_is_rejected_before_a_job_exists(tmp_path, stub) -> None:
    client, agent = build(tmp_path, stub)
    with client:
        assert client.post("/v1/reviews", json={"url": "not-a-url"}).status_code == 422
        assert client.get("/v1/reviews").json()["count"] == 0
    assert agent.calls == []


def test_max_usd_over_the_cap_is_rejected(tmp_path, stub) -> None:
    client, _ = build(tmp_path, stub)
    with client:
        response = client.post("/v1/reviews", json={"url": URL, "max_usd": 500})
    assert response.status_code == 422


def test_a_key_is_required_once_one_is_configured(tmp_path, stub) -> None:
    client, agent = build(tmp_path, stub, api_keys=("s3cret", "other"))
    with client:
        assert client.post("/v1/reviews", json={"url": URL}).status_code == 401
        assert client.get("/v1/reviews").status_code == 401
        assert (
            client.post("/v1/reviews", json={"url": URL}, headers={"X-API-Key": "wrong"})
        ).status_code == 401

        accepted = client.post("/v1/reviews", json={"url": URL}, headers={"X-API-Key": "other"})
        assert accepted.status_code == 202
        done = wait_for(client, accepted.json()["job_id"], headers={"X-API-Key": "s3cret"})
    assert done["status"] == "succeeded"
    assert len(agent.calls) == 1


def test_a_job_cut_off_by_shutdown_is_interrupted_not_running(tmp_path) -> None:
    """A row left `running` would make a caller poll for ever, so shutdown closes it out."""

    class Hangs(StubAgent):
        async def run(self, request) -> RunResult:
            await asyncio.sleep(30)
            raise AssertionError("unreachable")

    jobs_db = str(tmp_path / "jobs.sqlite")
    app = create_app(ApiSettings(jobs_db=jobs_db))
    app.dependency_overrides[agent_of] = lambda: Hangs()
    with TestClient(app) as client:
        job_id = client.post("/v1/reviews", json={"url": URL}).json()["job_id"]
        for _ in range(100):  # let the background task reach `running`
            if client.get(f"/v1/reviews/{job_id}").json()["status"] == "running":
                break
            time.sleep(0.02)
        assert client.get(f"/v1/reviews/{job_id}").json()["status"] == "running"

    store = JobStore(jobs_db)
    row = store.get(job_id)
    store.close()
    assert row is not None
    assert row.status is JobStatus.interrupted
    assert "shut down" in (row.error or "")


def test_a_restart_finds_no_row_left_mid_flight(tmp_path, stub) -> None:
    jobs_db = str(tmp_path / "jobs.sqlite")
    first = create_app(ApiSettings(jobs_db=jobs_db))
    first.dependency_overrides[agent_of] = lambda: StubAgent(error=AgentError("worker down"))
    with TestClient(first) as client:
        failed = client.post("/v1/reviews", json={"url": URL}).json()["job_id"]
        wait_for(client, failed)

    # A row that never ran, as a crash before startup reconciliation would leave it.
    store = JobStore(jobs_db)
    orphan = store.create(url=URL)
    store.close()

    second = create_app(ApiSettings(jobs_db=jobs_db))
    second.dependency_overrides[agent_of] = lambda: stub
    with TestClient(second) as client:
        listed = client.get("/v1/reviews").json()
    statuses = {job["job_id"]: job["status"] for job in listed["jobs"]}
    assert statuses[orphan.job_id] == "interrupted"
    assert statuses[failed] == "failed"
