"""The gateway's side of the worker call; only connect is short, read waits for the whole run."""

from typing import Any

import httpx

from ..schemas import RerunRequest, ReviewRequest, RunResult


class AgentError(RuntimeError):
    """The worker refused or crashed. The message is what goes onto the job row."""


class AgentClient:
    def __init__(self, base_url: str, run_timeout_seconds: float) -> None:
        self.base_url = base_url.rstrip("/")
        self._timeout = httpx.Timeout(connect=10.0, read=run_timeout_seconds, write=30.0, pool=30.0)

    async def healthz(self) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
            response = await client.get("/healthz")
            response.raise_for_status()
            return response.json()

    async def readyz(self) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
            response = await client.get("/readyz")
            return response.json()

    async def run(self, request: ReviewRequest) -> RunResult:
        return await self._post("/run", request.model_dump(mode="json"))

    async def rerun(self, request: RerunRequest) -> RunResult:
        return await self._post("/rerun", request.model_dump(mode="json"))

    async def _post(self, path: str, payload: dict[str, Any]) -> RunResult:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self._timeout) as client:
            try:
                response = await client.post(path, json=payload)
            except httpx.TimeoutException as error:
                raise AgentError(f"the worker did not finish in time: {error}") from error
            except httpx.HTTPError as error:
                raise AgentError(f"the worker is unreachable: {error}") from error
        if response.status_code >= 400:
            raise AgentError(_detail(response))
        return RunResult.model_validate(response.json())


def _detail(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return f"worker returned {response.status_code}: {response.text[:500]}"
    detail = body.get("detail") if isinstance(body, dict) else None
    return f"worker returned {response.status_code}: {detail or str(body)[:500]}"
