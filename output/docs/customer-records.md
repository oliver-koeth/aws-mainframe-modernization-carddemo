# Customer Records

`CVCUS01Y` defines the authoritative Phase 1 customer record used by the flat-file GNUCobol runtime. The runtime file is `app/data/ASCII/custdata.txt`, with shipped bootstrap rows in `app/data/ASCII.seed/custdata.txt`.

## Record Layout

- Copybook: `app/cpy/CVCUS01Y.cpy`
- Logical width: `500` bytes
- Physical file behavior: GNUCobol writes `custdata.txt` as `LINE SEQUENTIAL`, so trailing spaces may be omitted on disk. Parsers should right-pad each line to `500` characters before slicing copybook fields.

| Copybook field | Width | JSON target | Handling |
| --- | ---: | --- | --- |
| `CUST-ID` | 9 | `customer_id` | Required. Must contain exactly 9 digits. Stored as a string to preserve leading zeros. |
| `CUST-FIRST-NAME` | 25 | `name.first_name` | Required. Right-trimmed. Blank values are rejected. |
| `CUST-MIDDLE-NAME` | 25 | `name.middle_name` | Optional. Right-trimmed. All-space values normalize to `null`. |
| `CUST-LAST-NAME` | 25 | `name.last_name` | Required. Right-trimmed. Blank values are rejected. |
| `CUST-ADDR-LINE-1` | 50 | `address.line_1` | Required. Right-trimmed. Blank values are rejected. |
| `CUST-ADDR-LINE-2` | 50 | `address.line_2` | Optional. Right-trimmed. All-space values normalize to `null`. |
| `CUST-ADDR-LINE-3` | 50 | `address.line_3` | Optional. Right-trimmed. All-space values normalize to `null`. |
| `CUST-ADDR-STATE-CD` | 2 | `address.state_code` | Required. Right-trimmed. Blank values are rejected. |
| `CUST-ADDR-COUNTRY-CD` | 3 | `address.country_code` | Required. Right-trimmed. Blank values are rejected. |
| `CUST-ADDR-ZIP` | 10 | `address.postal_code` | Required. Right-trimmed. Blank values are rejected. |
| `CUST-PHONE-NUM-1` | 15 | `contact.primary_phone` | Required. Right-trimmed. Blank values are rejected. |
| `CUST-PHONE-NUM-2` | 15 | `contact.secondary_phone` | Optional. Right-trimmed. All-space values normalize to `null`. |
| `CUST-SSN` | 9 | `contact.social_security_number` | Required. Must contain exactly 9 digits. Stored as a string to preserve leading zeros. |
| `CUST-GOVT-ISSUED-ID` | 20 | `contact.government_issued_id` | Optional. Right-trimmed. All-space values normalize to `null`. |
| `CUST-DOB-YYYY-MM-DD` | 10 | `date_of_birth` | Required. Parsed as an ISO `date`. Invalid or non-ISO values are rejected deterministically. |
| `CUST-EFT-ACCOUNT-ID` | 10 | `contact.eft_account_id` | Optional. Right-trimmed. All-space values normalize to `null`. |
| `CUST-PRI-CARD-HOLDER-IND` | 1 | `primary_card_holder_indicator`, `is_primary_card_holder` | Required. Supported values are `Y` and `N`. Any other value is rejected as unsupported. |
| `CUST-FICO-CREDIT-SCORE` | 3 | `fico_credit_score` | Required. Must contain only digits. Parsed as an integer in the inclusive range `0..999`. |
| `FILLER` | 168 | `filler` | Optional. Right-trimmed. All-space values normalize to `null`. |

## Semantics

- Customer IDs and SSNs stay as digit strings in JSON so later services preserve COBOL-width identifiers without stripping leading zeros.
- The flat-file runtime copies `CUST-DOB-YYYY-MM-DD` straight through export/import flows, so Phase 1 parsing treats ISO `YYYY-MM-DD` as authoritative rather than coercing alternate date formats.
- `CUST-PRI-CARD-HOLDER-IND` is modeled with both the preserved code and a normalized boolean for later service code. Unsupported values fail parsing instead of defaulting silently.
