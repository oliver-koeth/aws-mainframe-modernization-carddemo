# Account, Card, And Cross-Reference Records

## Authority

`CVACT01Y`, `CVACT02Y`, and `CVACT03Y` are the authoritative Phase 1 record layouts for account, card, and card/account relationship data. For runtime behavior, prefer the GNUCobol flat-file files `app/data/ASCII/acctdata.txt`, `app/data/ASCII/carddata.txt`, and `app/data/ASCII/cardxref.txt`, with `app/data/ASCII.seed/*` as the deterministic bootstrap inputs.

## Record Widths And Models

| Source copybook | Runtime/seed file | Logical width | Canonical model | Key fields |
| :-- | :-- | :-- | :-- | :-- |
| `app/cpy/CVACT01Y.cpy` | `acctdata.txt` | 300 | `AccountRecord` | `account_id` |
| `app/cpy/CVACT02Y.cpy` | `carddata.txt` | 150 | `CardRecord` | `card_number`, `account_id` |
| `app/cpy/CVACT03Y.cpy` | `cardxref.txt` | 50 | `CardAccountXrefRecord` | `card_number`, `customer_id`, `account_id` |

`cardxref.txt` links `customer_id` from `CVCUS01Y` to both the account and card records. `carddata.txt.account_id` and `cardxref.txt.account_id` should point at the same `AccountRecord.account_id` when the shipped seed data is imported.

## Field Mapping

### `CVACT01Y` -> `AccountRecord`

| Offset | Length | Source field | Target field | Notes |
| :-- | --: | :-- | :-- | :-- |
| 1 | 11 | `ACCT-ID` | `account_id` | Preserve leading zeroes as a string. |
| 12 | 1 | `ACCT-ACTIVE-STATUS` | `active_status`, `is_active` | Phase 1 currently supports only `Y`; other values fail deterministically. |
| 13 | 12 | `ACCT-CURR-BAL` | `current_balance` | Parse COBOL signed zoned-decimal text into `Decimal`. |
| 25 | 12 | `ACCT-CREDIT-LIMIT` | `credit_limit` | Parse as `Decimal`. |
| 37 | 12 | `ACCT-CASH-CREDIT-LIMIT` | `cash_credit_limit` | Parse as `Decimal`. |
| 49 | 10 | `ACCT-OPEN-DATE` | `open_date` | ISO `YYYY-MM-DD`. |
| 59 | 10 | `ACCT-EXPIRAION-DATE` | `expiration_date` | Copybook spelling preserved in source reference, normalized in JSON. |
| 69 | 10 | `ACCT-REISSUE-DATE` | `reissue_date` | ISO `YYYY-MM-DD`. |
| 79 | 12 | `ACCT-CURR-CYC-CREDIT` | `current_cycle_credit` | Parse as `Decimal`. |
| 91 | 12 | `ACCT-CURR-CYC-DEBIT` | `current_cycle_debit` | Parse as `Decimal`. |
| 103 | 10 | `ACCT-ADDR-ZIP` | `billing_postal_code` | Preserve as trimmed text; the shipped seed includes alphanumeric values. |
| 113 | 10 | `ACCT-GROUP-ID` | `group_id` | Blank becomes `null`. |
| 123 | 178 | `FILLER` | `filler` | Blank becomes `null`. |

### `CVACT02Y` -> `CardRecord`

| Offset | Length | Source field | Target field | Notes |
| :-- | --: | :-- | :-- | :-- |
| 1 | 16 | `CARD-NUM` | `card_number` | Preserve leading zeroes as a string. |
| 17 | 11 | `CARD-ACCT-ID` | `account_id` | Links to `AccountRecord.account_id`. |
| 28 | 3 | `CARD-CVV-CD` | `cvv_code` | Preserve as a zero-padded string. |
| 31 | 50 | `CARD-EMBOSSED-NAME` | `embossed_name` | Right-trim spaces; blank is invalid. |
| 81 | 10 | `CARD-EXPIRAION-DATE` | `expiration_date` | ISO `YYYY-MM-DD`. |
| 91 | 1 | `CARD-ACTIVE-STATUS` | `active_status`, `is_active` | Phase 1 currently supports only `Y`; other values fail deterministically. |
| 92 | 59 | `FILLER` | `filler` | Blank becomes `null`. |

### `CVACT03Y` -> `CardAccountXrefRecord`

| Offset | Length | Source field | Target field | Notes |
| :-- | --: | :-- | :-- | :-- |
| 1 | 16 | `XREF-CARD-NUM` | `card_number` | Links to `CardRecord.card_number`. |
| 17 | 9 | `XREF-CUST-ID` | `customer_id` | Links to `CustomerRecord.customer_id`. |
| 26 | 11 | `XREF-ACCT-ID` | `account_id` | Links to `AccountRecord.account_id`. |
| 37 | 14 | `FILLER` | `filler` | The shipped seed omits trailing filler on disk, so this is usually blank after right-padding. |

## Parsing Conventions

- Right-pad lines to the logical copybook width before slicing fields because GNUCobol `LINE SEQUENTIAL` writes omit trailing spaces on disk.
- Required text fields are right-trimmed; blank required fields fail deterministically.
- Optional text fields are right-trimmed and become `null` when blank.
- Account monetary fields use COBOL signed zoned-decimal text. The trailing character carries both the final digit and the sign, for example `{` means positive zero and `N` means negative five.
- Identifier fields such as account IDs, customer IDs, card numbers, and CVV codes stay as strings to preserve leading zeroes.
- Unsupported status codes, malformed dates, non-digit identifiers, and invalid signed-decimal suffixes raise deterministic parser errors rather than being coerced silently.
