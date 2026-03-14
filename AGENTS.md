# AGENTS.md

## Purpose

This repository contains the CardDemo mainframe sample application plus an in-progress modernization plan for a new Angular + FastAPI target.

Use this file as the working agreement for coding agents operating in this repo.

## Project Context

- Legacy application: credit-card management system implemented primarily in COBOL, CICS, VSAM, JCL, RACF, and assembler.
- Current executable modernization source of truth: the flat-file GNUCobol runtime under `app/cbl`, `app/cpy`, and `app/data/ASCII`.
- Current target modernization architecture: Angular frontend + FastAPI backend + JSON persistence + schedulable/monitorable batch jobs.
- Modernization planning artifacts:
  - [MIGRATION_PLAN.md](/Users/Oliver.Koeth/work/aws-mainframe-modernization-carddemo/MIGRATION_PLAN.md)
  - [tasks/prd-phase-0-scaffolding.md](/Users/Oliver.Koeth/work/aws-mainframe-modernization-carddemo/tasks/prd-phase-0-scaffolding.md)
  - [scripts/ralph/prd.json](/Users/Oliver.Koeth/work/aws-mainframe-modernization-carddemo/scripts/ralph/prd.json)

## Source Of Truth Rules

- For business behavior, treat the GNUCobol flat-file runtime as authoritative before the original CICS runtime.
- For modernization sequencing, follow [MIGRATION_PLAN.md](/Users/Oliver.Koeth/work/aws-mainframe-modernization-carddemo/MIGRATION_PLAN.md).
- For Ralph execution, follow [scripts/ralph/prd.json](/Users/Oliver.Koeth/work/aws-mainframe-modernization-carddemo/scripts/ralph/prd.json).
- Do not invent business rules when COBOL or seeded flat files already define them.

## In-Scope Modernization Surface

Primary scope:

- `app/cbl`
- `app/cpy`
- `app/bms` only as a legacy reference
- `app/data/ASCII`
- `app/data/ASCII.seed`
- `scripts/` relevant to GNUCobol runtime and batch behavior

Out of scope unless explicitly requested:

- `app/app-transaction-type-db2`
- `app/app-authorization-ims-db2-mq`
- `app/app-vsam-mq`
- legacy mainframe deployment mechanics not needed for the flat-file modernization target

## Output Location Rule

All generated Angular/FastAPI modernization artifacts belong under `output/`.

Use:

- `output/backend/`
- `output/frontend/`
- `output/docs/`

Do not mix placeholder modernization files into legacy source directories unless the task explicitly requires modifying legacy assets.

## Phase 0 Defaults

Unless the user says otherwise, use these defaults for the scaffold:

- Python `3.12`
- Node.js `20 LTS`
- frontend package manager: `npm`
- backend typecheck: `python -m mypy app`
- backend tests: `python -m pytest`
- backend import smoke: `python -c "import app.main"`
- frontend build: `npm run build`
- frontend browser smoke/E2E: Playwright
- frontend/backend dev integration: Angular proxy using `/api`

Phase 0 placeholder endpoint behavior:

- `GET /jobs` returns `[]`
- `GET /accounts` returns `[]`
- `GET /transactions` returns `[]`

## Working Style For Agents

- Make the smallest coherent change that advances the current slice.
- Prefer finishing one PRD story cleanly over partially implementing several.
- Keep backend and frontend contracts explicit and JSON-only.
- Preserve the existing repo unless the current task explicitly asks for structural cleanup.
- When touching legacy COBOL or seed data, explain the behavior link to the modernization target.

## Ralph Workflow

When working from Ralph artifacts:

1. Read `scripts/ralph/prd.json`.
2. Execute stories in priority order.
3. Keep each change scoped to the current story unless an earlier blocking fix is required.
4. Update `scripts/ralph/progress.txt` with learnings and changed files after each completed story.
5. If the active `prd.json` is being replaced by a different feature, archive the previous `prd.json` and `progress.txt` under `scripts/ralph/archive/YYYY-MM-DD-feature-name/`.

## PRD Workflow

When asked to create or update a PRD:

- Save markdown PRDs under `tasks/`.
- Keep PRDs implementation-ready and explicit for junior developers or autonomous agents.
- If the PRD will be executed by Ralph, convert it into `scripts/ralph/prd.json`.
- Split stories so each one is completable in a single Ralph iteration.

## Testing Expectations

For modernization work, favor these validation layers:

- Backend:
  - import smoke
  - `mypy`
  - `pytest`
- Frontend:
  - build
  - Playwright smoke tests
  - browser verification for UI stories

If a story changes UI, include browser verification.

If a story changes API or persistence behavior, include automated tests.

## Data And Persistence Rules

- Preserve COBOL record semantics even when migrating storage to JSON.
- Preserve leading-zero numeric identifiers from copybooks, such as customer IDs and SSNs, as strings in JSON models unless the runtime semantics require arithmetic.
- Money should remain precise end-to-end; avoid float-based persistence logic.
- JSON persistence must support `Decimal`, `date`, and `datetime`.
- Treat flat files written with GNUCobol `LINE SEQUENTIAL` semantics as logically copybook-width records even when trailing spaces are omitted on disk; right-pad to the authoritative copybook width before slicing fields, then fail deterministically only when required fields are truncated, blank, or invalid.
- Treat display-form `PIC S9(...)V99` values from flat files as COBOL signed zoned-decimal text; decode the trailing overpunch character into sign plus final digit before normalizing money fields to `Decimal`.
- For copybook-backed backend parsers under `output/backend/app/domain`, use the shared helpers in `output/backend/app/fixed_width.py` for width checks, field slicing, text normalization, and signed-amount decoding so malformed-line behavior stays consistent across record families.
- For lookup services over `card_account_xref`, preserve store order: account-driven and card-driven inquiries should stop on the first matching xref to mirror the GNUCobol sequential scans, while customer-driven retrieval can return all related xrefs/accounts/cards in that same persisted order.
- Treat transaction reference relationships as composite keys: `CVTRA04Y` categories join to `CVTRA03Y` types by `transaction_type_code`, while `CVTRA01Y` balances and `CVTRA02Y` disclosure groups both use the `transaction_type_code` + `transaction_category_code` pair and then join to accounts by `account_id` or `group_id` respectively.
- Treat `app/data/ASCII/tranrept_requests.txt` as a pipe-delimited runtime file written by `CORPT00C`, not a fixed-width copybook record; each line is `request_timestamp|user_id|report_name|start_date|end_date`, and the emitted report names are limited to `Monthly`, `Yearly`, and `Custom`.
- Preserve `CORPT00C` report-request append semantics in modernization services: confirmed requests append to `report_requests[]` in store order without duplicate suppression, while `Monthly` and `Yearly` windows are derived from the current date and only `Custom` accepts explicit start/end inputs.
- Keep job telemetry under `store.json` `operations.job_runs` and `operations.job_run_details`; Phase 1 headers are intentionally minimal (`job_run_id`, `job_name`, `status`, `started_at`, `ended_at`, optional `summary`) and status transitions should stay constrained to `pending -> running -> succeeded` with `failed` allowed from `pending` or `running`.
- Treat `output/backend/app/models.py` `default_store_document()` plus `output/backend/app/storage.py` `read_store`/`write_store` validation as the authoritative top-level `store.json` contract; extend record collections inside that envelope instead of changing root keys ad hoc.
- When adding or renaming `store.json` collections, update `output/backend/app/models.py` `STORE_COLLECTION_NAMES` / `STORE_OPERATION_COLLECTION_NAMES` together with `default_store_document()` so seed bootstrap, storage validation, and contract tests stay aligned.
- For storage-backed domain services under `output/backend/app/domain`, load raw `store.json` collections through `app.storage.read_store()` and validate each persisted row into the canonical Pydantic model at the service boundary before applying business rules; this keeps malformed store data as deterministic consistency errors instead of leaking untyped dict handling across services.
- For storage-backed transaction creation under `output/backend/app/domain/transactions.py`, mirror `COTRN02C` next-ID semantics by scanning persisted `transactions[]` in store order, remembering the last numeric `transaction_id`, and incrementing that value rather than computing a collection-wide max.
- Keep bill-payment semantics split the same way as the GNUCobol runtime: `COBIL00C` online payment writes a fixed payment transaction and zeroes only `accounts[].current_balance`, while `CBTRN02C` posting updates `category_balances[]` plus the account cycle buckets.
- For Phase 1 seed bootstrap work, use `output/backend/app/importing.py` `parse_lines_strict()` as the shared malformed-line strategy so import commands hard-fail with structured `SeedImportError.detail` diagnostics instead of inventing per-file quarantine formats.
- Keep the canonical seed bootstrap entry point in `output/backend/app/seed_import.py`; extend its `SEED_SOURCES` mapping and shared storage write path instead of adding parallel one-off import scripts when new Phase 1 record families are imported.
- When bootstrap stories import related record families, add cross-file referential checks in `output/backend/app/seed_import.py` before `write_store()` so individually valid rows do not persist broken joins to `store.json`.
- When shipped seed fixtures change, keep the documented Phase 1 baseline counts in `output/backend/README.md` synchronized with the centralized regression expectations in `output/backend/tests/test_seed_import.py` so bootstrap drift is explicit in both docs and CI.
- Writes should be atomic.
- Concurrency protection belongs in shared storage code, not duplicated per endpoint.

## Batch Modernization Rules

- Keep batch schedules externalized.
- Persist job run history durably.
- Prevent overlapping runs for the same job.
- Expose monitoring surfaces for jobs, runs, and run details.
- Deliver batch jobs together with their admin/monitoring surface when working on later phases.

## Documentation Rules

- Update docs when behavior, commands, or scope assumptions change.
- Keep Phase 0 docs honest: scaffolding only, not feature-complete migration.
- Prefer concise operational documentation over long narrative descriptions.
- Keep `output/docs/record-layouts.md` as the consolidated Phase 1 record-to-model index; retain narrower `output/docs/*-records.md` documents for field-level details rather than duplicating those tables everywhere.
- Keep `output/docs/phase-1-service-contracts.md` as the consolidated Phase 1 service-boundary and deferred-behavior index; update it when shared domain contracts change so later API/UI stories have one current reference.

## When To Pause And Ask

Pause and confirm with the user before:

- broadening scope beyond the active PRD story or migration slice
- modifying optional DB2/IMS/MQ modules
- replacing legacy sources rather than adding modernization output under `output/`
- making destructive changes to generated or archived Ralph artifacts

## Good First References

Start here when you need context:

- [README.md](/Users/Oliver.Koeth/work/aws-mainframe-modernization-carddemo/README.md)
- [GNUCOBOL_RUNTIME.md](/Users/Oliver.Koeth/work/aws-mainframe-modernization-carddemo/GNUCOBOL_RUNTIME.md)
- [MIGRATION_PLAN.md](/Users/Oliver.Koeth/work/aws-mainframe-modernization-carddemo/MIGRATION_PLAN.md)
- [tasks/prd-phase-0-scaffolding.md](/Users/Oliver.Koeth/work/aws-mainframe-modernization-carddemo/tasks/prd-phase-0-scaffolding.md)
- [scripts/ralph/prd.json](/Users/Oliver.Koeth/work/aws-mainframe-modernization-carddemo/scripts/ralph/prd.json)
