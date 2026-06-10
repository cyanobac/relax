# Repository Guidelines

## Project Structure & Module Organization

Relax extracts Oura Daytime Stress data from screenshots. The backend is a FastAPI service in `backend/`. Application code is under `backend/app/`, with routing in `routes.py`, startup in `main.py`, logging/rate limiting in dedicated modules, and the vendored extraction pipeline in `backend/app/extractor/`. Backend tests and fixtures are in `backend/tests/`.

The frontend uses React, TypeScript, and Vite in `frontend/`. UI code is in `frontend/src/`, with API calls in `api.ts`, zone metadata in `zones.ts`, and styles in `index.css`. Shared screenshots are in `assets/`. Deployment files are `docker-compose.yml`, `Caddyfile`, and `.env.example`.

## Build, Test, and Development Commands

- `cd backend && pip install -r requirements-dev.txt`: install backend and test dependencies.
- `cd backend && uvicorn app.main:app --reload --port 8000`: run the API.
- `cd backend && pytest`: run backend tests. Tesseract is required; set `TESSERACT_CMD` if needed.
- `cd frontend && npm install`: install frontend dependencies. Use Node.js v20.19+ or v22.12+.
- `cd frontend && npm run dev`: start Vite on `http://localhost:5173`.
- `cd frontend && npm run build`: type-check and build the frontend.
- `docker compose up --build`: run the full stack through Caddy.

## Coding Style & Naming Conventions

Python uses 4-space indentation and small modules with explicit error boundaries. Keep expected user failures as `ExtractionError` or handled `ValueError` paths that map to 422.

TypeScript uses 2-space indentation, ES modules, React function components, and local helpers. Name components in `PascalCase`, functions and variables in `camelCase`, and fixed constants in `UPPER_SNAKE_CASE`.

## Testing Guidelines

Backend tests use `pytest` and live in `backend/tests/test_*.py`. OCR-backed golden tests use fixtures in `backend/tests/fixtures/`; do not update expectations without understanding the extraction change. Add focused tests for route behavior, rate limiting, logging, and extractor edge cases. No frontend test runner is configured, so validate UI changes with `npm run build` and manual browser checks.

## Commit & Pull Request Guidelines

Recent history uses short, imperative summaries, sometimes with conventional prefixes such as `chore(security): ...`. Prefer concise commits that describe the user-visible or operational change, for example `fix: reject oversized screenshots`.

Pull requests should include a short description, testing performed, linked issues when relevant, and screenshots for UI changes. Call out deployment, security, environment variable, and fixture changes.

## Security & Configuration Tips

Do not commit `.env`, private certificates, logs, or generated databases. Keep `REQUEST_LOG_SALT` stable in deployments. `CONTACT_EMAIL` is baked into the frontend bundle at build time.
