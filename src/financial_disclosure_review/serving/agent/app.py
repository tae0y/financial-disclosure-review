"""The internal worker API. Reachable only from the compose network, never from the tunnel.

One endpoint does real work, and it blocks for as long as the review takes — minutes, not
seconds. The gateway is what turns that into a pollable job; this process stays a plain
request/response worker so it can be curled directly while debugging.
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import anyio
from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI, HTTPException, Request, status

from ..schemas import Health, RerunRequest, ReviewRequest, RunResult
from ..settings import AgentSettings
from .runner import run_rerun, run_review

log = logging.getLogger("fdr.agent")


def create_app(settings: AgentSettings | None = None) -> FastAPI:
    settings = settings or AgentSettings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logging.basicConfig(level=os.environ.get("FDR_LOG_LEVEL", "INFO"))
        app.state.settings = settings
        # `core.usage` keeps the run meter in a module-level global, so two runs in one process
        # would share one budget. Serialized unless FDR_AGENT_CONCURRENCY says otherwise.
        app.state.slots = anyio.Semaphore(max(1, settings.concurrency))
        log.info(
            "agent up: model=%s data_dir=%s db=%s checkpoints=%s concurrency=%s",
            settings.model,
            settings.data_dir,
            settings.resolved_db_path(),
            settings.resolved_checkpoints(),
            settings.concurrency,
        )
        if not Path(settings.resolved_db_path()).exists():
            log.warning(
                "reference DB %s is missing; rubric-backed judgments will come back 판정 불가",
                settings.resolved_db_path(),
            )
        yield

    app = FastAPI(
        title="Financial Disclosure Review — agent worker",
        description="Internal LangGraph worker. Not exposed through the Cloudflare tunnel.",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/healthz", response_model=Health, tags=["health"])
    async def healthz() -> Health:
        """Liveness only: the process answers. It says nothing about the reference DB."""
        return Health(status="ok", service="agent", detail={"model": settings.model})

    @app.get("/readyz", response_model=Health, tags=["health"])
    async def readyz() -> Health:
        """Readiness: the reference DB exists, `data/` is writable, and the model key is set."""
        data = Path(settings.data_dir)
        checks = {
            "reference_db": Path(settings.resolved_db_path()).exists(),
            "data_dir_writable": data.exists() and os.access(data, os.W_OK),
            "openai_api_key": bool(os.environ.get("OPENAI_API_KEY")),
        }
        ok = all(checks.values())
        return Health(status="ok" if ok else "degraded", service="agent", detail=checks)

    @app.post("/run", response_model=RunResult, tags=["run"])
    async def run(request: ReviewRequest, http: Request) -> RunResult:
        """Review one page. Blocks until the graph reaches END."""
        async with http.app.state.slots:
            log.info("run start url=%s model=%s", request.url, request.model or settings.model)
            try:
                return await anyio.to_thread.run_sync(
                    lambda: run_review(
                        str(request.url),
                        settings,
                        model=request.model,
                        thread_id=request.thread_id,
                        detail=request.detail,
                        max_calls=request.max_calls,
                        max_usd=request.max_usd,
                    )
                )
            except Exception as error:  # surfaced to the gateway, which records it on the job
                log.exception("run failed url=%s", request.url)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"{type(error).__name__}: {error}",
                ) from error

    @app.post("/rerun", response_model=RunResult, tags=["run"])
    async def rerun(request: RerunRequest, http: Request) -> RunResult:
        """Resume a recorded thread from one node onward."""
        async with http.app.state.slots:
            log.info("rerun start thread=%s from=%s", request.thread_id, request.from_node)
            try:
                return await anyio.to_thread.run_sync(
                    lambda: run_rerun(
                        request.thread_id,
                        request.from_node,
                        settings,
                        model=request.model,
                        detail=request.detail,
                        max_calls=request.max_calls,
                        max_usd=request.max_usd,
                    )
                )
            except LookupError as error:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
                ) from error
            except Exception as error:
                log.exception("rerun failed thread=%s", request.thread_id)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"{type(error).__name__}: {error}",
                ) from error

    return app


# In the container the environment comes from compose; locally it comes from .env.
load_dotenv(find_dotenv(usecwd=True))
app = create_app()
