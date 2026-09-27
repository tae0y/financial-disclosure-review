"""The public gateway. This is what the Cloudflare tunnel points at.

A review takes minutes, and Cloudflare closes a response that produces nothing for ~100 seconds,
so nothing here waits for the graph. A submission returns 202 with a job id, a background task
drives the worker, and the caller polls. The one blocking dependency is SQLite, and that goes to a
thread.

`create_app(settings)` takes its settings as an argument rather than reading the environment at
import time, so a test drives a temporary job store and a stub worker without touching the process
environment. `app` at the bottom is the uvicorn entry point.
"""

import asyncio
import hmac
import logging
import os
from contextlib import asynccontextmanager
from typing import Annotated, Any

from dotenv import find_dotenv, load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.security import APIKeyHeader
from starlette.concurrency import run_in_threadpool

from ..schemas import (
    Health,
    Job,
    JobAccepted,
    JobList,
    JobStatus,
    RerunRequest,
    ReviewRequest,
)
from ..settings import ApiSettings
from .client import AgentClient, AgentError
from .jobs import JobStore

log = logging.getLogger("fdr.api")

DESCRIPTION = """\
Reviews a Korean financial-product web page against the explanation duty (설명의무) and the
display-method rules (표시방법), and rewrites its explanation in plain Korean.

**A review takes minutes, so nothing here returns one.** The page is rendered in a real browser and
judged over a series of model calls. Cloudflare closes a response that has produced nothing for
about 100 seconds, so a synchronous endpoint would fail on exactly the runs that worked.

Submitting therefore returns `202 Accepted` with a job id; poll `GET /v1/reviews/{job_id}` until
`status` leaves `queued`/`running`. Job rows are stored on disk, so a restart does not lose the
record of what was asked.

`status` reaches one of:

- `succeeded` — `result` is filled.
- `failed` — the worker raised; `error` holds the type and message.
- `interrupted` — the gateway restarted mid-run. The partial run's checkpoints survive, so
  `POST /v1/reruns` resumes it instead of starting over.
"""

TAGS = [
    {
        "name": "reviews",
        "description": (
            "Submitting a review and reading it back. Every route here requires `X-API-Key` "
            "once `FDR_API_KEYS` is set."
        ),
    },
    {
        "name": "health",
        "description": (
            "Always unauthenticated, so a container probe needs no credential. `/healthz` is "
            "liveness of this process alone; `/readyz` also reports the worker, the reference "
            "DB and the model key."
        ),
    },
]

SERVERS = [
    {"url": "http://localhost:8000", "description": "Local, via the compose override file."},
    {
        "url": "https://{hostname}",
        "description": "Through the Cloudflare tunnel.",
        "variables": {
            "hostname": {
                "default": "disclosure-review.example.com",
                "description": "The public hostname routed to api:8000 by the tunnel.",
            }
        },
    },
]

# Typed the way FastAPI declares `responses`, so these can be spread into a route decorator.
Responses = dict[int | str, dict[str, Any]]

AUTH_RESPONSES: Responses = {
    401: {"description": "`FDR_API_KEYS` is set and the `X-API-Key` header is missing or wrong."}
}
NOT_FOUND_RESPONSE: Responses = {404: {"description": "No job with that id."}}
ACCEPTED_RESPONSES: Responses = {
    202: {"description": "Queued. Poll the `poll` path until the job reaches a terminal status."},
    **AUTH_RESPONSES,
}


def _cors_origins() -> list[str]:
    raw = os.environ.get("FDR_CORS_ORIGINS", "")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def settings_of(request: Request) -> ApiSettings:
    return request.app.state.settings


def store_of(request: Request) -> JobStore:
    return request.app.state.store


def agent_of(request: Request) -> AgentClient:
    return request.app.state.agent


# Declared as a security scheme rather than read off the raw headers, so the generated OpenAPI
# document carries the requirement and a generated client knows how to authenticate.
# `auto_error=False` keeps the 401 here, where the "no keys configured" case is decided.
api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description=(
        "Required on every /v1 route when FDR_API_KEYS is set. With that variable empty the "
        "check is skipped and any caller is accepted, which is only appropriate locally."
    ),
)


async def require_key(
    request: Request, offered: Annotated[str | None, Security(api_key_header)] = None
) -> None:
    """`X-API-Key` against `FDR_API_KEYS`. With no keys configured the check is skipped."""
    keys = settings_of(request).api_keys
    if not keys:
        return
    if not any(hmac.compare_digest(offered or "", key) for key in keys):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="a valid X-API-Key header is required",
            headers={"WWW-Authenticate": "X-API-Key"},
        )


Authorized = Annotated[None, Security(require_key)]
Store = Annotated[JobStore, Depends(store_of)]
Agent = Annotated[AgentClient, Depends(agent_of)]


async def _drive(app: FastAPI, job_id: str, call) -> None:
    """Run one job to a terminal state. Every exit path writes a row; none leaves it `running`."""
    store: JobStore = app.state.store
    async with app.state.slots:
        await run_in_threadpool(store.mark_running, job_id)
        try:
            result = await call()
        except AgentError as error:
            log.warning("job %s failed: %s", job_id, error)
            await run_in_threadpool(store.mark_failed, job_id, str(error))
        except asyncio.CancelledError:
            # Shutdown closes the row out. A cancelled coroutine cannot reach another await
            # point, so writing the row from here would never complete.
            raise
        except Exception as error:  # noqa: BLE001 - a row must never be left mid-flight
            log.exception("job %s crashed", job_id)
            await run_in_threadpool(store.mark_failed, job_id, f"{type(error).__name__}: {error}")
        else:
            log.info(
                "job %s done: thread=%s status=%s %ss",
                job_id,
                result.thread_id,
                result.status,
                result.elapsed_seconds,
            )
            await run_in_threadpool(store.mark_succeeded, job_id, result)


def _spawn(app: FastAPI, job_id: str, call) -> None:
    """Hold a reference to the task so it is not collected mid-run."""
    task = asyncio.create_task(_drive(app, job_id, call))
    app.state.running.add(task)
    task.add_done_callback(app.state.running.discard)


def create_app(settings: ApiSettings | None = None) -> FastAPI:
    settings = settings or ApiSettings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logging.basicConfig(level=os.environ.get("FDR_LOG_LEVEL", "INFO"))
        app.state.settings = settings
        app.state.store = JobStore(settings.jobs_db)
        app.state.agent = AgentClient(settings.agent_url, settings.run_timeout_seconds)
        app.state.slots = asyncio.Semaphore(max(1, settings.concurrency))
        app.state.running = set()

        stale = await run_in_threadpool(
            app.state.store.close_out_in_flight,
            "the gateway restarted while this job was in flight; submit it again",
        )
        purged = await run_in_threadpool(
            app.state.store.purge_older_than, settings.job_retention_days
        )
        if not settings.api_keys:
            log.warning(
                "FDR_API_KEYS is empty: every caller is accepted. Set it before putting this "
                "behind a public hostname."
            )
        log.info(
            "gateway up: agent=%s jobs=%s concurrency=%s interrupted=%s purged=%s auth=%s",
            settings.agent_url,
            settings.jobs_db,
            settings.concurrency,
            stale,
            purged,
            "on" if settings.api_keys else "off",
        )
        try:
            yield
        finally:
            tasks = list(app.state.running)
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            app.state.store.close_out_in_flight("the gateway shut down while this job was running")
            app.state.store.close()

    app = FastAPI(
        title="Financial Disclosure Review API",
        description=DESCRIPTION,
        version="0.1.0",
        lifespan=lifespan,
        openapi_tags=TAGS,
        servers=SERVERS,
    )
    if origins := _cors_origins():
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["GET", "POST"],
            allow_headers=["X-API-Key", "Content-Type"],
        )

    @app.get("/healthz", response_model=Health, tags=["health"], operation_id="getHealth")
    async def healthz() -> Health:
        """Liveness of the gateway alone, so the container probe never fails on the worker."""
        return Health(status="ok", service="api")

    @app.get("/readyz", response_model=Health, tags=["health"], operation_id="getReadiness")
    async def readyz(agent: Agent) -> Health:
        """Readiness including the worker, for a caller deciding whether to submit."""
        detail: dict[str, Any] = {"jobs_db": settings.jobs_db, "auth": bool(settings.api_keys)}
        try:
            detail["agent"] = await agent.readyz()
            ok = detail["agent"].get("status") == "ok"
        except Exception as error:  # noqa: BLE001
            detail["agent"] = {"status": "unreachable", "error": str(error)}
            ok = False
        return Health(status="ok" if ok else "degraded", service="api", detail=detail)

    @app.post(
        "/v1/reviews",
        response_model=JobAccepted,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["reviews"],
        operation_id="submitReview",
        responses=ACCEPTED_RESPONSES,
    )
    async def submit_review(
        request: ReviewRequest, http: Request, store: Store, agent: Agent, _: Authorized
    ) -> JobAccepted:
        """Queue a review of one product page URL."""
        job = await run_in_threadpool(
            store.create, url=str(request.url), thread_id=request.thread_id, model=request.model
        )
        _spawn(http.app, job.job_id, lambda: agent.run(request))
        return JobAccepted(job_id=job.job_id, status=job.status, poll=f"/v1/reviews/{job.job_id}")

    @app.post(
        "/v1/reruns",
        response_model=JobAccepted,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["reviews"],
        operation_id="submitRerun",
        responses=ACCEPTED_RESPONSES,
    )
    async def submit_rerun(
        request: RerunRequest, http: Request, store: Store, agent: Agent, _: Authorized
    ) -> JobAccepted:
        """Queue a re-run of a recorded thread from one node onward."""
        job = await run_in_threadpool(
            store.create, kind="rerun", thread_id=request.thread_id, model=request.model
        )
        _spawn(http.app, job.job_id, lambda: agent.rerun(request))
        return JobAccepted(job_id=job.job_id, status=job.status, poll=f"/v1/reviews/{job.job_id}")

    @app.get(
        "/v1/reviews",
        response_model=JobList,
        tags=["reviews"],
        operation_id="listReviews",
        responses=AUTH_RESPONSES,
    )
    async def list_reviews(
        store: Store,
        _: Authorized,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        job_status: Annotated[JobStatus | None, Query(alias="status")] = None,
    ) -> JobList:
        """Recent jobs, newest first."""
        jobs = await run_in_threadpool(store.list, limit=limit, status=job_status)
        return JobList(jobs=jobs, count=len(jobs))

    @app.get(
        "/v1/reviews/{job_id}",
        response_model=Job,
        tags=["reviews"],
        operation_id="getReview",
        responses={**AUTH_RESPONSES, **NOT_FOUND_RESPONSE},
    )
    async def get_review(job_id: str, store: Store, _: Authorized) -> Job:
        """One job. `result` is filled once `status` is `succeeded`."""
        job = await run_in_threadpool(store.get, job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"no job {job_id!r}")
        return job

    @app.get(
        "/v1/reviews/{job_id}/report.md",
        response_class=PlainTextResponse,
        tags=["reviews"],
        operation_id="getReviewReportMarkdown",
        responses={
            200: {
                "description": "The report as Markdown.",
                "content": {"text/markdown": {"schema": {"type": "string"}}},
            },
            409: {"description": "The job has not succeeded, so there is no report yet."},
            **AUTH_RESPONSES,
            **NOT_FOUND_RESPONSE,
        },
    )
    async def get_report_markdown(job_id: str, store: Store, _: Authorized) -> PlainTextResponse:
        """The reviewer-facing report as Markdown, once the job has succeeded."""
        job = await run_in_threadpool(store.get, job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"no job {job_id!r}")
        if job.status is not JobStatus.succeeded or job.result is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"job {job_id} is {job.status.value}; no report yet",
            )
        return PlainTextResponse(
            content=job.result.report.get("markdown") or "",
            media_type="text/markdown; charset=utf-8",
        )

    return app


# In the container the environment comes from compose; locally it comes from .env.
load_dotenv(find_dotenv(usecwd=True))
app = create_app()
