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

Bootstrap the canonical JSON store from the shipped GNUCobol seed files with:

```bash
.venv/bin/python -m app.seed_import
```

The acceptance baseline for this scaffold is that `python -m mypy app` and `python -m pytest` both pass from `output/backend/`.

## Storage Conventions

Application data lives in `store.json`. Future interactive API handlers and batch jobs should treat that file as the single shared JSON store for scaffold and migrated business data.

`store.json` now uses a canonical schema envelope with explicit metadata and predeclared collections:

```json
{
  "metadata": {
    "schema_name": "carddemo.store",
    "schema_version": 1
  },
  "users": [],
  "customers": [],
  "accounts": [],
  "cards": [],
  "card_account_xref": [],
  "transaction_types": [],
  "transaction_categories": [],
  "disclosure_groups": [],
  "category_balances": [],
  "transactions": [],
  "report_requests": [],
  "operations": {
    "sessions": [],
    "job_runs": [],
    "job_run_details": []
  }
}
```

Later migration stories should add domain records inside these collections rather than changing the top-level shape ad hoc. Session state is reserved under `operations.sessions`; batch telemetry is reserved under `operations.job_runs` and `operations.job_run_details`.

When `store.json` is missing or empty, `app.storage.read_store` returns the default schema envelope. When the file declares an unsupported schema version or schema name, `read_store` raises `StoreSchemaError` so later import or migration commands fail deterministically instead of guessing how to coerce the payload.

Schedule declarations live in `schedules.json`. Future scheduler and batch stories should use that file for persisted schedule configuration rather than introducing a second schedule store.

Shared JSON writes go through `app.storage`, which serializes updates with a same-directory `.lock` file per target JSON document before performing a temp-file-plus-rename replacement. Future API and batch code should keep using `write_store`, `write_schedules`, or `write_json_file` directly instead of implementing ad hoc write locks at call sites.

## Seed Import Error Handling

Phase 1 uses a strict malformed-line strategy for bootstrap work. Import code should route source rows through `app.importing.parse_lines_strict`, which calls the record-family parser for each line and hard-fails on the first malformed row.

The raised `SeedImportError` includes a structured `detail` payload with:

- `source_name`
- `line_number`
- `raw_line`
- `reason`

This is the canonical place to record malformed-line diagnostics for bootstrap and seed-import commands. Parsers continue to own field-level validation messages; import code wraps those parser errors with source-file context instead of quarantining or coercing bad rows.

## Seed Bootstrap Workflow

The canonical Phase 1 bootstrap command is `.venv/bin/python -m app.seed_import` from `output/backend/`. By default it:

- reads the shipped fixed-width seed sources from `app/data/ASCII.seed`
- parses them through the shared record-family parsers plus `app.importing.parse_lines_strict`
- rewrites `output/backend/store.json` through `app.storage.write_store`

Expected successful output is a one-line summary naming the target `store.json` path plus imported collection counts. `report_requests` and the `operations.*` collections remain present but empty until later stories import runtime-managed files and job telemetry.

Use `--seed-dir`, `--store-path`, or `--schedules-path` only when testing against alternate fixtures or an isolated workspace.

## Frontend Integration

During frontend development, the Angular dev server proxies browser requests from `/api/*` to this backend process and strips the `/api` prefix before forwarding. Later frontend slices should keep using `/api` as the only browser-facing base path.
