# Phase 1 Service Contracts

This document is the concise implementation-oriented index for the framework-agnostic business services already available under `output/backend/app/domain`.

Use it when later slices need to know which Phase 1 behavior is already implemented in Python, which surfaces are still deferred, and where the modernization work had to infer behavior because the GNUCobol flat-file runtime does not fully define it.

## Implemented Services

| Service | Module | Public contract | Authoritative source |
| --- | --- | --- | --- |
| Authentication and session lookup | `app.domain.auth.AuthenticationService` | `authenticate()`, `lookup_session()` | `COSGN00C.cbl`, `GCUSRSEC.cbl`, `CSUSR01Y` |
| Account, card, and customer lookups | `app.domain.lookups.LookupService` | `lookup_account()`, `lookup_card()`, `lookup_customer()` | `COACTVWC.cbl`, `COACTUPC.cbl`, `COCRDSLC.cbl`, seeded account/card files |
| Transaction add | `app.domain.transactions.TransactionService` | `validate_transaction()`, `create_transaction()` | `COTRN02C.cbl`, transaction reference files |
| Posting and online bill payment | `app.domain.posting.PostingService` | `create_online_bill_payment()`, `post_transaction()` | `COBIL00C.cbl`, `CBTRN02C.cbl` |
| Report requests | `app.domain.report_requests.ReportRequestService` | `create_report_request()`, `list_report_requests()` | `CORPT00C.cbl`, `tranrept_requests.txt` |
| Job telemetry | `app.domain.job_telemetry.JobTelemetryService` | `create_job_run()`, `start_job_run()`, `complete_job_run()`, `fail_job_run()`, `append_job_run_detail()` | Phase 1 JSON contract under `store.json` |

All services are storage-backed and framework-agnostic. They read persisted collections through `app.storage.read_store()`, validate rows into canonical Pydantic models at the service boundary, and persist mutations through `app.storage.write_store()`.

## Contract Summary

### AuthenticationService

- `authenticate()` upper-cases `user_id` and `password`, matches credentials against `users[]`, resolves the canonical user role, and can enforce a required role.
- `lookup_session()` resolves one persisted `operations.sessions[]` row back to its canonical user.
- Invalid credentials do not reveal whether the user ID or password was wrong.

Deferred:

- No REST sign-in endpoint exists yet.
- No durable session-creation workflow exists yet; Phase 1 only supports session lookup for rows already present in `store.json`.

Known inference or gap:

- The flat-file runtime does not expose disabled or locked user state, so Phase 1 cannot model those cases yet.

### LookupService

- `lookup_account()` and `lookup_card()` preserve GNUCobol sequential-scan semantics by stopping on the first matching `card_account_xref[]` row.
- `lookup_customer()` returns all related xref/account/card rows in persisted order.
- Missing inputs, inactive primary account/card records, ambiguous primary keys, and broken joins surface as explicit domain errors.

Deferred:

- No inquiry REST endpoints or UI screens call these services yet.

Known inference or gap:

- Customer-wide retrieval is a modernization helper rather than a one-screen COBOL transaction, so returning all related rows is an explicit Phase 1 design choice.

### TransactionService

- `validate_transaction()` normalizes and validates add-transaction input without mutating storage.
- `create_transaction()` appends a canonical transaction row and assigns the next transaction ID by scanning persisted rows in store order.
- Validation requires valid account/card resolution, known type/category codes, an existing category-balance bucket, signed money text with two decimals, nonblank merchant fields, and valid dates.

Deferred:

- No transaction-entry API or UI exists yet.
- Posting and balance mutation remain separate and are not performed by `create_transaction()`.

Known inference or gap:

- Phase 1 normalizes dates with strict calendar validation in Python. That is intentionally stricter than some COBOL string handling because the flat-file evidence does not define a separate invalid-date persistence path.

### PostingService

- `create_online_bill_payment()` preserves the `COBIL00C` behavior: append the fixed payment transaction and zero only `accounts[].current_balance`.
- `post_transaction()` preserves the `CBTRN02C` path: append the transaction, update the first matching `category_balances[]` row or create one, and update the account balance plus current-cycle buckets.

Deferred:

- No batch runner or online-payment endpoint exists yet.
- No overlap prevention or scheduler-triggered posting flow exists yet.

Known inference or gap:

- The Python service reuses canonical transaction models and store validation rather than reproducing every intermediate COBOL working-storage field.

### ReportRequestService

- `create_report_request()` validates the requesting user, normalizes the report type, derives or validates the date range, stamps `requested_at`, and appends the request in store order.
- `list_report_requests()` returns persisted rows in append order and supports optional filtering by requesting user and report type.

Deferred:

- No report-generation API or rendered report output exists yet.
- `CVTRA07Y` remains a deferred output-layout contract rather than an implemented generated file or endpoint.

Known inference or gap:

- `Monthly` and `Yearly` windows are derived from the current date because `CORPT00C` writes requests, not a separate durable parameter record describing an alternate derivation rule.

### JobTelemetryService

- `create_job_run()` appends a `pending` header row under `operations.job_runs[]`.
- `start_job_run()`, `complete_job_run()`, and `fail_job_run()` enforce the minimal Phase 1 lifecycle `pending -> running -> succeeded`, with `failed` allowed from `pending` or `running`.
- `append_job_run_detail()` appends per-run detail rows with the next `sequence_number` chosen by persisted order for that `job_run_id`.

Deferred:

- No scheduler, admin monitoring API, or UI surface exists yet.
- No job catalog or schedule execution integration exists yet.

Known inference or gap:

- Job telemetry has no legacy flat-file source; it is a deliberate Phase 1 JSON contract reserved so later batch stories can persist run history without reshaping `store.json`.

## Deferred Surfaces

Phase 1 intentionally stops at domain logic, parsing, seed import, and storage contracts. These surfaces remain deferred to Phase 2 or later:

- REST endpoints for authentication, lookups, transactions, posting, reports, jobs, and monitoring
- Angular UI flows for sign-on, inquiry, transaction entry, bill payment, reporting, and job administration
- Durable session issuance and expiration behavior
- Scheduler execution, job registration, schedule editing, overlap prevention enforcement, and job monitoring screens
- Report rendering/output based on the deferred `CVTRA07Y` contract

The placeholder FastAPI collection routes in `output/backend/app/main.py` remain scaffold-only and are not the public contract for the services listed above.

## Implementation Notes

- The canonical store envelope is defined in `output/backend/app/models.py` and documented in `output/docs/store-schema.md`.
- Fixed-width record parsing rules are documented in `output/docs/record-layouts.md` and implemented through `output/backend/app/fixed_width.py`.
- Seed bootstrap remains the only canonical loader for repository data: use `output/backend/app/seed_import.py` instead of ad hoc import scripts.
- Service-level tests under `output/backend/tests/` are the regression contract for these behaviors until API-level tests exist.
