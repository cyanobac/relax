# Relax Architecture

_Version: 1.0 — Architecture_  
_Status: Stable_

Relax is a public, unauthenticated web app that converts an Oura Daytime Stress screenshot into structured `(timestamp, zone)` rows. It is intentionally small: a React/Vite frontend, a FastAPI OCR backend, and Caddy as the public reverse proxy.

## High-Level Topology

```text
Browser
  |
  | HTTPS / static assets / POST /api/extract
  v
Caddy
  |-- non-/api/* ----------> frontend nginx container -> static Vite bundle
  |
  `-- /api/* --------------> backend FastAPI container -> OpenCV + Tesseract
                                      |
                                      `-> SQLite files in /data
```

In production, only Caddy publishes ports 80 and 443. The backend and frontend containers are internal Docker services reached by service name. In local frontend development, Vite proxies `/api` to `127.0.0.1:8000` so the browser code can use the same relative API paths as production.

## Repository Layout

- `frontend/`: React + TypeScript + Vite application.
- `frontend/src/api.ts`: typed client for `POST /api/extract`.
- `frontend/src/App.tsx`: upload flow, extraction result display, CSV/Markdown copy/download UI, annotated image preview, and theme state.
- `frontend/src/zones.ts`: stress-zone labels, order, and display metadata.
- `backend/app/main.py`: FastAPI app construction, CORS for local Vite, and Tesseract startup configuration.
- `backend/app/routes.py`: API endpoints, upload validation, concurrency controls, rate limiting, request logging, and HTTP error mapping.
- `backend/app/extractor/`: vendored extraction core from the larger daystar project.
- `backend/tests/`: pytest suite, including OCR-backed golden tests and fixtures.
- `Caddyfile`, `docker-compose.yml`, `.env.example`: production and local Docker deployment configuration.

## Frontend Architecture

The frontend is a static single-page app. It collects a screenshot file, a reference date, and an `include_image` option, then submits multipart form data to `/api/extract`. The API client returns:

- `points`: extracted timestamp/zone rows.
- `gaps`: detected missing 15-minute intervals.
- `warnings`: duplicate timestamp or extraction-quality warnings.
- `meta`: reference date, inferred chart bounds, and detected/used dot counts.
- `annotated_png`: optional base64 PNG preview with detected dots drawn.

The UI is deliberately same-origin. In production, Caddy routes `/api/*` to FastAPI and everything else to the static frontend. In development, `vite.config.ts` mirrors that setup with a proxy. `CONTACT_EMAIL` is compiled into the static bundle as `VITE_CONTACT_EMAIL`; changing it requires rebuilding the frontend image.

The frontend has no configured test runner. TypeScript strictness and `npm run build` provide the current automated validation.

## Backend API

The FastAPI backend exposes:

- `GET /api/health`: health check used by Docker Compose.
- `POST /api/extract`: OCR extraction endpoint.

`POST /api/extract` accepts multipart fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `file` | file | PNG/JPEG Oura screenshot |
| `date` | string | reference date in `YYYY-MM-DD` format |
| `include_image` | bool | include annotated PNG in the response |

The route validates the date, reads at most 1 MB plus one byte, rejects empty or oversized uploads, applies the per-IP quota, and then runs the synchronous extraction pipeline in a worker thread. OCR is CPU-bound, so it is never run on the event loop.

Expected response classes:

- `200`: extraction succeeded.
- `413`: uploaded body exceeds 1 MB.
- `422`: bad date, empty upload, undecodable image, wrong dimensions, or no dots detected.
- `429`: per-IP quota exceeded.
- `503`: too many active or queued extractions.
- `504`: extraction exceeded the timeout.
- `500`: unexpected backend failure; full details are logged server-side only.

## Extraction Pipeline

The extractor expects a 640 x 1136 iPhone SE/8-class Oura Daytime Stress screenshot, with a small dimension tolerance. This is a core architectural constraint: the mask, crop regions, dot bounds, OCR regions, and zone y-coordinate mapping all depend on that resolution. Unsupported dimensions are rejected rather than processed with incorrect geometry.

Pipeline summary:

1. Parse PNG/JPEG headers for a decompression-bomb guard.
2. Decode image bytes with OpenCV.
3. Validate screenshot dimensions.
4. Preprocess the chart and apply the bundled mask.
5. OCR the x-axis labels with Tesseract to anchor first and last times.
6. Detect chart dots with OpenCV Hough circles.
7. Filter dots to the chart x-range.
8. Map each dot x-position to a 15-minute timestamp.
9. Map each dot y-position to a stress zone.
10. Detect interior gaps and duplicate timestamps.
11. Produce structured points plus an annotated preview image.

The backend caller passes the reference date explicitly. The original daystar CLI derived dates from filenames; this app intentionally avoids that filesystem coupling.

## Concurrency, Rate Limiting, and Timeouts

OCR can consume significant CPU and memory, so the backend has several controls:

- `MAX_UPLOAD_BYTES`: 1 MB upload limit in FastAPI, matched by Caddy `request_body max_size 1MB`.
- `MAX_CONCURRENT_EXTRACTIONS`: number of OCR jobs allowed to run at once, default `2`.
- `MAX_INFLIGHT_EXTRACTIONS`: running plus queued requests allowed, default `6`.
- `EXTRACT_TIMEOUT_SECONDS`: per-request timeout, default `30`.
- Docker backend memory limit: `2.5G`.

The inflight counter rejects excess requests before they accumulate uploaded bytes and open connections. The timeout frees the client-facing request path, although Python cannot forcibly kill the worker thread; the orphaned OCR thread is allowed to finish.

Rate limiting is stored in SQLite. `RATE_LIMIT_MAX` defaults to `10` successful extractions per IP per rolling 24-hour window. Only `200` responses are recorded against the quota, so failed attempts do not consume a user’s daily allowance. The counter persists in the Docker volume at `/data/ratelimit.db`.

## Request Logging and Observability

Every API request, including rejections, is logged to a separate SQLite database when `REQUEST_LOG` is not `0`. The log records:

- UTC timestamp.
- SHA-256 hash of `REQUEST_LOG_SALT + client_ip`.
- processing time in milliseconds.
- returned HTTP status.
- success flag.
- nullable error detail.

Raw IP addresses are not stored. The salt must remain stable across restarts if repeat-visitor correlation matters. Logging is best-effort: failures are caught and logged without breaking the request path.

There is deliberately no admin HTTP endpoint. Operators inspect logs out of band with:

```bash
cd backend
python -m app.logdump --limit 100
```

Under Docker, run the command inside the backend container and copy the output from `/data` if needed.

## Security and Hardening

The app is public and unauthenticated, so hardening focuses on limiting blast radius and bounding resource use.

Caddy controls the public edge:

- Terminates TLS.
- Serves JSON access logs to stdout.
- Enforces the same 1 MB API upload cap as the backend.
- Sets `X-Real-IP` for backend quota and logging.
- Sets HSTS, CSP, `nosniff`, referrer policy, permissions policy, and frame denial headers.
- Removes the `Server` header.
- Pins the single inline frontend script in the CSP by SHA-256 hash.

Container hardening:

- Backend and frontend run as non-root users.
- Backend, frontend, and Caddy use `no-new-privileges:true`.
- Linux capabilities are dropped from all services.
- Caddy receives only `NET_BIND_SERVICE` so it can bind ports 80/443.
- Backend has no published host port.
- Frontend has no published host port.
- SQLite data is stored in a named Docker volume rather than the image filesystem.

Application hardening:

- Date parsing is explicit.
- Upload size is bounded before decode.
- PNG/JPEG dimensions are checked before decode where possible.
- Decoded screenshots are dimension-validated before extraction.
- Expected extraction failures use user-facing 422 responses.
- Unexpected exceptions return a generic 500 and log details server-side.
- Request logging stores salted IP hashes, not raw IPs.

## Deployment Strategy

The preferred deployment is Docker Compose behind Cloudflare:

1. Build and run `backend`, `frontend`, and `caddy` with `docker compose up -d --build`.
2. Point DNS at the host and enable Cloudflare proxying.
3. Set `CADDY_SITE_ADDR=https://your-domain`.
4. Set `CADDY_TLS_SNIPPET=tls_origin`.
5. Mount Cloudflare Origin Certificate files into `./certs/origin.pem` and `./certs/origin-key.pem`.
6. Configure Cloudflare SSL/TLS mode as Full (strict).
7. Restrict the origin firewall so ports 80/443 accept only Cloudflare IP ranges.

The `Caddyfile` lists Cloudflare ranges as trusted proxies so Caddy’s `{client_ip}` resolves to the real visitor. That value is forwarded to the backend as `X-Real-IP`, which drives rate limiting and request logging.

Local Docker defaults are intentionally simpler: `CADDY_SITE_ADDR=http://localhost` and `CADDY_TLS_SNIPPET=no_tls` serve plain HTTP on localhost. Local source development usually runs FastAPI directly on port 8000 and Vite on port 5173.

## Configuration Reference

Important runtime variables. Defaults below reflect the code as of v1.0;
`.env.example` and the code are authoritative if they disagree:

| Variable | Default | Purpose |
| --- | --- | --- |
| `CADDY_SITE_ADDR` | `http://localhost` | public site address Caddy serves |
| `CADDY_TLS_SNIPPET` | `no_tls` | Caddy TLS mode, usually `tls_origin` in production |
| `CONTACT_EMAIL` | empty | frontend footer mailto, baked into build |
| `REQUEST_LOG` | `1` | disables request logging when set to `0` |
| `REQUEST_LOG_DB` | `/data/requests.db` in Docker | durable request log path |
| `REQUEST_LOG_SALT` | empty | salt for hashed IPs; set in production |
| `RATE_LIMIT_DB` | `/data/ratelimit.db` in Docker | quota database path |
| `RATE_LIMIT_MAX` | `10` | successful extractions per IP per window |
| `RATE_LIMIT_WINDOW_HOURS` | `24` | rolling quota window |
| `MAX_CONCURRENT_EXTRACTIONS` | `2` | OCR jobs running concurrently |
| `MAX_INFLIGHT_EXTRACTIONS` | `6` | running plus queued extraction requests |
| `EXTRACT_TIMEOUT_SECONDS` | `30` | per-extraction timeout |
| `TESSERACT_CMD` | auto-detect | explicit Tesseract binary path |
| `CORS_ORIGINS` | `http://localhost:5173` | local development browser origin |

## Testing Strategy

Backend tests use `pytest`. The suite covers request logging, rate limiting, route behavior, and the extraction core. The golden extraction test runs real OCR against fixtures in `backend/tests/fixtures/` so changes to extraction logic are visible. Tesseract must be installed for the full suite.

Frontend validation is currently build-based:

```bash
cd frontend
npm run build
```

For end-to-end confidence, run the backend on port 8000 and the Vite frontend on port 5173, or run the complete stack with Docker Compose.

## Key Tradeoffs and Constraints

- The app favors correctness over broad device support. Unknown screenshot sizes are rejected because the extractor geometry is resolution-specific.
- The service is unauthenticated, so abuse control is layered: Cloudflare for volumetric traffic, Caddy for edge limits and headers, FastAPI for quotas and concurrency, and Docker for process isolation.
- SQLite is sufficient because state is small, local, and append/count oriented. There is no multi-host deployment model.
- The frontend is static and simple by design; most complexity belongs to the extractor and operational hardening.
- The extraction core is vendored from daystar. Golden tests should guard behavior when updating it.
