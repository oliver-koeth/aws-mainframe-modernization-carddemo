# PRD: Phase 1 Domain Model And Data Contracts

## Introduction

Phase 1 establishes the canonical domain layer for the CardDemo modernization target. It converts GNUCobol flat-file record layouts and seeded ASCII data into explicit backend models, deterministic import/bootstrap behavior, and reusable framework-agnostic domain services that later API and batch slices can call without re-deriving business structure.

This phase is intentionally non-user-facing. It must not introduce new REST endpoints or Angular screens. Its purpose is to remove ambiguity from record layouts, persistence schema, and shared business service boundaries before the online and batch migration phases begin.

This PRD is based on:

- [MIGRATION_PLAN.md](/Users/Oliver.Koeth/work/aws-mainframe-modernization-carddemo/MIGRATION_PLAN.md)
- [tasks/prd-phase-0-scaffolding.md](/Users/Oliver.Koeth/work/aws-mainframe-modernization-carddemo/tasks/prd-phase-0-scaffolding.md)
- GNUCobol flat-file runtime sources under `app/cbl`, `app/cpy`, and `app/data/ASCII`
- Seed data and reset/init scripts under `app/data/ASCII.seed` and `scripts/`

## Goals

- Define canonical backend models for all Phase 1 entities using the GNUCobol flat-file runtime as the business structure source of truth.
- Document record layouts, fixed-width parsing rules, and JSON schema mapping so later slices do not infer structure differently.
- Provide a deterministic bootstrap path that imports shipped ASCII seed data into `output/backend/store.json`.
- Establish stable, framework-agnostic domain services for authentication/session lookup, account/customer/card lookup, transaction validation/posting semantics, report requests, and job telemetry writes.
- Keep all Phase 1 work implementation-ready for later API and UI slices without introducing user-facing endpoints.

## Authoritative Phase 1 Sources

Phase 1 data behavior is anchored to the GNUCobol flat-file runtime under `app/cbl`, `app/cpy`, `app/data/ASCII`, and `app/data/ASCII.seed`. When the flat-file runtime and the legacy CICS-oriented runtime differ, the GNUCobol flat-file runtime is authoritative for Phase 1 modeling, parsing, bootstrap, and service behavior.

The detailed inventory for this phase lives in [output/docs/phase-1-source-artifacts.md](/Users/Oliver.Koeth/work/aws-mainframe-modernization-carddemo/output/docs/phase-1-source-artifacts.md). That inventory identifies:

- the authoritative copybooks for `CSUSR01Y`, `CVCUS01Y`, `CVACT01Y` through `CVACT03Y`, and `CVTRA01Y` through `CVTRA07Y`
- the corresponding runtime and seed flat files under `app/data/ASCII` and `app/data/ASCII.seed`
- the GNUCobol programs that currently consume those layouts
- the reset/bootstrap scripts under `scripts/` that initialize or restore the flat-file datasets

## User Stories

### US-001: Inventory authoritative Phase 1 source artifacts
**Description:** As a developer, I want the exact copybooks, programs, flat files, and scripts for Phase 1 identified so that implementation does not drift from the GNUCobol runtime baseline.

**Acceptance Criteria:**
- [ ] List the authoritative copybooks, flat files, and scripts used by Phase 1 in the PRD or linked docs.
- [ ] Identify which entities come from `CVACT01Y`, `CVACT02Y`, `CVACT03Y`, `CVCUS01Y`, `CVTRA01Y` through `CVTRA07Y`, and `CSUSR01Y`.
- [ ] Identify the seed/bootstrap sources under `app/data/ASCII.seed` and the reset/init scripts under `scripts/`.
- [ ] Explicitly state that the GNUCobol flat-file runtime is authoritative over the legacy CICS runtime for Phase 1 data behavior.

### US-002: Define canonical store schema envelope and versioning
**Description:** As a developer, I want a versioned `store.json` schema envelope so that imported data and later mutations share one explicit contract.

**Acceptance Criteria:**
- [ ] Define the top-level `store.json` structure, including schema version metadata and entity collections.
- [ ] Define where job run history and future session-related data will live without requiring a Phase 1 API surface.
- [ ] Describe migration/versioning rules for future schema changes.
- [ ] Specify deterministic behavior when a store is missing, empty, or on an unsupported schema version.
- [ ] Typecheck passes.

### US-003: Model user security records
**Description:** As a developer, I want canonical user models derived from `CSUSR01Y` so that later authentication and administration flows can use a stable user contract.

**Acceptance Criteria:**
- [ ] Define Pydantic models for user security records and any normalized sub-structures required by the JSON store.
- [ ] Map fixed-width fields from the authoritative copybook to typed model fields, including status/role semantics if present in the flat-file runtime.
- [ ] Document field-level handling for trimmed text, blank values, and unsupported values.
- [ ] Add representative parser tests for valid and malformed user-security lines.
- [ ] Tests pass.
- [ ] Typecheck passes.

### US-004: Model customer records
**Description:** As a developer, I want canonical customer models derived from `CVCUS01Y` so that later inquiry and maintenance flows can reuse one customer contract.

**Acceptance Criteria:**
- [ ] Define Pydantic models for customer records and any normalized nested structures needed in JSON.
- [ ] Map fixed-width customer fields to typed model fields, including address/contact/date handling where present.
- [ ] Document blank-field and unsupported-value handling rules.
- [ ] Add representative parser tests for valid and malformed customer lines.
- [ ] Tests pass.
- [ ] Typecheck passes.

### US-005: Model account, card, and card cross-reference records
**Description:** As a developer, I want canonical account and card models so that account and card lookup flows have one shared contract.

**Acceptance Criteria:**
- [ ] Define Pydantic models for account records from `CVACT01Y`, card records from `CVACT02Y`, and card/account cross-reference records from `CVACT03Y`.
- [ ] Document key relationships between account IDs, customer IDs, and card numbers.
- [ ] Specify precision rules for balances, limits, and other money fields using `Decimal`.
- [ ] Add representative parser tests for valid and malformed lines across all three record types.
- [ ] Tests pass.
- [ ] Typecheck passes.

### US-006: Model transaction reference and balance records
**Description:** As a developer, I want canonical models for transaction types, categories, disclosure groups, and category balances so that transaction logic and reporting can reuse stable reference data.

**Acceptance Criteria:**
- [ ] Define Pydantic models for `CVTRA01Y` through `CVTRA04Y` record families used for category balances, disclosure groups, transaction types, and transaction categories.
- [ ] Document primary keys, lookup fields, and cross-entity relationships.
- [ ] Define deterministic handling for unknown codes, blank values, and unsupported flags.
- [ ] Add representative parser tests for valid and malformed lines across these record families.
- [ ] Tests pass.
- [ ] Typecheck passes.

### US-007: Model transaction event, report request, and job telemetry records
**Description:** As a developer, I want canonical models for transactions, report requests, and job runs so that both online and batch slices can share stable event and monitoring contracts.

**Acceptance Criteria:**
- [ ] Define Pydantic models for transaction records using the applicable `CVTRA05Y` through `CVTRA07Y` layouts and flat-file semantics.
- [ ] Define a canonical model for report requests sourced from `tranrept_requests.txt`.
- [ ] Define canonical job run and job run detail models for JSON persistence, even if Phase 1 does not yet implement schedulable jobs.
- [ ] Document timestamp, date, and money serialization rules used by these models.
- [ ] Add representative parser tests for valid and malformed transaction/report-request lines.
- [ ] Tests pass.
- [ ] Typecheck passes.

### US-008: Author `record-layouts` documentation
**Description:** As a developer, I want one document that explains how COBOL record layouts map into the modernization schema so later slices do not reverse-engineer field meanings repeatedly.

**Acceptance Criteria:**
- [ ] Create or update `output/docs/record-layouts.md`.
- [ ] Document each Phase 1 entity, its source copybook or flat file, record width, key fields, and target JSON model.
- [ ] Document parsing conventions such as trimming, numeric conversion, date interpretation, and malformed-line handling.
- [ ] Document any intentionally deferred or unsupported fields explicitly rather than omitting them silently.

### US-009: Implement reusable fixed-width parsing primitives
**Description:** As a developer, I want shared parsing helpers for fixed-width records so every importer and parser test uses the same width and conversion rules.

**Acceptance Criteria:**
- [ ] Implement shared parsing primitives under `output/backend/` rather than duplicating per-entity parsing logic.
- [ ] Parsing helpers support field slicing, typed conversion, and deterministic parse errors or quarantine results.
- [ ] Parser behavior is explicit for malformed-width lines, invalid numeric data, and blank optional fields.
- [ ] Add unit tests covering success paths and deterministic failures.
- [ ] Tests pass.
- [ ] Typecheck passes.

### US-010: Decide and implement malformed-line handling strategy
**Description:** As a developer, I want a deterministic strategy for malformed-width or invalid lines so bootstrap behavior is repeatable and diagnosable.

**Acceptance Criteria:**
- [ ] Choose one strategy for malformed lines: hard-fail import, quarantine with reporting, or another explicitly documented deterministic path.
- [ ] Apply the same strategy consistently across all Phase 1 parsers.
- [ ] Document where malformed-line details are recorded and how tests assert that behavior.
- [ ] Add tests covering malformed-width rejection or quarantine behavior.
- [ ] Tests pass.
- [ ] Typecheck passes.

### US-011: Define seed import command and bootstrap workflow
**Description:** As a developer, I want one canonical importer entry point so a fresh Phase 1 environment can initialize `store.json` from shipped seed data without manual file editing.

**Acceptance Criteria:**
- [ ] Define one canonical import command or script entry point under `output/backend/`.
- [ ] The workflow reads from `app/data/ASCII.seed/*` and initializes `output/backend/store.json`.
- [ ] The workflow is documented in backend docs with prerequisites and expected output.
- [ ] The workflow supports a clean bootstrap from repository seed data after Phase 0 scaffolding.
- [ ] Tests pass.
- [ ] Typecheck passes.

### US-012: Import user, customer, account, and card seed data
**Description:** As a developer, I want the primary identity and account datasets loaded into the JSON store so later domain services can assume seeded relationships exist.

**Acceptance Criteria:**
- [ ] Import user, customer, account, card, and card cross-reference data from the shipped ASCII seed files.
- [ ] Preserve key relationships across imported entities.
- [ ] Define deterministic rules for unsupported, ignored, or normalized source values.
- [ ] Add tests that assert stable entity counts and key relationships after import.
- [ ] Tests pass.
- [ ] Typecheck passes.

### US-013: Import transaction reference data and report-request seed data
**Description:** As a developer, I want reference and reporting datasets loaded into the JSON store so later transaction and reporting flows can rely on stable seeded lookups.

**Acceptance Criteria:**
- [ ] Import transaction types, transaction categories, disclosure groups, category balances, and report requests from the shipped seed files.
- [ ] Preserve lookup integrity among imported reference datasets.
- [ ] Document deterministic handling for values present in flat files but not yet used by later slices.
- [ ] Add tests that assert stable counts and representative lookup relationships after import.
- [ ] Tests pass.
- [ ] Typecheck passes.

### US-014: Bootstrap default store metadata and empty operational collections
**Description:** As a developer, I want seed import to produce a complete usable store so later slices can start without additional manual initialization.

**Acceptance Criteria:**
- [ ] Imported `store.json` includes schema version metadata and all required Phase 1 collections.
- [ ] Collections with no shipped seed rows still exist with deterministic empty defaults where later slices expect them.
- [ ] Backend startup after import does not require additional manual store edits.
- [ ] Add tests proving a newly imported store can be loaded successfully by backend storage code.
- [ ] Tests pass.
- [ ] Typecheck passes.

### US-015: Expose baseline import counts and verification expectations
**Description:** As a developer, I want documented baseline import counts and integrity checks so regressions in seed bootstrap can be detected quickly.

**Acceptance Criteria:**
- [ ] Document baseline row counts for imported Phase 1 entities or define a generated snapshot assertion approach with stable expectations.
- [ ] Document the key integrity checks that must hold after import.
- [ ] Add automated tests that fail when baseline counts or critical relationships drift unexpectedly.
- [ ] Tests pass.
- [ ] Typecheck passes.

### US-016: Implement authentication and session lookup domain service
**Description:** As a developer, I want a framework-agnostic authentication/session lookup service so the later session API can reuse Phase 1 business logic directly.

**Acceptance Criteria:**
- [ ] Implement a shared service that validates credentials against imported user data using the GNUCobol flat-file behavior as the source of truth where applicable.
- [ ] Implement session lookup behavior as a domain service contract without creating REST endpoints in Phase 1.
- [ ] Document any unresolved ambiguities in password or session semantics explicitly.
- [ ] Add pytest coverage for valid login, invalid login, disabled or unauthorized cases as supported by the source data.
- [ ] Tests pass.
- [ ] Typecheck passes.

### US-017: Implement customer, account, and card lookup domain services
**Description:** As a developer, I want shared lookup services so later inquiry flows can retrieve related customers, accounts, and cards from one place.

**Acceptance Criteria:**
- [ ] Implement lookup services for account ID, customer ID, and card number driven retrieval.
- [ ] Services return canonical domain models or explicit domain errors rather than framework-specific responses.
- [ ] Define deterministic behavior for missing records, inactive records, and ambiguous lookups if they can occur in the source data.
- [ ] Add pytest coverage for successful and failing lookup scenarios.
- [ ] Tests pass.
- [ ] Typecheck passes.

### US-018: Implement transaction validation and creation domain service
**Description:** As a developer, I want shared transaction validation and creation logic so later online and batch posting flows do not duplicate monetary and reference-data rules.

**Acceptance Criteria:**
- [ ] Implement a framework-agnostic service for transaction creation and validation.
- [ ] Validate required relationships against imported accounts, cards, transaction types, categories, and balances as required by the flat-file runtime semantics.
- [ ] Use `Decimal` consistently for money handling and document rounding rules if any apply.
- [ ] Add pytest coverage for valid transaction creation and representative validation failures.
- [ ] Tests pass.
- [ ] Typecheck passes.

### US-019: Implement bill-payment posting semantics service
**Description:** As a developer, I want bill-payment posting logic isolated in a shared service so later online and batch flows can reuse the same balance update rules.

**Acceptance Criteria:**
- [ ] Implement shared domain logic for bill-payment posting semantics based on the GNUCobol runtime behavior.
- [ ] Document how balances, transaction records, and category balances change when a payment is posted.
- [ ] Ensure the service remains framework-agnostic and storage-aware without introducing new API endpoints.
- [ ] Add pytest coverage for representative posting scenarios and validation failures.
- [ ] Tests pass.
- [ ] Typecheck passes.

### US-020: Implement report request capture and retrieval service
**Description:** As a developer, I want report-request capture logic in a shared service so later reporting APIs and jobs can reuse one contract.

**Acceptance Criteria:**
- [ ] Implement shared service methods for creating and retrieving report requests.
- [ ] Define canonical validation for report request fields and duplicate or conflicting request behavior if applicable.
- [ ] Persist report requests through shared storage contracts without introducing a Phase 1 endpoint.
- [ ] Add pytest coverage for request creation, retrieval, and validation errors.
- [ ] Tests pass.
- [ ] Typecheck passes.

### US-021: Implement job/run telemetry write service
**Description:** As a developer, I want shared job telemetry write behavior so later batch schedulers and admin surfaces can record run history consistently.

**Acceptance Criteria:**
- [ ] Implement shared service methods for creating and updating job run records in the JSON store.
- [ ] Define status transitions, timestamps, and stored metadata needed by later monitoring slices.
- [ ] Keep the service framework-agnostic and independent of actual schedule execution in Phase 1.
- [ ] Add pytest coverage for job run creation, transition updates, and invalid state changes.
- [ ] Tests pass.
- [ ] Typecheck passes.

### US-022: Document Phase 1 service contracts and deferred behavior
**Description:** As a developer, I want the Phase 1 service boundaries documented so later slices know which logic already exists and what remains deferred.

**Acceptance Criteria:**
- [ ] Document the public domain-service contracts created in Phase 1 in backend docs or `output/docs/`.
- [ ] Document explicitly which behaviors are deferred to Phase 2 or later, especially endpoint surfaces and UI flows.
- [ ] Document any known gaps where Phase 1 had to infer behavior from incomplete flat-file evidence.
- [ ] Keep documentation concise and implementation-oriented.

## Functional Requirements

1. FR-1: The system must treat the GNUCobol flat-file runtime under `app/cbl`, `app/cpy`, and `app/data/ASCII*` as the authoritative business-structure source for Phase 1.
2. FR-2: The system must define canonical Pydantic models for users, customers, accounts, cards, card cross-references, transactions, transaction types, transaction categories, disclosure groups, category balances, report requests, and job runs.
3. FR-3: The system must define a versioned top-level schema for `output/backend/store.json`.
4. FR-4: The system must document field-level mappings from authoritative copybooks and flat files into the Phase 1 canonical models.
5. FR-5: The system must create or update `output/docs/record-layouts.md` with record widths, key fields, parsing conventions, and deferred fields.
6. FR-6: The system must provide shared fixed-width parsing primitives rather than duplicating parsing behavior per entity.
7. FR-7: The system must handle malformed-width or otherwise invalid lines deterministically and document that strategy.
8. FR-8: The system must provide one canonical importer/bootstrap path that loads shipped ASCII seed data into `output/backend/store.json`.
9. FR-9: The importer must use `app/data/ASCII.seed/*` as the seed source unless an authoritative Phase 1 source artifact explicitly requires a different input.
10. FR-10: The importer must preserve key relationships among imported entities and make normalization rules explicit.
11. FR-11: The imported store must be usable by backend storage code without additional manual setup.
12. FR-12: The system must define baseline import verification expectations, including stable counts or equivalent deterministic integrity assertions.
13. FR-13: Phase 1 must implement framework-agnostic domain services for authentication/session lookup.
14. FR-14: Phase 1 must implement framework-agnostic domain services for customer/account/card lookup by primary business identifiers.
15. FR-15: Phase 1 must implement framework-agnostic domain services for transaction creation and validation.
16. FR-16: Phase 1 must implement shared bill-payment posting semantics based on the GNUCobol runtime behavior.
17. FR-17: Phase 1 must implement shared report-request capture logic.
18. FR-18: Phase 1 must implement shared job/run telemetry write logic for later batch monitoring features.
19. FR-19: Phase 1 must keep service outputs domain-oriented and must not introduce new REST endpoints or Angular UI routes.
20. FR-20: Phase 1 must include pytest coverage for parser behavior, seed import stability, domain service behavior, money handling, key lookups, update behavior, and validation errors.
21. FR-21: Phase 1 backend code must remain type-checkable with `python -m mypy app`.
22. FR-22: Phase 1 documentation must explicitly call out deferred behavior that belongs to Phase 2 or later.

## Non-Goals

- No new public REST endpoints beyond the Phase 0 scaffold.
- No Angular UI changes, screens, routes, or browser verification work in this phase.
- No replacement of the GNUCobol runtime or modification of legacy source files unless required to clarify authoritative behavior.
- No batch scheduler implementation, manual trigger UI, or batch admin interface.
- No migration of optional DB2, IMS, or MQ modules.
- No schema migration engine beyond a documented schema-versioning plan suitable for later implementation.
- No attempt to complete Phase 2 session APIs or user-administration flows during Phase 1.

## Design Considerations

- Preserve COBOL record semantics even when the target JSON schema is normalized for backend use.
- Prefer explicit model names and domain terminology over raw copybook field names, but keep mappings traceable in documentation.
- Keep Phase 1 documentation concise and operational; it should help later slices implement behavior, not retell the migration narrative.
- Use iteration-sized stories so Ralph or a junior developer can complete one bounded slice without mixing parser, importer, and service responsibilities.

## Technical Considerations

- All modernization artifacts for this phase belong under `output/` in accordance with repository rules.
- Money must remain precise end-to-end using `Decimal`; floats are not acceptable in parsing, storage, or domain service logic.
- JSON persistence must remain compatible with the Phase 0 atomic-write and serialization primitives.
- Concurrency protection belongs in shared storage code from Phase 0, not re-implemented in Phase 1 services.
- Import logic should reuse shared parsing/storage abstractions rather than bypassing them.
- Where GNUCobol source behavior is ambiguous, Phase 1 should document the inference and keep the behavior easy to revise later.

## Success Metrics

- A developer can trace every Phase 1 entity from copybook or flat file source to canonical JSON model without guessing field meaning.
- A fresh repository workspace can bootstrap `output/backend/store.json` from shipped seed data through one documented command.
- Seed import tests catch regressions in row counts, key relationships, or malformed-line handling deterministically.
- Later Phase 2 and Phase 3 work can call shared domain services directly instead of embedding business rules in endpoints or jobs.
- Phase 1 lands with no new public API surface, keeping the architectural cut line clean.

## Open Questions

- Authentication semantics likely need close review of the GNUCobol runtime to confirm whether password handling is plain-text, transformed, or partially implied by surrounding logic.
- Some transaction record families may need an explicit normalization decision if the flat-file runtime stores overlapping online and batch representations for similar events.
- The exact shape of job run detail payloads may need refinement once Phase 3 monitoring requirements are implemented, but Phase 1 should still define a stable minimal telemetry contract.

## Backlog Order

Recommended implementation order for this phase:

1. US-001 through US-010 to lock down source inventory, schema, record mappings, parsing helpers, and malformed-line rules.
2. US-011 through US-015 to implement seed bootstrap and prove stable imported data.
3. US-016 through US-022 to implement and document reusable domain services on top of the imported canonical store.
