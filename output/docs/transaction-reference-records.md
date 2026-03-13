# Transaction Reference Records

This document defines the canonical Phase 1 JSON models for the GNUCobol flat-file reference datasets backed by `CVTRA01Y` through `CVTRA04Y`.

## Authoritative Sources

| Entity | Copybook | Runtime file | Seed file | Current GNUCobol consumers |
| --- | --- | --- | --- | --- |
| Category balance | `app/cpy/CVTRA01Y.cpy` | `app/data/ASCII/tcatbal.txt` | `app/data/ASCII.seed/tcatbal.txt` | `app/cbl/CBACT04C.cbl`, `app/cbl/CBTRN02C.cbl` |
| Disclosure group | `app/cpy/CVTRA02Y.cpy` | `app/data/ASCII/discgrp.txt` | `app/data/ASCII.seed/discgrp.txt` | `app/cbl/CBACT04C.cbl` |
| Transaction type | `app/cpy/CVTRA03Y.cpy` | `app/data/ASCII/trantype.txt` | `app/data/ASCII.seed/trantype.txt` | `app/cbl/CBTRN03C.cbl` |
| Transaction category | `app/cpy/CVTRA04Y.cpy` | `app/data/ASCII/trancatg.txt` | `app/data/ASCII.seed/trancatg.txt` | `app/cbl/CBTRN03C.cbl` |

The GNUCobol flat-file runtime remains authoritative for Phase 1 behavior. These parsers normalize those fixed-width records without introducing new lookup rules beyond what the files and COBOL programs already encode.

## Canonical Models

### `CategoryBalanceRecord` from `CVTRA01Y`

- Logical width: `50`
- Key fields: `account_id` + `transaction_type_code` + `transaction_category_code`
- JSON fields:
  - `account_id`: 11-digit string from `TRANCAT-ACCT-ID`
  - `transaction_type_code`: 2-character code from `TRANCAT-TYPE-CD`
  - `transaction_category_code`: 4-digit string from `TRANCAT-CD`
  - `balance`: `Decimal` parsed from `TRAN-CAT-BAL` signed zoned-decimal text
  - `filler`: trimmed optional remainder

### `DisclosureGroupRecord` from `CVTRA02Y`

- Logical width: `50`
- Key fields: `account_group_id` + `transaction_type_code` + `transaction_category_code`
- JSON fields:
  - `account_group_id`: trimmed string from `DIS-ACCT-GROUP-ID`
  - `transaction_type_code`: 2-character code from `DIS-TRAN-TYPE-CD`
  - `transaction_category_code`: 4-digit string from `DIS-TRAN-CAT-CD`
  - `interest_rate`: `Decimal` parsed from `DIS-INT-RATE` signed zoned-decimal text
  - `filler`: trimmed optional remainder

### `TransactionTypeRecord` from `CVTRA03Y`

- Logical width: `60`
- Primary key: `transaction_type_code`
- JSON fields:
  - `transaction_type_code`: 2-character code from `TRAN-TYPE`
  - `description`: trimmed text from `TRAN-TYPE-DESC`
  - `filler`: trimmed optional remainder

### `TransactionCategoryRecord` from `CVTRA04Y`

- Logical width: `60`
- Key fields: `transaction_type_code` + `transaction_category_code`
- JSON fields:
  - `transaction_type_code`: 2-character code from `TRAN-TYPE-CD`
  - `transaction_category_code`: 4-digit string from `TRAN-CAT-CD`
  - `description`: trimmed text from `TRAN-CAT-TYPE-DESC`
  - `filler`: trimmed optional remainder

## Relationship Rules

- `TransactionCategoryRecord.transaction_type_code` must correspond to `TransactionTypeRecord.transaction_type_code` for downstream lookup integrity.
- `CategoryBalanceRecord` and `DisclosureGroupRecord` both use the composite `transaction_type_code` + `transaction_category_code` pair used by `TransactionCategoryRecord`.
- `CategoryBalanceRecord.account_id` joins to `AccountRecord.account_id`.
- `DisclosureGroupRecord.account_group_id` joins to `AccountRecord.group_id`; the COBOL interest calculator (`CBACT04C`) reads disclosure rates by account group and transaction category rather than by account number.

## Parsing Rules

- Treat the copybook width as authoritative even when GNUCobol line-sequential files omit trailing spaces on disk; right-pad shorter lines before slicing fields.
- Required text fields fail deterministically when blank after right trimming.
- Digit-only identifiers and category codes remain strings to preserve formatting and leading zeros.
- Signed numeric values are decoded from the trailing overpunch character into `Decimal` values with two fractional digits.
- Oversized lines fail immediately instead of being truncated.

## Deterministic Handling of Unknown or Unsupported Values

- The parsers validate only record-local constraints: width, required/optional status, digit-only fields, and signed-zoned-decimal formatting.
- Unknown transaction type or category codes are preserved as-is inside the record model; cross-file lookup failures are a later import or service-layer concern and must fail deterministically there rather than being coerced.
- `CVTRA01Y` through `CVTRA04Y` do not expose additional status flags in the flat-file runtime. There are therefore no hidden flag defaults to infer in Phase 1.
