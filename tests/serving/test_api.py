"""The gateway, driven with a stub worker: no graph, no model call, no browser.

What is under test is the job protocol — 202 then poll — and the auth gate, not the review itself.
"""

import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from financial_disclosure_review.core import urls
from financial_disclosure_review.serving.api.app import MissingTokenError, agent_of, create_app
from financial_disclosure_review.serving.api.client import AgentError
from financial_disclosure_review.serving.api.jobs import JobStore
from financial_disclosure_review.serving.schemas import JobStatus, RunResult
from financial_disclosure_review.serving.settings import ApiSettings

URL = "https://example.test/card/apply"


@pytest.fixture(autouse=True)
def public_dns(monkeypatch):
    """`example.test` does not resolve; stand in a public address so only the URL rules decide."""
    monkeypatch.setattr(urls, "resolve", lambda host: ["211.45.27.10"])


TOKEN = "fdr_test_token_value"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


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
    overrides.setdefault("api_tokens", (TOKEN,))
    settings = ApiSettings(jobs_db=str(tmp_path / "jobs.sqlite"), **overrides)
    app = create_app(settings)
    app.dependency_overrides[agent_of] = lambda: agent
    return TestClient(app), agent


def wait_for(client: TestClient, job_id: str, *, headers=None, timeout: float = 5.0) -> dict:
    """Poll the way a caller does, until the job leaves queued/running."""
    deadline = time.time() + timeout
    body: dict = {}
    while time.time() < deadline:
        body = client.get(f"/v1/reviews/{job_id}", headers=headers or AUTH).json()
        if body["status"] not in ("queued", "running"):
            return body
        time.sleep(0.02)
    raise AssertionError(f"job {job_id} never finished: {body}")


@pytest.fixture
def stub() -> StubAgent:
    return StubAgent()


def test_healthz_needs_no_token_and_no_worker(tmp_path, stub) -> None:
    client, _ = build(tmp_path, stub)
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
        accepted = client.post("/v1/reviews", json={"url": URL}, headers=AUTH)
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
        job_id = client.post("/v1/reviews", json={"url": URL}, headers=AUTH).json()["job_id"]
        done = wait_for(client, job_id)
    assert done["status"] == "failed"
    assert "BudgetExceeded" in done["error"]
    assert done["result"] is None


def test_an_unexpected_crash_still_closes_the_job(tmp_path) -> None:
    client, _ = build(tmp_path, StubAgent(error=RuntimeError("boom")))
    with client:
        job_id = client.post("/v1/reviews", json={"url": URL}, headers=AUTH).json()["job_id"]
        done = wait_for(client, job_id)
    assert done["status"] == "failed"
    assert done["error"] == "RuntimeError: boom"


def test_report_markdown_is_409_until_the_job_succeeds(tmp_path, stub) -> None:
    client, _ = build(tmp_path, stub)
    with client:
        job_id = client.post("/v1/reviews", json={"url": URL}, headers=AUTH).json()["job_id"]
        wait_for(client, job_id)
        ok = client.get(f"/v1/reviews/{job_id}/report.md", headers=AUTH)
        assert ok.status_code == 200
        assert ok.text.startswith("# 검토 보고서")
        assert "text/markdown" in ok.headers["content-type"]

        client.post("/v1/reviews", json={"url": URL}, headers=AUTH)
        missing = client.get("/v1/reviews/nope/report.md", headers=AUTH)
    assert missing.status_code == 404


def test_rerun_takes_a_thread_and_a_node(tmp_path, stub) -> None:
    client, agent = build(tmp_path, stub)
    with client:
        accepted = client.post(
            "/v1/reruns",
            json={"thread_id": "review-260927-101500", "from_node": "judge_display_method"},
            headers=AUTH,
        )
        assert accepted.status_code == 202
        done = wait_for(client, accepted.json()["job_id"])
    assert done["status"] == "succeeded"
    assert done["kind"] == "rerun"
    assert agent.calls == [{"kind": "rerun", "thread_id": "review-260927-101500"}]


def test_a_bad_url_is_rejected_before_a_job_exists(tmp_path, stub) -> None:
    client, agent = build(tmp_path, stub)
    with client:
        bad = client.post("/v1/reviews", json={"url": "not-a-url"}, headers=AUTH)
        assert bad.status_code == 422
        assert client.get("/v1/reviews", headers=AUTH).json()["count"] == 0
    assert agent.calls == []


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8100/run",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.8/admin",
        "http://[::1]/",
    ],
)
def test_an_address_only_the_server_can_reach_is_refused_before_a_job_exists(
    tmp_path, stub, url
) -> None:
    client, agent = build(tmp_path, stub)
    with client:
        refused = client.post("/v1/reviews", json={"url": url}, headers=AUTH)
        assert refused.status_code == 422
        assert "non-public address" in refused.json()["detail"]
        assert client.get("/v1/reviews", headers=AUTH).json()["count"] == 0
    assert agent.calls == []


def test_the_allowed_list_limits_which_domains_are_reviewed(tmp_path, stub) -> None:
    client, agent = build(tmp_path, stub, allowed_hosts=("lottecard.co.kr",))
    with client:
        refused = client.post("/v1/reviews", json={"url": URL}, headers=AUTH)
        assert refused.status_code == 422
        assert "not in the allowed list" in refused.json()["detail"]
        accepted = client.post(
            "/v1/reviews", json={"url": "https://www.lottecard.co.kr/app/x.lc"}, headers=AUTH
        )
        assert accepted.status_code == 202
        wait_for(client, accepted.json()["job_id"])
    assert len(agent.calls) == 1


def test_max_usd_over_the_cap_is_rejected(tmp_path, stub) -> None:
    client, _ = build(tmp_path, stub)
    with client:
        response = client.post("/v1/reviews", json={"url": URL, "max_usd": 500}, headers=AUTH)
    assert response.status_code == 422


def test_null_persona_fields_are_accepted_and_reach_the_worker(tmp_path) -> None:
    """A form sends every persona field, null when the user left it blank."""

    class Recording(StubAgent):
        async def run(self, request) -> RunResult:
            self.requests.append(request)
            return await super().run(request)

    agent = Recording()
    agent.requests = []
    client, _ = build(tmp_path, agent)
    persona = {
        "request": None,
        "uuid": None,
        "attributes": {
            "age_min": 70,
            "age_max": None,
            "sex": None,
            "education_level": None,
            "occupation_contains": None,
            "province": ["서울"],
            "family_type": None,
            "housing_type": None,
            "marital_status": None,
        },
    }
    with client:
        for body in ({"url": URL, "persona": None}, {"url": URL, "persona": persona}):
            accepted = client.post("/v1/reviews", json=body, headers=AUTH)
            assert accepted.status_code == 202, accepted.json()
            assert wait_for(client, accepted.json()["job_id"])["status"] == "succeeded"

    assert agent.requests[0].persona is None
    sent = agent.requests[1].persona
    assert sent.request is None and sent.uuid is None
    assert sent.attributes.age_min == 70 and sent.attributes.province == ["서울"]


@pytest.mark.parametrize(
    "persona",
    [
        {"attributes": {"income": 3000}},
        {"attributes": {"age_min": "칠십"}},
        {"attributes": {"age_min": 200}},
        {"attributes": {"province": "서울"}},
        {"uuid": "not-a-uuid"},
    ],
)
def test_a_malformed_persona_is_rejected_before_a_job_exists(tmp_path, stub, persona) -> None:
    client, agent = build(tmp_path, stub)
    with client:
        response = client.post("/v1/reviews", json={"url": URL, "persona": persona}, headers=AUTH)
        assert response.status_code == 422
        assert client.get("/v1/reviews", headers=AUTH).json()["count"] == 0
    assert agent.calls == []


def test_every_v1_route_rejects_a_caller_without_a_token(tmp_path, stub) -> None:
    client, agent = build(tmp_path, stub)
    with client:
        assert client.post("/v1/reviews", json={"url": URL}).status_code == 401
        assert client.get("/v1/reviews").status_code == 401
        assert client.get("/v1/reviews/anything").status_code == 401
        assert client.get("/v1/reviews/anything/report.md").status_code == 401
        assert (
            client.post(
                "/v1/reruns", json={"thread_id": "t", "from_node": "classify_type"}
            ).status_code
            == 401
        )
    assert agent.calls == []


def test_a_wrong_or_malformed_token_is_rejected(tmp_path, stub) -> None:
    client, agent = build(tmp_path, stub)
    with client:
        for headers in (
            {"Authorization": "Bearer wrong-token"},
            {"Authorization": TOKEN},  # no scheme
            {"Authorization": f"Basic {TOKEN}"},  # wrong scheme
            {"Authorization": "Bearer "},
            {"X-API-Key": TOKEN},  # the scheme this replaced
        ):
            response = client.post("/v1/reviews", json={"url": URL}, headers=headers)
            assert response.status_code == 401, headers
            assert response.headers["WWW-Authenticate"] == "Bearer"
    assert agent.calls == []


def test_the_issued_token_is_accepted(tmp_path, stub) -> None:
    client, agent = build(tmp_path, stub)
    with client:
        accepted = client.post("/v1/reviews", json={"url": URL}, headers=AUTH)
        assert accepted.status_code == 202
        done = wait_for(client, accepted.json()["job_id"])
    assert done["status"] == "succeeded"
    assert len(agent.calls) == 1


def test_a_second_token_stays_valid_during_a_rotation(tmp_path, stub) -> None:
    """Two live tokens let a caller move to the new one before the old one is withdrawn."""
    client, _ = build(tmp_path, stub, api_tokens=(TOKEN, "fdr_the_new_one"))
    with client:
        for token in (TOKEN, "fdr_the_new_one"):
            response = client.post(
                "/v1/reviews", json={"url": URL}, headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 202
        assert (
            client.post(
                "/v1/reviews", json={"url": URL}, headers={"Authorization": "Bearer fdr_retired"}
            ).status_code
            == 401
        )


def test_the_gateway_refuses_to_start_without_a_token(tmp_path, stub) -> None:
    """Fail closed: no opt-out, so a forgotten variable cannot publish an open API."""
    app = create_app(ApiSettings(jobs_db=str(tmp_path / "jobs.sqlite"), api_tokens=()))
    app.dependency_overrides[agent_of] = lambda: stub
    with pytest.raises(MissingTokenError, match="FDR_API_TOKEN"):
        with TestClient(app):
            pass


def test_health_routes_answer_without_a_token(tmp_path, stub) -> None:
    client, _ = build(tmp_path, stub)
    with client:
        assert client.get("/healthz").status_code == 200
        assert client.get("/readyz").status_code == 200


def test_cors_preflight_allows_the_frontend_bearer_request(tmp_path, stub, monkeypatch) -> None:
    origin = "https://finalproject-phi-sooty.vercel.app"
    monkeypatch.setenv("FDR_CORS_ORIGINS", origin)
    client, _ = build(tmp_path, stub)
    with client:
        response = client.options(
            "/v1/reviews",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "authorization" in response.headers["access-control-allow-headers"].lower()


def test_a_job_cut_off_by_shutdown_is_interrupted_not_running(tmp_path) -> None:
    """A row left `running` would make a caller poll for ever, so shutdown closes it out."""

    class Hangs(StubAgent):
        async def run(self, request) -> RunResult:
            await asyncio.sleep(30)
            raise AssertionError("unreachable")

    jobs_db = str(tmp_path / "jobs.sqlite")
    app = create_app(ApiSettings(jobs_db=jobs_db, api_tokens=(TOKEN,)))
    app.dependency_overrides[agent_of] = lambda: Hangs()
    with TestClient(app) as client:
        job_id = client.post("/v1/reviews", json={"url": URL}, headers=AUTH).json()["job_id"]
        for _ in range(100):  # let the background task reach `running`
            if client.get(f"/v1/reviews/{job_id}", headers=AUTH).json()["status"] == "running":
                break
            time.sleep(0.02)
        assert client.get(f"/v1/reviews/{job_id}", headers=AUTH).json()["status"] == "running"

    store = JobStore(jobs_db)
    row = store.get(job_id)
    store.close()
    assert row is not None
    assert row.status is JobStatus.interrupted
    assert "shut down" in (row.error or "")


def test_a_restart_finds_no_row_left_mid_flight(tmp_path, stub) -> None:
    jobs_db = str(tmp_path / "jobs.sqlite")
    first = create_app(ApiSettings(jobs_db=jobs_db, api_tokens=(TOKEN,)))
    first.dependency_overrides[agent_of] = lambda: StubAgent(error=AgentError("worker down"))
    with TestClient(first) as client:
        failed = client.post("/v1/reviews", json={"url": URL}, headers=AUTH).json()["job_id"]
        wait_for(client, failed)

    # A row that never ran, as a crash before startup reconciliation would leave it.
    store = JobStore(jobs_db)
    orphan = store.create(url=URL)
    store.close()

    second = create_app(ApiSettings(jobs_db=jobs_db, api_tokens=(TOKEN,)))
    second.dependency_overrides[agent_of] = lambda: stub
    with TestClient(second) as client:
        listed = client.get("/v1/reviews", headers=AUTH).json()
    statuses = {job["job_id"]: job["status"] for job in listed["jobs"]}
    assert statuses[orphan.job_id] == "interrupted"
    assert statuses[failed] == "failed"
