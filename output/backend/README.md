# Backend Scaffold

Phase 0 provides scaffolding for the backend workspace under `output/backend/`.

The canonical FastAPI package lives in `app/`, with placeholder modules for APIs, services, jobs, scheduler wiring, and JSON storage primitives. This story establishes the importable package and Python tooling only; business-domain behavior is added in later stories.

## Local Development

Run the scaffold backend from this directory with:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

During frontend development, the Angular dev server proxies browser requests from
`/api/*` to this backend process and strips the `/api` prefix before forwarding.
Later frontend slices should keep using `/api` as the only browser-facing base path.
