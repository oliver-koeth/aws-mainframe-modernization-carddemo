# Phase 1 Record Layouts

This document is the consolidated Phase 1 index from authoritative GNUCobol copybooks and runtime flat files into the modernization JSON schema under `output/backend/store.json`.

Use this document first when later stories need to trace an entity from source record layout to canonical model. The GNUCobol flat-file runtime under `app/cbl`, `app/cpy`, `app/data/ASCII`, and `app/data/ASCII.seed` remains authoritative over the legacy CICS runtime for Phase 1 behavior.

## Store Targets

The canonical store envelope is documented in `output/docs/store-schema.md`. Phase 1 record families map into these collections:

| Store collection | Canonical model(s) | Source record family |
| --- | --- | --- |
| `users` | `UserSecurityRecord` | `CSUSR01Y` |
| `customers` | `CustomerRecord` | `CVCUS01Y` |
| `accounts` | `AccountRecord` | `CVACT01Y` |
| `cards` | `CardRecord` | `CVACT02Y` |
| `card_account_xref` | `CardAccountXrefRecord` | `CVACT03Y` |
| `category_balances` | `CategoryBalanceRecord` | `CVTRA01Y` |
| `disclosure_groups` | `DisclosureGroupRecord` | `CVTRA02Y` |
| `transaction_types` | `TransactionTypeRecord` | `CVTRA03Y` |
| `transaction_categories` | `TransactionCategoryRecord` | `CVTRA04Y` |
| `transactions` | `TransactionRecord` | `CVTRA05Y` and `CVTRA06Y` |
| `report_requests` | `ReportRequestRecord` | `tranrept_requests.txt` runtime log |
| `operations.job_runs` | `JobRunRecord` | Phase 1 JSON-only operational contract |
| `operations.job_run_details` | `JobRunDetailRecord` | Phase 1 JSON-only operational contract |
| Deferred report output | `TransactionReportDetailRecord` | `CVTRA07Y` |

## Record Index

| Entity | Authoritative source | Runtime / bootstrap input | Logical width or format | Key fields | Canonical target |
| --- | --- | --- | --- | --- | --- |
| User security | `app/cpy/CSUSR01Y.cpy` | `app/data/ASCII/usrsec.dat`, `app/data/ASCII.seed/usrsec.dat` | `80` bytes | `user_id` | `users[] -> UserSecurityRecord` |
| Customer | `app/cpy/CVCUS01Y.cpy` | `app/data/ASCII/custdata.txt`, `app/data/ASCII.seed/custdata.txt` | `500` bytes | `customer_id` | `customers[] -> CustomerRecord` |
| Account | `app/cpy/CVACT01Y.cpy` | `app/data/ASCII/acctdata.txt`, `app/data/ASCII.seed/acctdata.txt` | `300` bytes | `account_id` | `accounts[] -> AccountRecord` |
| Card | `app/cpy/CVACT02Y.cpy` | `app/data/ASCII/carddata.txt`, `app/data/ASCII.seed/carddata.txt` | `150` bytes | `card_number`, `account_id` | `cards[] -> CardRecord` |
| Card/account xref | `app/cpy/CVACT03Y.cpy` | `app/data/ASCII/cardxref.txt`, `app/data/ASCII.seed/cardxref.txt` | `50` bytes | `card_number`, `customer_id`, `account_id` | `card_account_xref[] -> CardAccountXrefRecord` |
| Category balance | `app/cpy/CVTRA01Y.cpy` | `app/data/ASCII/tcatbal.txt`, `app/data/ASCII.seed/tcatbal.txt` | `50` bytes | `account_id`, `transaction_type_code`, `transaction_category_code` | `category_balances[] -> CategoryBalanceRecord` |
| Disclosure group | `app/cpy/CVTRA02Y.cpy` | `app/data/ASCII/discgrp.txt`, `app/data/ASCII.seed/discgrp.txt` | `50` bytes | `account_group_id`, `transaction_type_code`, `transaction_category_code` | `disclosure_groups[] -> DisclosureGroupRecord` |
| Transaction type | `app/cpy/CVTRA03Y.cpy` | `app/data/ASCII/trantype.txt`, `app/data/ASCII.seed/trantype.txt` | `60` bytes | `transaction_type_code` | `transaction_types[] -> TransactionTypeRecord` |
| Transaction category | `app/cpy/CVTRA04Y.cpy` | `app/data/ASCII/trancatg.txt`, `app/data/ASCII.seed/trancatg.txt` | `60` bytes | `transaction_type_code`, `transaction_category_code` | `transaction_categories[] -> TransactionCategoryRecord` |
| Transaction event | `app/cpy/CVTRA05Y.cpy`, `app/cpy/CVTRA06Y.cpy` | `app/data/ASCII/dailytran.txt`, `app/data/ASCII.seed/dailytran.txt` | `350` bytes | `transaction_id` | `transactions[] -> TransactionRecord` |
| Report request | `app/data/ASCII/tranrept_requests.txt` | Runtime-managed only; empty by default until `CORPT00C` writes rows | Pipe-delimited `timestamp|user_id|report_name|start_date|end_date` | `requested_at`, `requested_by_user_id`, `report_type`, `start_date`, `end_date` | `report_requests[] -> ReportRequestRecord` |
| Report detail projection | `app/cpy/CVTRA07Y.cpy` | No current runtime flat file | `115` bytes | Report-line projection fields | Deferred `TransactionReportDetailRecord` contract only |
| Job run telemetry | No legacy flat file; Phase 1 schema contract | JSON store operational data | JSON object | `job_run_id` | `operations.job_runs[] -> JobRunRecord` |
| Job run detail telemetry | No legacy flat file; Phase 1 schema contract | JSON store operational data | JSON object | `job_run_id`, detail sequence / timestamp payload chosen by later services | `operations.job_run_details[] -> JobRunDetailRecord` |

## Relationship Map

- `CardRecord.account_id` and `CardAccountXrefRecord.account_id` join to `AccountRecord.account_id`.
- `CardAccountXrefRecord.customer_id` joins to `CustomerRecord.customer_id`.
- `TransactionCategoryRecord` joins to `TransactionTypeRecord` by `transaction_type_code`.
- `CategoryBalanceRecord` joins to `TransactionCategoryRecord` by `transaction_type_code` + `transaction_category_code`, then joins to `AccountRecord` by `account_id`.
- `DisclosureGroupRecord` joins to `TransactionCategoryRecord` by `transaction_type_code` + `transaction_category_code`, then joins to `AccountRecord` by `group_id`.
- `TransactionRecord` uses `transaction_type_code`, `transaction_category_code`, `account_id`, and `card_number` semantics already established by the account/card/reference datasets.

## Parsing Conventions

- Fixed-width copybook width is authoritative even when GNUCobol `LINE SEQUENTIAL` files are physically shorter on disk because trailing spaces were omitted. Right-pad each line to the logical width before slicing fields.
- Oversized fixed-width lines fail deterministically instead of being truncated.
- Required text fields are right-trimmed and rejected when blank after trimming.
- Optional text fields are right-trimmed and normalized to `null` when blank.
- Numeric identifiers that can contain meaningful leading zeros, such as customer IDs, SSNs, account IDs, card numbers, CVV codes, and transaction category codes, stay as strings in JSON.
- COBOL display-form signed decimals are decoded from their trailing overpunch character into `Decimal` values. Phase 1 does not use floats for persisted money.
- ISO `YYYY-MM-DD` date fields are parsed as `date`. Timestamp fields are parsed as timezone-free ISO `datetime` values because the source files do not encode timezone offsets.
- Pipe-delimited report-request rows are not fixed-width and must contain exactly five fields in `CORPT00C` order.

## Malformed And Unsupported Data Handling

- Current entity parsers hard-fail deterministically on malformed lines. Unsupported widths, blank required fields, invalid dates, invalid signed-decimal suffixes, and invalid digit-only fields raise parse errors rather than being quarantined or coerced.
- Unknown cross-file references are preserved at the record-model level when the local record itself is structurally valid; later import and service stories are responsible for enforcing referential integrity checks.
- Unsupported code values that are record-local semantics today also fail deterministically:
  - `SEC-USR-TYPE` supports only `A` and `U`.
  - `CUST-PRI-CARD-HOLDER-IND` supports only `Y` and `N`.
  - Account and card active-status handling currently supports only `Y`.
  - `tranrept_requests.txt` report names support only `Monthly`, `Yearly`, and `Custom`.

## Deferred Or JSON-Only Contracts

- `CVTRA07Y` is authoritative for the printable report-detail layout, but Phase 1 defines only the `TransactionReportDetailRecord` contract. No report-output flat file is parsed yet because the current runtime persists requests and transactions, not rendered report lines.
- `JobRunRecord` and `JobRunDetailRecord` have no legacy flat-file source. They are Phase 1 JSON persistence contracts reserved under `operations.*` so later batch-monitoring stories can write durable telemetry without reshaping `store.json`.
- Runtime-managed files such as `tranrept_requests.txt` may be empty after reset scripts. Empty operational datasets are still represented by present-but-empty collections in `store.json`.

## Supporting References

- `output/docs/phase-1-source-artifacts.md` inventories the copybooks, runtime files, seed files, and GNUCobol consumers.
- `output/docs/user-security-records.md`, `output/docs/customer-records.md`, `output/docs/account-card-records.md`, `output/docs/transaction-reference-records.md`, and `output/docs/transaction-activity-records.md` retain the field-level detail for each record family.
- `output/docs/store-schema.md` defines the top-level `store.json` envelope that these records populate.
