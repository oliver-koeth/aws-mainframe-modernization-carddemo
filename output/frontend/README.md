# Frontend Scaffold

Phase 0 now includes the Angular workspace scaffold for the modernization frontend.
This workspace intentionally stops at the minimum standalone application shell needed
for compilation and later feature slices. Business routes and feature components
will be added in subsequent stories under `output/frontend/`.

## Development Proxy

Local development uses the Angular dev-server proxy so all frontend code targets the
shared `/api` base path without enabling wildcard credentialed CORS in FastAPI.
Requests sent to `/api/*` from the browser are forwarded to the backend at
`http://127.0.0.1:8000/*`.

Run the paired local dev servers from their workspace roots:

```bash
cd output/backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```bash
cd output/frontend
npm start -- --host 127.0.0.1 --port 4200
```

With both processes running, browser code should call backend routes with relative
paths such as `/api/openapi.json` or future scaffold endpoints under `/api/jobs`.

## Build Verification

Use the frontend workspace build command for local verification and later CI wiring:

```bash
cd output/frontend
npm run build
```

The scaffold keeps this command rooted in `output/frontend/` so later UI slices can
reuse the same verification entrypoint without changing package metadata.

## Playwright Smoke Tests

The baseline browser smoke tests live under `output/frontend/e2e/` and run the
scaffolded frontend and backend together before executing Playwright checks.

```bash
cd output/frontend
npm run test:e2e
```

The Playwright config starts the backend from `../backend/.venv/bin/python` on
`127.0.0.1:8000` and the Angular dev server on `127.0.0.1:4200`, then runs the
smoke suite against the proxied frontend at `/jobs`.

## Shared API Client

Frontend code should reach backend routes through the shared `ApiClientService` in
`src/app/api-client.service.ts`. The service owns the `'/api'` base path so routed
components can request scaffold endpoints without hard-coding backend origins or
duplicating URL prefix logic.
