# Run the Review Service in Docker

This page describes how to run the review API and its worker locally or in production with Docker Compose.

| Service | Image | Port | Reachable from |
|---|---|---|---|
| `api` | `docker/Dockerfile.api` | 8000 | The tunnel, and the host in local mode |
| `agent` | `docker/Dockerfile.agent` | 8100 | The compose network only |
| `cloudflared` | `cloudflare/cloudflared` | — | Outbound only |

The worker carries Chromium (a few GB); the gateway does not. Editing a route rebuilds only the small image, and the process that answers the internet is not the one driving a browser.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine with the Compose plugin)
- [uv](https://docs.astral.sh/uv/), to issue an API token
- An OpenAI API key

## Prepare the environment

1. Get the repository root.

    ```bash
    # bash/zsh
    REPOSITORY_ROOT=$(git rev-parse --show-toplevel)
    cd $REPOSITORY_ROOT
    ```

    ```powershell
    # PowerShell
    $REPOSITORY_ROOT = git rev-parse --show-toplevel
    Set-Location $REPOSITORY_ROOT
    ```

1. Create a `.env` file.

    ```bash
    # bash/zsh
    cp .env.example .env
    ```

    ```powershell
    # PowerShell
    Copy-Item .env.example .env
    ```

1. Issue an API token.

    ```bash
    uv run python -m financial_disclosure_review.serving.token
    ```

1. Set `OPENAI_API_KEY` and `FDR_API_TOKEN` in `.env`. The other values have working defaults documented in `.env.example`.
   The gateway exits with code 3 when `FDR_API_TOKEN` is unset, so an unauthenticated instance cannot start.

The rubric yaml is mounted read-only from `assets/` (override with `FDR_RUBRIC_HOST_DIR`). On first boot the agent entrypoint builds `data/reference.sqlite` from it and downloads the persona dataset into `data/personas/`; later boots skip both.

## Run on local machine

The override file publishes both ports to the host and scales `cloudflared` to zero, so no tunnel token is needed.

1. Start the stack.

    ```bash
    docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml up --build
    ```

1. Check readiness. `/readyz` reports the reference DB, the writable data directory, and the model key per process.

    ```bash
    # bash/zsh
    curl -s localhost:8000/readyz | python3 -m json.tool
    ```

    ```powershell
    # PowerShell
    Invoke-RestMethod http://localhost:8000/readyz | ConvertTo-Json
    ```

1. Open `http://localhost:8000/docs` in a browser to try the API.

To check a change end to end without model cost, see [Run an End-to-End Check without Model Cost](setup-mock-llm.md).

## Run in production

Production drops the override file. Neither application port is published; the only way in is the tunnel.

1. Set up the tunnel token and hostname as described in [Set Up a Cloudflare Tunnel](setup-cloudflare.md).

1. Start the stack in the background.

    ```bash
    docker compose -f docker/docker-compose.yml up -d --build
    ```

1. Check the services and follow the logs.

    ```bash
    docker compose -f docker/docker-compose.yml ps
    docker compose -f docker/docker-compose.yml logs -f api agent
    ```

## Rebuild the reference DB

Run this after changing the rubric yaml.

1. Delete the DB.

    ```bash
    # bash/zsh
    rm data/reference.sqlite
    ```

    ```powershell
    # PowerShell
    Remove-Item data/reference.sqlite
    ```

1. Restart the agent; its entrypoint rebuilds the DB.

    ```bash
    docker compose -f docker/docker-compose.yml restart agent
    ```

Without a reference DB and a rubric mount the service still starts, and rubric-backed judgments come back `판정 불가`. `GET /readyz` reports which one is missing.

## Persistent data

The `data/` bind mount is shared by both services and is the only persistent state.

| Path | Written by | Holds |
|---|---|---|
| `data/reference.sqlite` | Agent entrypoint | Rubrics, built from the yaml |
| `data/checkpoints.sqlite` | `agent` | Per-thread graph checkpoints |
| `data/jobs.sqlite` | `api` | One row per submitted review |
| `data/snapshots/`, `data/site_rules/` | `agent` | Rendered pages and per-site rules |

> **Important:** Nothing prunes `data/snapshots/`. Watch its size on a long-lived deployment.

## Container notes

- Both images run as uid 1000 (`appuser`), never root.
- `shm_size: 1gb` on the agent replaces Docker's 64MB `/dev/shm`, which Chromium exhausts mid-render.
- `init: true` on the agent reaps browser processes Playwright leaves behind when a run is cut short.
- `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright` puts Chromium where `appuser` can read it.

## Troubleshooting

- **`agent` never turns healthy.** `start_period` is 20s and the first boot also builds the reference DB. Check `docker compose logs agent`.
- **`api` exits at startup.** Either `agent` is unhealthy (the gateway waits for it), or `FDR_API_TOKEN` is unset (exit code 3; the log says so).
- **Jobs fail with `BudgetExceeded`.** The per-run cap was reached. Raise `FDR_MAX_USD` or `FDR_MAX_CALLS`, or pass `max_usd` on the request.
- **Jobs end `interrupted`.** The gateway restarted mid-run. `POST /v1/reruns` with that `thread_id` resumes from the checkpoint.
- **A run times out.** `FDR_RUN_TIMEOUT` (default 1800s) is how long the gateway waits for the worker. The tunnel's limit does not apply because no request is held open across a run.

## Remove

1. Stop the stack. Use the same `-f` files you started it with.

    ```bash
    docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml down
    ```
