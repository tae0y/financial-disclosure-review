# Run the review service in Docker

Two application images and a tunnel sidecar, built and run with Docker Compose.

| Service | Image | Port | Reachable from |
|---|---|---|---|
| `api` | `docker/Dockerfile.api` | 8000 | the tunnel, and the host in local mode |
| `agent` | `docker/Dockerfile.agent` | 8100 | the compose network only |
| `cloudflared` | `cloudflare/cloudflared` | — | outbound only |

The split is not ceremony. The worker carries Chromium and its system libraries — a few GB — while
the gateway carries neither. Editing a route rebuilds the small image, and the process answering
the internet is not the one driving a browser.

## Prerequisites

- Docker Desktop, or Docker Engine with the Compose plugin
- A `.env` at the repository root
- The rubric yaml folder on the host (`05 법령·지침 원문 검증/카드사 가드레일 루브릭`)

## Environment

```bash
cp .env.example .env
```

`OPENAI_API_KEY` and `FDR_API_TOKEN` are the two values the service cannot start without. The
rest have working defaults; `.env.example` documents each one.

The Cloudflare tunnel token is deliberately **not** in `.env`. It lives in `.env.tunnel` (see
`.env.tunnel.example`), read only by the `cloudflared` sidecar, so that container never receives
the model key. The file is optional: local runs scale the tunnel to zero and need no token.

Two worth setting deliberately:

- **`FDR_API_TOKEN`** — required. The gateway exits with code 3 if it is unset, so there is no
  way to start an unauthenticated instance. Issue one with
  `uv run python -m financial_disclosure_review.serving.token`.
- **`FDR_RUBRIC_HOST_DIR`** — the host path mounted read-only at `/app/rubrics`. The default is
  the sibling folder inside `261001 ABC Final Project`; set it if your checkout sits elsewhere.

## The reference DB

`data/*.sqlite` is gitignored and the rubric yaml lives outside the repository, so neither is
baked into the image. The agent entrypoint builds the DB into the mounted `data/` volume on first
boot and skips the work afterwards. Nothing to run by hand.

To force a rebuild after the rubric yaml changes:

```bash
rm data/reference.sqlite
docker compose -f docker/docker-compose.yml restart agent
```

Without a reference DB and without a rubric mount the service still starts, and rubric-backed
judgments come back `판정 불가`. `GET /readyz` reports which of the two is missing.

## Local run

The override file publishes both ports to the host and scales `cloudflared` to zero, so no tunnel
token is needed:

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml up --build
```

Compose picks up `docker-compose.override.yml` automatically when both files sit in the directory
you point `-f` at, but naming it is clearer about which mode you are in.

Then:

```bash
curl -s localhost:8000/healthz
curl -s localhost:8000/readyz | python3 -m json.tool
open http://localhost:8000/docs
```

`/readyz` is the one to read first — it reports the reference DB, the writable data directory and
the model key, per process.

Stop:

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml down
```

## Production run

Drop the override file. Neither application port is published to the host; the only way in is the
tunnel.

```bash
docker compose -f docker/docker-compose.yml up -d --build
docker compose -f docker/docker-compose.yml ps
docker compose -f docker/docker-compose.yml logs -f api agent
```

See [setup-cloudflare.md](setup-cloudflare.md) for the hostname.

## What lives where

The `data/` bind mount is shared by both services and is the only persistent state:

| Path | Written by | Holds |
|---|---|---|
| `data/reference.sqlite` | agent entrypoint | rubrics, built from the yaml |
| `data/checkpoints.sqlite` | agent | per-thread graph checkpoints |
| `data/jobs.sqlite` | api | one row per submitted review |
| `data/snapshots/`, `data/site_rules/` | agent | rendered pages and per-site rules |

Rendered pages accumulate. `data/snapshots/` is worth watching on a long-lived deployment —
nothing prunes it.

## Container notes

Both images run as uid 1000 (`appuser`), never root.

Two settings on the agent exist for Chromium specifically. `shm_size: 1gb` replaces Docker's 64MB
`/dev/shm` default, which Chromium exhausts mid-render. `init: true` reaps the browser processes
Playwright leaves behind when a run is cut short.

`PLAYWRIGHT_BROWSERS_PATH=/ms-playwright` puts Chromium outside any home directory so `appuser`
can read it — Playwright's default is under `~/.cache`, which that user does not have.

## Troubleshooting

**`agent` never turns healthy.** Give it time: `start_period` is 20s and the first boot also builds
the reference DB. Then `docker compose logs agent`.

**`api` exits at startup.** Two causes. It waits on `agent` being healthy, so an unhealthy agent
stops it. Or `FDR_API_TOKEN` is unset — the log says so and the container exits with code 3.

**Jobs come back `failed` with `BudgetExceeded`.** The per-run cap was reached. Raise `FDR_MAX_USD`
or `FDR_MAX_CALLS`, or pass `max_usd` on the request.

**Jobs come back `interrupted`.** The gateway restarted mid-run. The partial run's checkpoints are
still on disk, so `POST /v1/reruns` with that `thread_id` resumes instead of starting over.

**A run times out.** `FDR_RUN_TIMEOUT` (default 1800s) is how long the gateway waits for the
worker. The tunnel's own limit does not apply — no request is held open across a run.
