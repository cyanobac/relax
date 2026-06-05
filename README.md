# Oura Stress Extractor

A small web app that turns a screenshot of Oura's **Daytime Stress** screen into a
table of `(time, stress zone)` rows. Oura has no public API for this data, so this
scrapes it off the app screen with OpenCV + Tesseract OCR.

Upload a screenshot, pick the date, and get a table you can copy or download as CSV.

> Extracted from the larger *daystar* project as a standalone, shareable repo.
> The extraction core (`backend/app/extractor/`) is vendored from daystar's
> `extractor/` package.

## How it works

1. **Mask** the chart to remove the zone labels ("Stressed", "Engaged", …).
2. **Detect dots** with `cv2.HoughCircles`.
3. **OCR the x-axis** time labels to anchor the chart's start/end times.
4. Map each dot's x-position to a 15-minute timeslot → timestamp, and its
   y-position to a stress zone.

### ⚠️ Fixed-resolution assumption

All the pixel geometry (dot x-range, crop bounds, OCR regions, the bundled mask)
assumes a **640×1136** screenshot (Oura on an iPhone SE/8-class device). Uploads of
other sizes are **rejected** rather than silently producing a wrong table. If you
capture on a different device, the constants in
`backend/app/extractor/core.py` and `image_helpers.py` need re-tuning.

## Develop locally

**Backend** (needs Tesseract installed locally, or just use Docker):

```bash
cd backend
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend** (proxies `/api` → `127.0.0.1:8000`):

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

## Tests

```bash
cd backend
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest
```

The suite includes a **golden test** that pins the vendored core's output to the
daystar CLI's known-good result for the bundled 2026-02-10 sample, so the copy
can't silently drift. Tests run real OCR, so Tesseract must be installed
(`TESSERACT_CMD` overrides the binary path).

## Run with Docker (local)

```bash
docker compose up --build
# DOMAIN defaults to localhost → Caddy serves a self-signed cert at https://localhost
```

## Deploy on Docker host

1. Point a DNS A record at the server.
2. `cp .env.example .env` and fill in `DOMAIN`, `BASIC_AUTH_USER`, `BASIC_AUTH_HASH`
   (generate the hash with
   `docker run caddy:2-alpine caddy hash-password --plaintext 'yourpass'`).
3. `docker compose up -d --build`

Caddy terminates TLS (auto Let's Encrypt), gates the site behind basic auth, serves
the static frontend, and reverse-proxies `/api/*` to the backend. Only ports 80/443
are exposed; the backend and frontend containers are internal.

## API

`POST /api/extract` (multipart form)

| field          | type   | notes                                  |
| -------------- | ------ | -------------------------------------- |
| `file`         | file   | PNG/JPEG screenshot, 640×1136          |
| `date`         | string | `YYYY-MM-DD`, the day the chart covers |
| `include_image`| bool   | return annotated chart as base64 PNG   |

Returns `{ points, gaps, warnings, meta }` (plus `annotated_png` if requested).

`GET /api/health` → `{ "status": "ok" }`

## License

MIT — see [LICENSE](LICENSE).
