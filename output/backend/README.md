# Backend Scaffold

Phase 0 provides scaffolding for the backend workspace under `output/backend/`.

The canonical FastAPI package lives in `app/`, with placeholder modules for APIs, services, jobs, scheduler wiring, and JSON storage primitives. This workspace targets Python 3.12 and is meant to stay scaffold-only until later migration stories add business behavior.

The scaffold backend currently exposes `GET /health`, plus temporary `GET /jobs`, `GET /accounts`, and `GET /transactions` placeholder collection endpoints. Those collection routes are Phase 0 scaffold contracts only and intentionally return empty JSON arrays until business migration stories replace them.

## Setup

Create or refresh the local virtual environment from this directory:

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

The editable install defined in `pyproject.toml` provides FastAPI, Uvicorn, pytest, and mypy for the scaffold workflow.

## Commands

Start the backend locally with:

```bash
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Run the backend typecheck with:

```bash
.venv/bin/python -m mypy app
```

Run the backend tests with:

```bash
.venv/bin/python -m pytest
```

The acceptance baseline for this scaffold is that `python -m mypy app` and `python -m pytest` both pass from `output/backend/`.

## Storage Conventions

Application data lives in `store.json`. Future interactive API handlers and batch jobs should treat that file as the single shared JSON store for scaffold and migrated business data.

Schedule declarations live in `schedules.json`. Future scheduler and batch stories should use that file for persisted schedule configuration rather than introducing a second schedule store.

Shared JSON writes go through `app.storage`, which serializes updates with a same-directory `.lock` file per target JSON document before performing a temp-file-plus-rename replacement. Future API and batch code should keep using `write_store`, `write_schedules`, or `write_json_file` directly instead of implementing ad hoc write locks at call sites.

## Frontend Integration

During frontend development, the Angular dev server proxies browser requests from `/api/*` to this backend process and strips the `/api` prefix before forwarding. Later frontend slices should keep using `/api` as the only browser-facing base path.
