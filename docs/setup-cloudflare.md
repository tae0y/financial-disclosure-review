# Serve the API through a Cloudflare tunnel

The tunnel gives the gateway a public hostname with no inbound port open on the host.
`cloudflared` dials out to Cloudflare and traffic arrives over that connection, so the machine
needs no port forwarding, no static address and no certificate of its own.

## What the tunnel reaches

Only `api:8000`. The worker is on the same compose network and publishes nothing, so a public
route to it cannot be created by accident.

## One-time setup

1. In the Cloudflare Zero Trust dashboard, open **Networks → Tunnels** and create a tunnel.
   Choose the **Docker** connector; the token in the command it shows is what you need.
2. Put that token in `.env`:

   ```
   CLOUDFLARE_TUNNEL_TOKEN=eyJhIjoi...
   ```

   It is a credential for your account. It belongs in `.env`, which is gitignored and is never
   copied into an image — compose passes it at run time.
3. Add a **public hostname** to the tunnel:

   | Field | Value |
   |---|---|
   | Subdomain | e.g. `disclosure-review` |
   | Domain | your domain |
   | Service type | `HTTP` |
   | URL | `api:8000` |

   `api` is the compose service name. `cloudflared` resolves it on the shared network, which is
   why the URL is not `localhost`.
4. Start the stack without the local override:

   ```bash
   docker compose -f docker/docker-compose.yml up -d --build
   ```

5. Check it:

   ```bash
   curl -s https://disclosure-review.example.com/healthz
   ```

## Before you point a hostname at it

**Set `FDR_API_KEYS`.** The tunnel makes the API reachable from anywhere. With that variable empty
every caller is accepted, and each accepted call spends model credit. Set it, restart `api`, and
confirm that an unauthenticated request now returns 401:

```bash
curl -s -o /dev/null -w '%{http_code}\n' -X POST https://your-hostname/v1/reviews \
  -H 'Content-Type: application/json' -d '{"url":"https://example.com"}'
# expect 401
```

Optionally add a Zero Trust **Access** policy in front of the hostname for a second layer. The API
key check is independent of it and stays useful for machine callers.

## Why the 100-second limit does not bite

Cloudflare closes a response that produces nothing for about 100 seconds, and a review takes
minutes. The API is built around that: submitting returns `202` immediately and the caller polls.
No request is ever held open across a run, so the limit is never reached. This is the reason for
the job model — see [api.md](api.md).

## Troubleshooting

**Error 1033, or the hostname does not resolve.** The tunnel is not connected.
`docker compose logs cloudflared` — a missing or wrong `CLOUDFLARE_TUNNEL_TOKEN` shows here.

**502 from the hostname.** `cloudflared` is up but cannot reach the service. The public hostname's
URL must be `api:8000`, not `localhost:8000`.

**`cloudflared` never starts.** It waits on `api` being healthy, which waits on `agent`. Check
those first: `docker compose ps`.
