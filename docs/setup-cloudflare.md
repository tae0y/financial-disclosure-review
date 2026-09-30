# Set Up a Cloudflare Tunnel

This page describes how to give the review API a public hostname through a Cloudflare tunnel, with no inbound port open on the host.

`cloudflared` dials out to Cloudflare, and traffic arrives over that connection. The host needs no port forwarding, static address, or certificate. The tunnel reaches only `api:8000`; the worker publishes nothing, so a public route to it cannot be created by accident.

## Prerequisites

- A [Cloudflare](https://dash.cloudflare.com/) account with a domain
- The service set up as in [Run the Review Service in Docker](setup-docker.md#prepare-the-environment)

## Create the tunnel

1. In the Cloudflare Zero Trust dashboard, open **Networks → Tunnels**, create a tunnel, and choose the **Docker** connector. Copy the token from the command it shows.

1. Create `.env.tunnel` from its example.

    ```bash
    # bash/zsh
    cp .env.tunnel.example .env.tunnel
    ```

    ```powershell
    # PowerShell
    Copy-Item .env.tunnel.example .env.tunnel
    ```

1. Set `TUNNEL_TOKEN` in `.env.tunnel` to the copied token.
   The token lives in its own file so the sidecar never receives the model key in `.env`. Both files are gitignored and never copied into an image.

1. Add a **public hostname** to the tunnel.

    | Field | Value |
    |---|---|
    | Subdomain | e.g. `disclosure-review` |
    | Domain | Your domain |
    | Service type | `HTTP` |
    | URL | `api:8000` |

   `api` is the compose service name, which `cloudflared` resolves on the shared network. Do not use `localhost`.

1. Start the stack without the local override file.

    ```bash
    docker compose -f docker/docker-compose.yml up -d --build
    ```

## Verify access control

> **Important:** The tunnel makes the API reachable from anywhere, and each accepted call spends model credit. Confirm the deployed instance rejects anonymous callers before sharing the hostname.

1. Check that an anonymous review request is rejected with `401`.

    ```bash
    # bash/zsh
    curl -s -o /dev/null -w '%{http_code}\n' -X POST https://<your-hostname>/v1/reviews \
      -H 'Content-Type: application/json' -d '{"url":"https://example.com"}'
    ```

    ```powershell
    # PowerShell
    try { Invoke-WebRequest -Method Post -Uri https://<your-hostname>/v1/reviews `
        -ContentType application/json -Body '{"url":"https://example.com"}' } `
    catch { $_.Exception.Response.StatusCode.value__ }
    ```

1. Check that the health endpoint answers `200`.

    ```bash
    # bash/zsh
    curl -s -o /dev/null -w '%{http_code}\n' https://<your-hostname>/healthz
    ```

    ```powershell
    # PowerShell
    (Invoke-WebRequest https://<your-hostname>/healthz).StatusCode
    ```

Hand the token to callers over a channel you would use for any credential. Optionally add a Zero Trust **Access** policy in front of the hostname; the token check stays independent of it.

## Rotate the token

1. Set `FDR_API_TOKEN` to the old and new tokens, comma-separated, and restart `api`.
1. Move every caller to the new token.
1. Remove the old token from `FDR_API_TOKEN` and restart `api` again.

## Why the 100-second limit does not apply

Cloudflare closes a response that produces nothing for about 100 seconds, and a review takes minutes. Submitting returns `202` at once and the caller polls, so no request is held open across a run. See [HTTP API](api.md).

## Troubleshooting

- **Error 1033, or the hostname does not resolve.** The tunnel is not connected. Check `docker compose logs cloudflared` and that `.env.tunnel` holds `TUNNEL_TOKEN`; the file is optional, so a missing one raises no error.
- **502 from the hostname.** `cloudflared` cannot reach the service. The public hostname's URL must be `api:8000`, not `localhost:8000`.
- **`cloudflared` never starts.** It waits for `api` to be healthy, which waits for `agent`. Check `docker compose ps`.

## Remove

1. Stop the stack.

    ```bash
    docker compose -f docker/docker-compose.yml down
    ```

1. Delete the tunnel in **Networks → Tunnels** in the Zero Trust dashboard.
