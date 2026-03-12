# Backend Scaffold

Phase 0 provides scaffolding for the backend workspace under `output/backend/`.

The canonical FastAPI package lives in `app/`, with placeholder modules for APIs, services, jobs, scheduler wiring, and JSON storage primitives. This story establishes the importable package and Python tooling only; business-domain behavior is added in later stories.

The scaffold backend currently exposes `GET /health`, plus temporary `GET /jobs`, `GET /accounts`, and `GET /transactions` placeholder collection endpoints. Those collection routes are Phase 0 scaffold contracts only and intentionally return empty JSON arrays until business migration stories replace them.

Shared JSON writes go through `app.storage`, which serializes updates with a same-directory `.lock` file per target JSON document before performing the existing temp-file-plus-rename replacement. Future API and batch code should keep using `write_store`, `write_schedules`, or `write_json_file` directly instead of implementing ad hoc write locks at call sites.

## Local Development

Run the scaffold backend from this directory with:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

During frontend development, the Angular dev server proxies browser requests from
`/api/*` to this backend process and strips the `/api` prefix before forwarding.
Later frontend slices should keep using `/api` as the only browser-facing base path.
