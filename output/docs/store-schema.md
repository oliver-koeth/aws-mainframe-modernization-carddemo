# Store Schema

`output/backend/store.json` is the canonical application-data document for the modernization target. Phase 1 fixes the top-level envelope now so later importer, API, and batch stories can add records without redefining the store shape per slice.

## Schema Envelope

The store root is always a JSON object with these keys:

- `metadata`: schema identification for deterministic loading and future migrations.
- `users`: canonical user-security records derived from `CSUSR01Y`.
- `customers`: canonical customer records derived from `CVCUS01Y`.
- `accounts`: canonical account records derived from `CVACT01Y`.
- `cards`: canonical card records derived from `CVACT02Y`.
- `card_account_xref`: canonical card-to-account links derived from `CVACT03Y`.
- `transaction_types`: reference records derived from `CVTRA03Y`.
- `transaction_categories`: reference records derived from `CVTRA04Y`.
- `disclosure_groups`: reference records derived from `CVTRA02Y`.
- `category_balances`: balance-by-category records derived from `CVTRA01Y`.
- `transactions`: canonical transaction event records derived from `CVTRA05Y` through `CVTRA07Y` as applicable.
- `report_requests`: canonical report-request records sourced from `tranrept_requests.txt`.
- `operations`: operational collections that are persisted in the same store even before their APIs or schedulers exist.

The initial Phase 1 metadata contract is:

```json
{
  "schema_name": "carddemo.store",
  "schema_version": 1
}
```

`operations` is reserved for non-seed operational state:

- `sessions`: future authenticated session records for Phase 2 API work.
- `job_runs`: batch run headers for later monitoring and scheduling slices.
- `job_run_details`: detailed job run events or per-step telemetry associated with `job_runs`.

The current Phase 1 job telemetry contract is intentionally minimal:

- `operations.job_runs[]` rows persist `job_run_id`, `job_name`, `status`, `started_at`, `ended_at`, and optional `summary`.
- `status` is limited to `pending`, `running`, `succeeded`, and `failed`.
- `operations.job_run_details[]` rows persist `job_run_id`, `sequence_number`, `recorded_at`, `level`, `message`, and optional JSON `context`.

All collections are present even when empty. Later stories may refine the record shape inside each collection, but they should not add or remove top-level collections without a schema-version change.

## Versioning Rules

- `schema_name` identifies the contract family. Loaders must reject unknown schema names rather than guessing compatibility.
- `schema_version` is an integer and must be explicitly supported by backend storage code.
- Backward-compatible additions inside existing collection items do not require a top-level version bump if older readers can ignore the new fields safely.
- Any change to top-level keys, collection meaning, or incompatible record semantics requires a new supported `schema_version`.
- Future migrations should be explicit: either transform older versions into the current version before normal use, or fail with a deterministic unsupported-version error until a migration step is added.

## Deterministic Load Behavior

- Missing `store.json`: treat as a fresh workspace and return the default empty schema envelope.
- Empty `store.json`: treat the same as missing and return the default empty schema envelope.
- Unsupported `schema_name` or `schema_version`: fail immediately with a storage schema error.
- Missing required collections: fail immediately with a storage schema error.

This behavior is implemented in `output/backend/app/storage.py` so importer and service stories all share the same contract.
