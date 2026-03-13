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

## Authentication And Session Lookup

Phase 1 now includes a framework-agnostic authentication service under `app.domain.auth`, built from the authoritative GNUCobol sign-on program `app/cbl/COSGN00C.cbl` plus the user-maintenance persistence rules in `app/cbl/GCUSRSEC.cbl`.

The shared `AuthenticationService.authenticate()` contract follows the COBOL behavior directly:

- upper-case the provided `user_id` and `password` before comparison
- compare against imported `users[]` records without exposing whether the user ID or password was wrong
- resolve the authenticated role from `CSUSR01Y` `user_type_code` (`A` -> `admin`, `U` -> `user`)
- optionally enforce a required role and fail with an authorization error when credentials are valid but the resolved user type is not allowed

`GCUSRSEC` upper-cases user IDs, passwords, and user-type input before persisting records, so the Phase 1 service assumes imported `users[]` data already reflects those write-time semantics. First and last names remain stored as entered.

The authoritative flat-file user record does not contain a disabled or locked status. Because neither `CSUSR01Y`, `COSGN00C`, nor `GCUSRSEC` exposes that state, Phase 1 authentication supports only:

- successful sign-on
- invalid credentials
- authorization failures based on the resolved `A`/`U` user type

Phase 1 also defines `AuthenticationService.lookup_session()` over `operations.sessions`, but this is intentionally a lookup-only contract. The GNUCobol runtime carries interactive state in COMMAREA fields rather than a durable session file, so current modernization code resolves previously persisted session rows without inventing a COBOL-backed session-creation workflow yet. The minimal persisted session contract is:

```json
{
  "session_id": "string",
  "user_id": "string",
  "created_at": "optional ISO-8601 datetime"
}
```

Session lookup joins that record back to the canonical `users[]` collection and raises a deterministic consistency error if a stored session references a missing user.

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
- reads the runtime-managed `tranrept_requests.txt` log from `app/data/ASCII`
- parses them through the shared record-family parsers plus `app.importing.parse_lines_strict`
- treats a missing or empty `tranrept_requests.txt` file as an empty `report_requests[]` collection
- validates the imported customer/account/card/card-xref collections plus transaction reference and report-request joins before writing anything
- rewrites `output/backend/store.json` through `app.storage.write_store`

Expected successful output is a one-line summary naming the target `store.json` path plus imported collection counts. The `operations.*` collections remain present but empty because Phase 1 only defines their schema.

The shipped Phase 1 bootstrap baseline currently expects these collection counts after a successful import:

- `users=2`
- `customers=50`
- `accounts=50`
- `cards=50`
- `card_account_xref=50`
- `transaction_types=7`
- `transaction_categories=18`
- `disclosure_groups=51`
- `category_balances=50`
- `transactions=300`
- `report_requests=1`
- `operations.sessions=0`
- `operations.job_runs=0`
- `operations.job_run_details=0`

`output/backend/tests/test_seed_import.py` treats that one-line count summary as a regression snapshot. If shipped seed files change intentionally, update both the fixture data and the documented baseline together so CI makes the drift explicit.

An imported `store.json` is considered complete when it can be loaded immediately through `app.storage.read_store` with no manual edits and still contains:

- the canonical `metadata` schema header
- every declared Phase 1 top-level collection, even when a collection has zero shipped rows
- the reserved empty operational collections under `operations.sessions`, `operations.job_runs`, and `operations.job_run_details`

Use `--seed-dir`, `--runtime-data-dir`, `--store-path`, or `--schedules-path` only when testing against alternate fixtures or an isolated workspace.

For the shipped identity/account bootstrap data, the importer currently requires these integrity rules:

- every `cards[].account_id` must exist in `accounts[]`
- every `card_account_xref[].customer_id` must exist in `customers[]`
- every `card_account_xref[].account_id` must exist in `accounts[]`
- every `card_account_xref[].card_number` must exist in `cards[]`
- every `card_account_xref` row must agree with the matching `cards[].account_id`

If any of those joins drift, `app.seed_import` fails with `SeedReferentialIntegrityError` and does not rewrite `store.json`.

For the shipped transaction reference and reporting data, the importer also requires these integrity rules:

- every `transaction_categories[].transaction_type_code` must exist in `transaction_types[]`
- every `disclosure_groups[]`, `category_balances[]`, and `transactions[]` composite `(transaction_type_code, transaction_category_code)` pair must exist in `transaction_categories[]`
- every `category_balances[].account_id` must exist in `accounts[]`
- every `transactions[].card_number` must exist in `cards[]`
- every `report_requests[].requested_by_user_id` must exist in `users[]`

Phase 1 preserves imported values that are not yet used by APIs or UI, such as disclosure-group interest rates and transaction filler text, by carrying them into the canonical JSON models unchanged instead of dropping fields during bootstrap.

## Frontend Integration

During frontend development, the Angular dev server proxies browser requests from `/api/*` to this backend process and strips the `/api` prefix before forwarding. Later frontend slices should keep using `/api` as the only browser-facing base path.
