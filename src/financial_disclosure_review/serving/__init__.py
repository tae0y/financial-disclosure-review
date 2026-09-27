"""HTTP serving layer: the public FastAPI gateway and the internal agent worker.

Two processes, two images. `api/` takes the outside request, owns the job store, and answers
immediately; `agent/` holds the LangGraph app, Playwright and Chromium, and runs one review at a
time. They speak over the compose-internal network only — nothing but `api/` is reachable from
the Cloudflare tunnel.
"""
