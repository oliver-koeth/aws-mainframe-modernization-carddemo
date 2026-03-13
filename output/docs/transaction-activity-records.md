# Transaction Activity Records

This document defines the canonical Phase 1 transaction-event, report-request, and job-telemetry contracts derived from `CVTRA05Y` through `CVTRA07Y` plus the runtime-managed `app/data/ASCII/tranrept_requests.txt` file.

## Authoritative Sources

- `app/cpy/CVTRA05Y.cpy`: posted transaction event layout, logical record width `350`
- `app/cpy/CVTRA06Y.cpy`: daily transaction runtime layout, logical record width `350`
- `app/cpy/CVTRA07Y.cpy`: printable transaction report detail projection, logical detail width `115`
- `app/data/ASCII.seed/dailytran.txt`: shipped bootstrap transaction events
- `app/data/ASCII/dailytran.txt`: runtime-managed transaction events
- `app/data/ASCII/tranrept_requests.txt`: runtime-managed report-request log written by `app/cbl/CORPT00C.cbl`

The GNUCobol flat-file runtime is authoritative for these records. `CVTRA05Y` and `CVTRA06Y` share the same 350-byte field layout; in the current flat-file runtime, `dailytran.txt` is the operational source that Phase 1 should parse and later import.

## Canonical Models

- `TransactionRecord` maps the `CVTRA05Y`/`CVTRA06Y` event row into JSON fields for transaction ID, type/category codes, source, description, amount, merchant attributes, card number, origin timestamp, optional processing timestamp, and optional filler.
- `TransactionReportDetailRecord` captures the printable detail projection from `CVTRA07Y` for later report-generation work. Phase 1 defines the shape now but does not parse report-output flat files because the current runtime persists requests and transactions, not rendered report lines.
- `ReportRequestRecord` maps one pipe-delimited `tranrept_requests.txt` line into `requested_at`, `requested_by_user_id`, `report_type`, `start_date`, and `end_date`.
- `JobRunRecord` and `JobRunDetailRecord` are the canonical JSON documents reserved for `store.json` `operations.job_runs` and `operations.job_run_details`.

## Parsing Rules

- Right-pad `CVTRA05Y` and `CVTRA06Y` lines to `350` characters before slicing because GNUCobol `LINE SEQUENTIAL` writes omit trailing spaces on disk.
- Treat `TRAN-AMT` as COBOL signed zoned-decimal text with two fractional digits. The trailing overpunch character determines both sign and final digit.
- Require nonblank text fields after trimming trailing spaces. Optional trailing filler normalizes to `null`.
- Preserve `transaction_type_code` exactly as the two-character source code. Preserve `transaction_category_code` as a four-digit string for joins to `CVTRA04Y`.
- Require digit-only values for `transaction_category_code`, `merchant_id`, and `card_number`.
- Parse `TRAN-ORIG-TS` and `TRAN-PROC-TS` with Python/Pydantic ISO datetime semantics. Blank `TRAN-PROC-TS` becomes `null`.
- Parse report-request lines with exactly five pipe-delimited fields in the `CORPT00C` order: timestamp, user ID, report name, start date, end date.
- Support only `Monthly`, `Yearly`, and `Custom` report names because those are the only values `CORPT00C` emits.
- Reject report requests whose start date is after the end date.

## JSON Serialization Rules

- Serialize `Decimal` money values with `model_dump(mode="json")`, which emits JSON strings such as `"504.78"` to preserve precision.
- Serialize `date` values as `YYYY-MM-DD`.
- Serialize `datetime` values as ISO 8601 strings without timezone offsets because the source flat files do not carry timezone information.
- Persist job telemetry in `store.json` under `operations.job_runs` and `operations.job_run_details`; no separate telemetry file is introduced in Phase 1.
