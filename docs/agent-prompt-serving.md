# Prompt: serve a LangGraph agent as an HTTP API behind a Cloudflare tunnel

A task prompt to hand to a coding agent working in a repository that already has a working
LangGraph (or LangChain) app driven by a CLI, and now needs that app callable over HTTP.

**How to use it.** Paste the whole document into the agent as the task. Replace the values in
*Fill these in first*; everything else is meant to be followed as written. The constraints in
§2 are the point of the document — they are failures already paid for once, and an agent that
skips them will produce something that passes a smoke test and breaks in production.

---

## Fill these in first

| Placeholder | Meaning | Example |
|---|---|---|
| `<PACKAGE>` | Import path of the existing app | `financial_disclosure_review` |
| `<GRAPH_ENTRY>` | Function that builds/compiles the graph | `graph.build.build_review_graph` |
| `<INVOKE_ARGS>` | What one run needs as input | a product page URL |
| `<RUN_MINUTES>` | Rough wall-clock of one run | 2–10 minutes |
| `<BROWSER>` | Does a run drive a browser? | yes, Playwright + Chromium |

---

## 1. The task

Add an HTTP surface to this repository without changing how the agent itself makes decisions.

Deliver:

1. A **worker** process holding the graph, exposing a small internal API.
2. A **gateway** process: the only thing reachable from outside. It validates, authenticates,
   owns a job store, and answers immediately.
3. **Two container images** — one per process — plus a `cloudflared` sidecar, wired with Compose.
4. **Tests** that run with no network, no model call and no browser.
5. A **committed OpenAPI document** and setup docs.

The existing CLI keeps working and keeps its behaviour. The serving layer is a second entry point
onto the same graph, not a replacement, and the two never import each other.

---

## 2. Hard constraints

Each of these is a real failure, not a style preference. The failure is stated so you can tell
whether your implementation avoids it.

### 2.1 Submission must not return the result

A run takes `<RUN_MINUTES>`. Cloudflare terminates a response that has produced no bytes for about
100 seconds. A synchronous endpoint therefore fails on precisely the runs that worked.

`POST` returns `202` with a job id; the caller polls. No request is held open across a run.

> **Failure if violated:** works on localhost, returns 524 through the tunnel, and the failure
> scales with how well the agent is doing its job.

### 2.2 Job state goes on disk, not in a dict

The job row is the API contract. If the gateway restarts, a caller polling an id must get an
answer rather than a 404. SQLite in a mounted volume is enough; no queue broker is needed for a
single-node deployment.

### 2.3 No row may ever be left `running`

A `running` row with no process behind it makes a caller poll for ever. Close out every path:

- The task raised → `failed`, with the message.
- The process is shutting down → `interrupted`.
- The process already died → the **next boot** sweeps `queued`/`running` rows to `interrupted`.

**Ordering matters on shutdown.** Cancel the tasks, `await` them, *then* write the rows, *then*
close the store. A cancelled coroutine cannot reach another `await`, so it cannot write its own
row — do that sweep from the shutdown handler, not from inside the cancelled task.

> **Failure if violated:** `sqlite3.ProgrammingError: Cannot operate on a closed database` during
> shutdown, and rows stuck at `running` for ever.

### 2.4 Audit the app for process-global state before serving it

A CLI runs once and exits, so module-level globals are harmless there. A server does not.

Search the codebase for module-level mutable state — token/cost meters, caches, counters,
"current run" singletons:

```bash
grep -rnE '^_[a-z_]+ *=|^[A-Z_]+ *= *(\[|\{)|global ' src/<PACKAGE> --include='*.py'
```

For each one, decide: reset per request, or serialize runs, or both.

In the reference implementation the cost meter was a module-level global that nothing reset. Left
alone it would have accumulated spend across requests and then raised `BudgetExceeded` on every
later request, permanently. The fix was to start a fresh meter per run **and** run one at a time.

> **Failure if violated:** the service works for the first few requests of its life and then fails
> for ever until restarted. Nothing in a smoke test catches it.

### 2.5 Concurrency follows from 2.4, not from taste

If shared state forces one run at a time, say so in code and in config, and scale with **worker
replicas** rather than threads — separate processes get separate globals. Put a matching limit on
the gateway so surplus submissions sit as `queued` instead of piling up inside an HTTP call.

### 2.6 Identifiers need entropy, not just a timestamp

A CLI's second-resolution id is unique for one person at a terminal. Two API submissions can land
in the same millisecond; a shared checkpoint thread id means two runs writing one history.

Append a random tail: `review-260927-101500-a1b2c3`. Keep the timestamp so ids stay sortable.

> **Test it:** generate 50 ids in a tight loop and assert 50 distinct values. A timestamp-only
> scheme fails this immediately.

### 2.7 The graph's state is not the response body

Agent state often holds the raw input — rendered HTML, retrieved documents, images. That can be
hundreds of kilobytes, and it is already on disk or in checkpoints.

Define an explicit response model that carries counts, verdicts and the final artifact. Offer a
`detail=full` level for the per-item rows. Never serialize the whole state.

> **Test it:** flatten the response to a string and assert a long marker from the source input
> does not appear in it, at every `detail` level.

### 2.8 Auth must be declared, not just enforced

Reading a header inside a handler protects the route but leaves the OpenAPI document silent, so a
generated client cannot authenticate. Declare a real security scheme (`APIKeyHeader`) so the
requirement appears in the document.

Compare keys with `hmac.compare_digest`. Keep health endpoints unauthenticated so container probes
need no credential — and assert that in a test, so no `/v1` route quietly becomes public.

**Default-open is a deliberate decision with a loud warning.** If no keys are configured, log a
warning at startup saying every caller is accepted. Each accepted call spends model credit.

### 2.9 Secrets reach the container at run time

`.env` goes in `.dockerignore` and in `env_file:`. No secret is ever `COPY`-ed into a layer.

### 2.10 Only the gateway is reachable

The worker uses `expose:`, never `ports:`, in the production Compose file. Publish ports only in a
local override file, which should also scale `cloudflared` to zero so local work needs no token.

### 2.11 `<BROWSER>` — if a run drives a browser

Four settings, each for a specific failure:

| Setting | Without it |
|---|---|
| `shm_size: "1gb"` | Chromium exhausts Docker's 64MB `/dev/shm` and crashes mid-render |
| `init: true` | Zombie browser processes accumulate when a run is cut short |
| `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright` | A non-root user cannot read browsers installed under `~/.cache` |
| A font package for your content's script | Text renders as tofu, or in a fallback face from the wrong language |

Install the browser **as root, before the `USER` switch**, through the pinned library
(`playwright install --with-deps chromium`) so the browser build matches the wheel.

The font point is easy to dismiss and worth taking seriously when a vision model reads the
rendering: a Debian slim image has no CJK font, so Chromium falls back to a Chinese face for
Korean. The text is legible, which is why this survives review — but the model is then judging
type that no real user is shown. Install `fonts-noto-cjk` (or the equivalent for your script) and
**verify by looking at a screenshot**, not by checking that a package is installed.

---

## 3. Build order

Work in this order and do not start a step before the previous one's gate passes.

**Step 1 — read before writing.** Find the CLI entry point, how the graph is invoked, what
settings it takes, what it writes to disk, and which files are gitignored. Run the existing test
suite and record the pass count. Do the §2.4 global-state audit now and write down what you find.

*Gate:* you can state, in one paragraph, what one run reads, writes, and how long it takes.

**Step 2 — serving package.** Add a `serving/` package beside the CLI: settings from environment,
shared request/response schemas, a runner that wraps one graph invocation. Respect the project's
existing layering rules and document the new package where the others are documented.

*Gate:* `python -c "import <PACKAGE>.serving"` succeeds and the existing tests still pass.

**Step 3 — worker.** A FastAPI app with `/healthz`, `/readyz` and the run endpoint. Blocking work
goes to a thread (`anyio.to_thread.run_sync`); sync browser APIs must not run on the event loop.
Build it with a `create_app(settings)` factory so tests do not need environment variables.

*Gate:* `uvicorn` starts it locally and `/healthz` answers.

**Step 4 — gateway.** Job store, background dispatch, auth, and the polling routes. Write the
tests here, against a stub worker — no graph, no model, no browser.

*Gate:* tests cover the success path, worker refusal, unexpected crash, cancelled-at-shutdown,
restart sweep, auth accept/reject, and validation rejection. All pass in under a second.

**Step 5 — images.** One Dockerfile per process, multi-stage, dependencies installed before source
so an edit does not re-resolve the lock. Non-root user, healthcheck, pinned base images.

*Gate:* both images build. **Verify the base image tag exists before using it** —
`docker manifest inspect <image>:<tag>` — rather than assuming a version tag is published. A tag
that merely looks plausible is a failed build minutes later.

**Step 6 — Compose.** Worker `expose`-only, gateway with a healthcheck, `cloudflared` depending on
the gateway being healthy, plus a local override publishing ports and scaling the tunnel to zero.

*Gate:* `docker compose ... config --quiet` passes, the stack comes up, and every service reports
healthy.

**Step 7 — prove it end to end.** See §4.

**Step 8 — document.** Export the OpenAPI document to a committed file and add a test that fails
when it drifts from the code. Write the setup and API docs. Validate the document with an external
validator (`uvx openapi-spec-validator <file>`), not only your own assertions.

---

## 4. Verification

Run these against the live stack. Each one checks something unit tests cannot.

```bash
# Both processes, and their dependencies, are actually ready.
curl -s localhost:8000/readyz | python3 -m json.tool

# A failing run must land on the job row, not hang and not 500 the submission.
job=$(curl -sS -X POST localhost:8000/v1/reviews \
        -H 'Content-Type: application/json' \
        -d '{"url":"http://127.0.0.1:9/nothing"}' \
      | python3 -c 'import json,sys; print(json.load(sys.stdin)["job_id"])')
sleep 5
curl -sS "localhost:8000/v1/reviews/$job" | python3 -m json.tool   # expect status=failed + a real message

# Auth actually plumbs through Compose, not just through the test client.
FDR_API_KEYS=test-key docker compose ... up -d gateway && sleep 6
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/v1/reviews                        # 401
curl -s -o /dev/null -w '%{http_code}\n' -H 'X-API-Key: test-key' localhost:8000/v1/reviews  # 200
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/healthz                           # 200
```

If a run drives a browser, exercise it inside the container **without** spending model credit:
launch the browser on locally-set content, read back a computed style, take a screenshot, and
**look at the image**.

Running a full paid end-to-end review is the user's call, not yours. Ask before spending model
credit or hitting a live third-party site, and respect any repository convention that already
separates paid tests from free ones.

---

## 5. Anti-patterns

- **Adding Celery, Redis or RabbitMQ.** For a single node with one worker, a SQLite table and a
  background task are the whole job system. Reach for a broker when you have multiple nodes.
- **One image for both processes.** The worker is gigabytes of browser; the gateway is not.
  Merging them means every route edit rebuilds the browser image.
- **Streaming the run to keep the connection alive.** Heartbeat bytes to defeat an idle timeout
  makes the client hold a connection for the whole run and lose everything on a blip. Poll.
- **Returning the whole graph state** "so the caller can decide". See §2.7.
- **Reading settings at import time in a module global.** Use a factory that takes settings, or
  tests will need environment variables and process reloads.
- **Trusting a healthcheck as readiness.** Liveness is "the process answers". Readiness is "its
  dependencies are present" — keep them as separate endpoints.
- **Declaring done on a green unit suite.** The interesting failures here — browser in a
  container, fonts, Compose wiring, base image tags, shutdown ordering — only appear in a running
  container.

---

## 6. Acceptance criteria

- [ ] The existing CLI behaves as it did, and the pre-existing tests still pass.
- [ ] Submission returns `202`; no endpoint holds a connection open for the length of a run.
- [ ] Every job reaches a terminal status: on success, failure, crash, shutdown and restart.
- [ ] Process-global state is audited; findings are fixed and documented in code comments.
- [ ] Identifiers survive 50 generations in a tight loop without collision.
- [ ] No raw input payload appears in any response, at any `detail` level.
- [ ] The OpenAPI document declares the security scheme; `/v1` routes require it and health
      routes do not, both asserted by tests.
- [ ] The committed OpenAPI file has a drift test and passes an external validator.
- [ ] Only the gateway is reachable in the production Compose file.
- [ ] Both images run as a non-root user and contain no secret.
- [ ] If a browser is involved: verified inside the container, including a screenshot you looked at.
- [ ] Docs cover local run, production run, the tunnel, and troubleshooting.
