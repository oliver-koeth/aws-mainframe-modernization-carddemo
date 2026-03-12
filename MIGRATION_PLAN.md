# GNUCobol To Angular + FastAPI Migration Plan

## Goal

Migrate the flat-file GNUCobol version of CardDemo into a runnable Angular frontend plus FastAPI backend with JSON persistence, schedulable batch jobs, monitoring, and automated tests.

This plan is intentionally organized into PRD-sized slices so the `prd` skill can turn each slice into a focused implementation brief for a Ralph execution loop.

## Scope

In scope:

- GNUCobol flat-file runtime under `app/cbl`, `app/cpy`, `app/data/ASCII`, `app/data/ASCII.seed`, and related local scripts.
- Base application online flows already ported away from required CICS dependencies.
- Base application batch programs and job-control behavior that operate on flat files.
- Angular UI, FastAPI REST APIs, JSON persistence, scheduler configuration, job monitoring, pytest, and Playwright.

Out of scope for this plan:

- Optional DB2, IMS, and MQ extensions under `app/app-transaction-type-db2`, `app/app-authorization-ims-db2-mq`, and `app/app-vsam-mq`.
- Legacy mainframe-only deployment artifacts except where they inform batch semantics or data layouts.

## Migration Source Of Truth

Use the current GNUCobol runtime as the executable business baseline, not the original CICS runtime:

- Online source programs:
  - `COSGN00C`, `COADM01C`, `GCUSRSEC`, `COUSR00C`-`COUSR03C`
  - `COMEN01C`
  - `COACTVWC`, `COACTUPC`
  - `COCRDLIC`, `COCRDSLC`, `COCRDUPC`
  - `COTRN00C`, `COTRN01C`, `COTRN02C`
  - `CORPT00C`
  - `COBIL00C`
- Batch source programs:
  - `CBTRN02C` transaction posting
  - `CBTRN03C` transaction report generation
  - `CBACT04C` interest calculation
  - `CBSTM03A`, `CBSTM03B` statement generation
  - `CBEXPORT`, `CBIMPORT` import/export
- Data source files:
  - `usrsec.dat`, `acctdata.txt`, `custdata.txt`, `carddata.txt`, `cardxref.txt`
  - `dailytran.txt`, `dailytran_pending.txt`, `dalyrejs.txt`
  - `trantype.txt`, `trancatg.txt`, `discgrp.txt`, `tcatbal.txt`
  - `dateparm.txt`, `tranrept_requests.txt`

## Target Architecture

- Frontend: Angular standalone app with reactive forms and a proxy-based `/api` integration strategy.
- Backend: FastAPI with Pydantic v2, shared domain services, and JSON responses only.
- Persistence: single versioned `backend/store.json` with atomic writes and serializer support for `Decimal` and ISO date/time values.
- Scheduling: externalized `backend/schedules.json` plus job run history stored in JSON persistence.
- Monitoring: job list, job detail, manual trigger, run history, run detail, schedule view/edit, overlap blocking, rerun/idempotency rules.
- Documentation: `docs/mapping.md`, `docs/record-layouts.md`, `docs/job-schedules.md`, and `docs/unsupported-features.md` only if needed.

## Delivery Rules

- Build the repository skeleton first.
- Migrate domain and storage contracts before feature UIs.
- Implement online flows before batch operations.
- Deliver batch jobs together with the batch admin UI, not as backend-only features.
- Each slice must end with runnable code, tests, and updated mapping docs.

## PRD Authoring Guidance

Use one PRD per slice below. Each PRD should contain:

- exact source programs and files
- target REST endpoints and Angular routes
- JSON store schema changes
- acceptance tests in pytest and Playwright
- cut lines for what is deferred to later slices

Do not combine slices unless the dependency notes below explicitly say they should land together.

## Phase 0: Scaffolding

### Slice 0.1: Repository Scaffold And Runtime Wiring

Purpose:

- Create the baseline `backend/`, `frontend/`, and `docs/` structure from the skill.
- Choose Angular proxy as the dev origin strategy and standardize frontend calls on `/api`.

Deliverables:

- FastAPI app bootstrap with `/health`
- Angular standalone shell with routes, layout, and API service foundation
- `store.json` and `schedules.json` bootstrapping
- local README files for backend and frontend
- CI/test commands for backend import, pytest, frontend build, and Playwright

Acceptance:

- backend imports cleanly
- frontend builds
- proxy-based `/api` calls parse JSON successfully

PRD boundary:

- No business migration yet beyond health checks and empty shells.

### Slice 0.2: Shared Storage, Locking, And Test Harness

Purpose:

- Implement the cross-cutting storage and testing primitives all later slices depend on.

Deliverables:

- atomic JSON persistence with temp-file rename
- serializer/deserializer for `Decimal`, `date`, and `datetime`
- optimistic write lock or process-safe file lock
- pytest fixtures for disposable stores
- Playwright smoke harness

Acceptance:

- persistence round-trip tests pass for money and timestamps
- frontend smoke test covers `/jobs`, `/accounts`, and `/transactions` JSON parsing

PRD boundary:

- Still no domain logic beyond persistence and test infrastructure.

## Phase 1: Domain Model And Data Contracts

### Slice 1.1: Record Layout Inventory And Canonical Schema

Purpose:

- Convert COBOL record layouts into canonical backend models and document them.

Source artifacts:

- `CVACT01Y`, `CVACT02Y`, `CVACT03Y`
- `CVCUS01Y`
- `CVTRA01Y`-`CVTRA07Y`
- `CSUSR01Y`
- flat files under `app/data/ASCII`

Deliverables:

- Pydantic models for users, customers, accounts, cards, transactions, transaction types, transaction categories, disclosure groups, category balances, report requests, and job runs
- `docs/record-layouts.md`
- schema versioning plan for `store.json`

Acceptance:

- parser tests verify exact fixed-width handling for representative sample lines
- malformed-width lines are rejected or quarantined deterministically

PRD boundary:

- This slice defines structure only; no user-facing flows.

### Slice 1.2: Seed Importer And Store Bootstrap

Purpose:

- Load the shipped ASCII seed files into the canonical JSON store.

Source artifacts:

- `app/data/ASCII.seed/*`
- `scripts/init_gnucobol_data.sh`
- `scripts/reset_gnucobol_data.sh`

Deliverables:

- one importer command/path that initializes `store.json` from seed files
- deterministic seed rules for unsupported or ignored values
- baseline counts for imported entities

Acceptance:

- import test proves row counts and key relationships are stable
- imported store supports backend startup without further manual setup

PRD boundary:

- This slice enables later APIs but does not expose business endpoints yet.

### Slice 1.3: Core Domain Services

Purpose:

- Build reusable services shared by online and batch flows.

Service areas:

- authentication and session lookup
- customer/account/card lookup via account ID or card number
- transaction creation and validation
- bill-payment posting semantics
- report request capture
- job/run telemetry writes

Acceptance:

- pytest covers money handling, key lookups, update behavior, and validation errors

PRD boundary:

- Keep services framework-agnostic so later APIs and jobs can reuse them directly.

## Phase 2: Online Function Migration

### Slice 2.1: Authentication And Navigation Shell

Source programs:

- `COSGN00C`
- `COADM01C`
- `COMEN01C`
- `GCUSRSEC` for authorization checks only

Deliverables:

- login API and session model
- Angular app shell with authenticated navigation
- role-aware menu for user vs admin

Target surface:

- `POST /session`
- `GET /session`
- Angular routes for sign-in and home

Acceptance:

- admin and regular user can sign in from seeded data
- unauthorized routes are blocked

PRD boundary:

- User maintenance CRUD is deferred to the next slice.

### Slice 2.2: User Security Administration

Source programs:

- `GCUSRSEC`
- `COUSR00C`
- `COUSR01C`
- `COUSR02C`
- `COUSR03C`

Deliverables:

- user list/create/update/delete APIs
- admin Angular screens for user maintenance
- validation and duplicate-user handling

Target surface:

- `GET /users`
- `POST /users`
- `PUT /users/{user_id}`
- `DELETE /users/{user_id}`
- Angular admin route for user security maintenance

Acceptance:

- CRUD flows work end-to-end from UI through persistence
- Playwright covers add, edit, and delete happy paths

### Slice 2.3: Account Domain Flows

Source programs:

- `COACTVWC`
- `COACTUPC`

Deliverables:

- account detail and update APIs
- related customer lookup on the same screen
- Angular account view/update routes

Target surface:

- `GET /accounts`
- `GET /accounts/{id}`
- `PUT /accounts/{id}`

Acceptance:

- account lookup works by account ID and related identifiers supported by the COBOL flow
- decimal balances preserve formatting and precision

### Slice 2.4: Card Domain Flows

Source programs:

- `COCRDLIC`
- `COCRDSLC`
- `COCRDUPC`

Deliverables:

- card list/detail/update APIs
- Angular list/detail/edit routes with filter and paging behavior matching the GNUCobol runtime intent

Target surface:

- `GET /cards`
- `GET /cards/{card_number}`
- `PUT /cards/{card_number}`

Acceptance:

- filtering by account/card works
- card status and expiry update rules match source behavior

### Slice 2.5: Transaction Inquiry And Entry

Source programs:

- `COTRN00C`
- `COTRN01C`
- `COTRN02C`

Deliverables:

- transaction list/detail/create APIs
- Angular transaction screens for inquiry and add
- pending transaction semantics separated from posted transaction history where required by the GNUCobol model

Target surface:

- `GET /transactions`
- `GET /transactions/{id}`
- `POST /transactions`

Acceptance:

- create transaction path writes the same business fields the COBOL runtime expects downstream
- list/detail screens reflect seeded and newly added transactions

### Slice 2.6: Bill Payment And Report Request

Source programs:

- `COBIL00C`
- `CORPT00C`

Deliverables:

- bill-payment action API
- transaction report request API
- Angular bill-payment and report-request routes

Target surface:

- `POST /accounts/{id}/payments`
- `POST /reports/transactions`
- optional `GET /reports/requests`

Acceptance:

- bill payment updates balances and creates the expected transaction artifacts
- report request persists the equivalent of `dateparm.txt` and `tranrept_requests.txt` contracts in JSON form

PRD boundary:

- Actual batch execution of reports is deferred to Phase 3.

## Phase 3: Batch Jobs And Batch Admin UI

### Slice 3.1: Job Framework, Schedules, And Monitoring Surface

Purpose:

- Create the shared batch runtime before implementing individual jobs.

Deliverables:

- job registry
- run state machine `queued -> running -> succeeded/failed/skipped`
- overlap blocking per `job_id`
- run history persistence
- Angular batch admin UI skeleton with job list, job detail, trigger button, run history, and run detail

Target surface:

- `GET /jobs`
- `GET /jobs/{job_id}`
- `POST /jobs/{job_id}/run`
- `GET /jobs/{job_id}/runs`
- `GET /jobs/runs/{run_id}`

Acceptance:

- manual double-trigger behavior is explicit and tested
- jobs page loads and renders empty/history states in Playwright

### Slice 3.2: Transaction Posting Job

Source programs:

- `CBTRN02C`
- online dependency from `COTRN02C` and `COBIL00C`

Default schedule:

- daily end-of-day candidate, configurable in `schedules.json`

Deliverables:

- job handler for posting pending transactions
- counters for read/posted/rejected/updated
- watermark or equivalent idempotency rule
- batch admin UI detail for posting job telemetry

Job ID:

- `post-transactions`

Acceptance:

- rerunning the same posting window does not duplicate effects
- rejects are persisted with diagnostic detail

### Slice 3.3: Transaction Report Job

Source programs:

- `CBTRN03C`
- request contract from `CORPT00C`

Default schedule:

- manual/on-demand by default, optionally schedulable

Deliverables:

- report generation job handler
- persisted report artifact metadata and downloadable output
- job monitoring and run detail support for produced reports

Job ID:

- `transaction-report`

Acceptance:

- requested date ranges generate the expected report summary
- run history retains timestamps and artifact references

### Slice 3.4: Interest Calculation And Statement Jobs

Source programs:

- `CBACT04C`
- `CBSTM03A`
- `CBSTM03B`

Default schedules:

- interest calculation: cycle-end or month-end candidate, default to `00:01` on day `1` when no stronger evidence is encoded
- statement generation: month-end candidate, default to `00:01` on day `1`

Deliverables:

- interest calculation handler
- statement generation handler and statement artifact metadata
- schedule inference docs in `docs/job-schedules.md`

Job IDs:

- `apply-interest`
- `generate-statements`

Acceptance:

- schedule inference tests cover month-end defaults
- job outputs include records scanned, updated, and generated artifacts

### Slice 3.5: Import And Export Jobs

Source programs:

- `CBEXPORT`
- `CBIMPORT`

Default schedule:

- manual/admin-triggered by default

Deliverables:

- import/export job handlers
- upload/download support as needed for job inputs and artifacts
- batch admin UI actions for manual execution

Job IDs:

- `branch-export`
- `branch-import`

Acceptance:

- import/export statistics are persisted in run history
- malformed input handling is visible in job detail

## Phase 4: Hardening, Traceability, And Handoff

### Slice 4.1: Mapping Documentation And Behavioral Reconciliation

Purpose:

- Finish the traceability artifacts Ralph and reviewers need.

Deliverables:

- `docs/mapping.md` mapping COBOL program/paragraph to API, Angular route, or batch job
- documented deviations where the web UX intentionally modernizes menu wording or flow shape

Acceptance:

- every in-scope source program is mapped to a target surface or explicitly deferred

### Slice 4.2: End-To-End Validation And Release Readiness

Purpose:

- Run the mandatory cross-stack gates before handoff.

Acceptance:

- backend import plus pytest pass
- frontend build plus UI tests pass
- Playwright covers at least login, account flow, transaction flow, jobs page load, and manual job trigger
- unsupported flat-file/COBOL features, if discovered during implementation, are written to `docs/unsupported-features.md`

## Recommended PRD Order

Create PRDs in this order:

1. Slice 0.1
2. Slice 0.2
3. Slice 1.1
4. Slice 1.2
5. Slice 1.3
6. Slice 2.1
7. Slice 2.2
8. Slice 2.3
9. Slice 2.4
10. Slice 2.5
11. Slice 2.6
12. Slice 3.1
13. Slice 3.2
14. Slice 3.3
15. Slice 3.4
16. Slice 3.5
17. Slice 4.1
18. Slice 4.2

## Phase Exit Criteria

Phase 0 exits when the scaffold, proxy strategy, persistence primitives, and test harness are in place.

Phase 1 exits when the JSON schema and seed import are stable enough that later feature slices do not need to reinterpret COBOL field layouts.

Phase 2 exits when all base online GNUCobol user and admin flows have equivalent Angular + FastAPI behavior.

Phase 3 exits when all in-scope batch jobs are runnable through API and batch admin UI, with persisted schedules and monitoring.

Phase 4 exits when traceability docs and mandatory validation gates are complete.
