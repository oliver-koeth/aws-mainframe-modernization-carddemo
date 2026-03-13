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
- During Phase 1 bootstrap, import `tranrept_requests.txt` from `app/data/ASCII` rather than `app/data/ASCII.seed`. If the runtime log is missing or empty, normalize it to an empty `report_requests[]` collection.

## JSON Serialization Rules

- Serialize `Decimal` money values with `model_dump(mode="json")`, which emits JSON strings such as `"504.78"` to preserve precision.
- Serialize `date` values as `YYYY-MM-DD`.
- Serialize `datetime` values as ISO 8601 strings without timezone offsets because the source flat files do not carry timezone information.
- Persist job telemetry in `store.json` under `operations.job_runs` and `operations.job_run_details`; no separate telemetry file is introduced in Phase 1.
- Preserve source fields that later slices do not yet consume, such as transaction filler text and disclosure/report metadata already represented in the canonical models, instead of silently dropping them during import.

## Transaction Creation Service

Phase 1 now exposes `TransactionService` under `output/backend/app/domain/transactions.py` for the `COTRN02C` transaction-add flow. The service is storage-backed and framework-agnostic: it validates raw transaction-add inputs, resolves the account/card pair through the shared lookup service, and appends a canonical `TransactionRecord` into `store.json`.

`TransactionService.validate_transaction()` and `create_transaction()` currently enforce these `COTRN02C`-derived rules:

- resolve the card/account pair using the same first-match xref semantics as the lookup service, and fail when the supplied account/card values conflict or the primary account/card is inactive
- require a 2-digit numeric `transaction_type_code` and a 4-digit numeric `transaction_category_code`
- require the resolved type/category pair to exist in `transaction_types[]` and `transaction_categories[]`
- require the resolved `(account_id, transaction_type_code, transaction_category_code)` row to exist in `category_balances[]` so the created transaction already maps to a persisted posting bucket
- require nonblank `source`, `description`, merchant name, merchant city, and merchant ZIP values, and reject values that would overflow the authoritative fixed-width fields
- require `merchant_id` to be exactly 9 digits so the canonical `TransactionRecord` stays compatible with the `CVTRA05Y`/`CVTRA06Y` layout
- require amount text in signed decimal form such as `+00000123.45` or `-00000123.45`; the service does not round and rejects values that do not fit the 11-character signed-zoned-decimal storage field
- require `originated_on` and optional `processed_on` in `YYYY-MM-DD` form, defaulting the processed date to the original date when omitted
- reject transactions whose original date is after the resolved account expiration date

When a transaction is created, the service mirrors `COTRN02C` append behavior by scanning persisted `transactions[]` in store order, remembering the last numeric `transaction_id`, incrementing it by one, zero-padding to 16 digits, and appending the new row at the end of the collection. As in the COBOL program, nonnumeric historical IDs do not participate in next-ID assignment.

The COBOL source only performs basic `YYYY-MM-DD` shape checks with month/day range bounds. The modernization service is intentionally stricter here because canonical JSON stores typed `date`/`datetime` values, so impossible calendar dates such as `2026-02-30` are rejected instead of being coerced.

## Posting Service

Phase 1 also exposes `PostingService` for the bill-payment behavior that the flat-file runtime splits between `COBIL00C` and `CBTRN02C`.

`PostingService.create_online_bill_payment(account_id=...)` mirrors the online bill-pay screen:

- resolve the first related card for the supplied account using persisted `card_account_xref[]` order
- require a positive `accounts[].current_balance`
- append a canonical payment transaction with fixed COBOL values: `transaction_type_code="02"`, `transaction_category_code="0002"`, `source="POS TERM"`, `description="BILL PAYMENT - ONLINE"`, merchant ID `999999999`, merchant name `BILL PAYMENT`, merchant city `N/A`, merchant ZIP `N/A`
- stamp both `originated_at` and `processed_at` from the current runtime timestamp
- set only `accounts[].current_balance` to zero after writing the transaction

That last rule is important: the current GNUCobol online flow does not also rewrite `category_balances[]`, `current_cycle_credit`, or `current_cycle_debit`.

`PostingService.post_transaction(transaction)` mirrors the `CBTRN02C` posting update path over a canonical `TransactionRecord`:

- resolve the account from the transaction card number through the first matching xref row
- stamp `processed_at` with the current runtime timestamp when it is absent
- append the posted transaction to `transactions[]`
- update the first matching `category_balances[]` row for `(account_id, transaction_type_code, transaction_category_code)` or create a new row when none exists
- add the transaction amount into `accounts[].current_balance`
- add nonnegative amounts into `accounts[].current_cycle_credit`; add negative amounts into `accounts[].current_cycle_debit`

This means the modernization layer preserves the COBOL split between immediate online bill payment and later posting updates instead of collapsing them into one inferred balance rule.
