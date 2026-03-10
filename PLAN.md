# Modernization Plan

## Goal

Remove required CICS dependencies from the base CardDemo application in small, runnable slices while preserving business behavior and moving the active runtime to GNUCobol-compatible, flat-file execution.

This plan assumes:

- Flat files under `app/data/ASCII` are the permanent storage model for the GNUCobol runtime.
- Batch programs remain COBOL and are migrated to consume the same flat-file storage model.
- Online flows are migrated from CICS/BMS screen programs to plain GNUCobol console or other non-CICS entrypoints one slice at a time.
- Each slice must leave the repository in a compilable and testable state.

## Current State

Completed runtime work:

- `COSGN00C` is now a GNUCobol console sign-on entrypoint.
- `COADM01C` is now a GNUCobol console admin menu.
- `COMEN01C` is now a GNUCobol regular-user menu shell.
- `COACTVWC` is now a GNUCobol file-backed account inquiry flow.
- `COACTUPC` is now a GNUCobol file-backed account/customer update flow.
- `GCUSRSEC` provides file-backed user security CRUD against `app/data/ASCII/usrsec.dat`.
- `COUSR00C`, `COUSR01C`, `COUSR02C`, and `COUSR03C` are now non-CICS wrapper entrypoints over the file-backed security runtime.

Phase 1 status:

- Slices 1 through 12 are complete.
- The active GNUCobol runtime covers the base online application flows without required CICS dependencies.

Remaining CICS-adjacent dependencies:

- Legacy CICS/BMS sources still remain in the repository for the original mainframe runtime.
- Batch report execution still needs a GNUCobol-native path.
- Batch transaction and account-maintenance flows still need migration to the flat-file runtime.
- Local data initialization and reset are still documented mostly in mainframe/JCL terms.

## Strategy

Port by vertical slice, not by statement type. Each slice should:

1. Replace one user-visible flow end-to-end.
2. Reuse or create a non-CICS file access layer for the involved datasets.
3. Replace BMS input/output with a plain interaction contract.
4. Preserve the data layouts in the existing copybooks where practical.
5. Add a build entry and a smoke test for the slice.

## Cross-Cutting Workstreams

These workstreams support all slices and should be expanded incrementally instead of built all at once.

### 1. Runtime Foundation

Deliverables:

- A shared GNUCobol runtime pattern for:
  - program dispatch
  - session/common state
  - input validation
  - formatted prompts and messages
- A dataset path convention using environment variables with sensible defaults under `app/data/ASCII/`
- A repeatable build script for the non-CICS binaries

Acceptance:

- New online modules can compile without `EXEC CICS`, `DFHAID`, or `DFHBMSCA`.
- File locations can be changed without source edits.

### 2. File Access Adapters

Deliverables:

- Reusable COBOL modules or local patterns for:
  - keyed read
  - sequential browse
  - insert
  - update
  - delete
- One adapter pattern per logical dataset:
  - `USRSEC`
  - `CUSTFILE`
  - `ACCTFILE`
  - `XREFFILE`
  - `CARDFILE`
  - `TRANFILE`
  - supporting lookup files such as `DISCGRP`, `TRANCATG`, `TRANTYPE`, `TCATBALF`

Acceptance:

- Each ported slice accesses data without `EXEC CICS READ/WRITE/REWRITE/DELETE`.
- Browse-heavy flows no longer use `STARTBR/READNEXT/READPREV/ENDBR`.

### 3. Verification Harness

Deliverables:

- One smoke script per migrated slice
- Golden input/output notes for key flows
- Data reset instructions for file-backed test runs

Acceptance:

- Every completed slice has at least one scripted happy-path run.

## Phase 0: Bootstrap

### Slice 0: Stabilize The New Entry Path

Scope:

- Keep the current GNUCobol sign-on/admin path as the base entrypoint.
- Normalize the new `usrsec.dat` file format and document it.
- Add a short runtime README for how to build and run the non-CICS path.

Programs:

- `COSGN00C`
- `COADM01C`
- `GCUSRSEC`

Exit criteria:

- Clean build from script
- Smoke run for admin login and user list
- File format for `USRSEC` documented

Status:

- Completed

## Phase 1: Online Base-App CICS Removal

Scope:

- Remove required CICS/BMS dependencies from the active online base-app path.
- Replace the user-visible CICS flows with GNUCobol console flows over flat files.
- Isolate the remaining legacy CICS sources as repository artifacts, not runtime requirements.

### Slice 1: Security Admin Completion

Scope:

- Retire the remaining CICS user admin programs by either:
  - folding their behavior fully into `GCUSRSEC`, or
  - replacing them with non-CICS equivalents
- Remove `COUSR00C`, `COUSR01C`, `COUSR02C`, `COUSR03C` from the active non-CICS path

Programs:

- `COUSR00C`
- `COUSR01C`
- `COUSR02C`
- `COUSR03C`

Dependencies removed:

- BMS user maintenance screens
- CICS user file CRUD calls
- CICS menu navigation back to admin menu

Exit criteria:

- List/add/update/delete user behavior available without CICS
- All user security admin functions reachable from `COADM01C`

Status:

- Completed

### Slice 2: Regular User Main Menu

Scope:

- Replace `COMEN01C` with a non-CICS menu shell that dispatches to migrated user flows
- Mark not-yet-ported flows explicitly instead of attempting CICS transfer

Programs:

- `COMEN01C`

Dependencies removed:

- `EXEC CICS RECEIVE/SEND/RETURN/XCTL`
- BMS option-entry screen handling

Exit criteria:

- A GNUCobol regular-user menu exists
- Menu can route to migrated slices and report unavailable slices cleanly

Status:

- Completed

### Slice 3: Account View

Scope:

- Port account inquiry from `COACTVWC`
- Replace CICS keyed reads on account, customer, and xref files with file-backed keyed access
- Replace screen rendering with a plain output view

Programs:

- `COACTVWC`

Datasets:

- `ACCTFILE`
- `CUSTFILE`
- `XREFFILE`

Dependencies removed:

- CICS screen display/input
- CICS file reads for inquiry

Exit criteria:

- User can view an account by account ID or related identifier without CICS
- Output includes the same core business fields as the old screen

Status:

- Completed

### Slice 4: Account Update

Scope:

- Port account modification flow from `COACTUPC`
- Implement optimistic read/update behavior against file-backed records
- Preserve field validations and cross-file effects

Programs:

- `COACTUPC`

Datasets:

- `ACCTFILE`
- `CUSTFILE`
- `XREFFILE`

Dependencies removed:

- CICS `READ`/`REWRITE`
- BMS form state management

Exit criteria:

- Account update works end-to-end without CICS
- Modified records persist correctly in file-backed storage

Status:

- Completed

### Slice 5: Credit Card List

Scope:

- Port browse/list behavior from `COCRDLIC`
- Replace CICS browse APIs with sequential/indexed file traversal logic
- Support forward/backward page navigation in a non-CICS form

Programs:

- `COCRDLIC`

Datasets:

- `CARDFILE`
- `XREFFILE`
- possibly `ACCTFILE`

Dependencies removed:

- `STARTBR`
- `READNEXT`
- `READPREV`
- `ENDBR`

Exit criteria:

- Card listing works without CICS browse APIs
- Pagination or next/previous navigation exists in the new runtime

Status:

- Completed

### Slice 6: Credit Card View And Update

Scope:

- Port `COCRDSLC` and `COCRDUPC`
- Reuse list slice data access where possible
- Preserve card validation and any linked account/customer lookups

Programs:

- `COCRDSLC`
- `COCRDUPC`

Datasets:

- `CARDFILE`
- `XREFFILE`
- `ACCTFILE`

Exit criteria:

- Card detail inquiry works without CICS
- Card update works and persists file changes

Status:

- Completed

### Slice 7: Transaction List

Scope:

- Port `COTRN00C`
- Replace transaction browse behavior with sequential/keyed file traversal
- Preserve filtering and next/previous semantics where relevant

Programs:

- `COTRN00C`

Datasets:

- `TRANFILE`

Dependencies removed:

- CICS browse APIs
- BMS list rendering

Exit criteria:

- Transaction list works without CICS

Status:

- Completed

### Slice 8: Transaction View

Scope:

- Port `COTRN01C`
- Replace single-record transaction inquiry with direct file-backed lookup

Programs:

- `COTRN01C`

Datasets:

- `TRANFILE`

Exit criteria:

- Transaction detail view works without CICS

Status:

- Completed

### Slice 9: Transaction Add

Scope:

- Port `COTRN02C`
- Preserve transaction creation rules and related file lookups
- Ensure newly created transactions are visible to transaction list/view and downstream batch flows

Programs:

- `COTRN02C`

Datasets:

- `TRANFILE`
- `XREFFILE`
- `ACCTFILE`

Exit criteria:

- User can add a transaction without CICS
- Data is compatible with existing batch programs

Status:

- Completed

### Slice 10: Bill Payment

Scope:

- Port `COBIL00C`
- Preserve bill payment logic and transaction/account updates
- Reuse transaction creation and account update logic from earlier slices

Programs:

- `COBIL00C`

Datasets:

- `ACCTFILE`
- `TRANFILE`
- related lookup files used by current logic

Exit criteria:

- Bill payment runs without CICS
- Resulting account and transaction records are correct

Status:

- Completed

### Slice 11: Transaction Reports Launcher

Scope:

- Port `CORPT00C`
- Replace `WRITEQ TD`/CICS queue behavior with direct invocation or a file-backed request artifact
- Keep the batch report generation path intact

Programs:

- `CORPT00C`
- interacts with `CBTRN03C`

Dependencies removed:

- `EXEC CICS WRITEQ TD`
- CICS-only report-request submission flow

Exit criteria:

- Report request can be created without CICS
- Existing batch report logic still runs successfully

Status:

- Completed

### Slice 12: Batch/Online Boundary Cleanup

Scope:

- Review all remaining base-app CICS assumptions in shared copybooks and wrappers
- Remove dead BMS/CICS references from the migrated path
- Split ported runtime code from legacy CICS code clearly

Targets:

- Shared copybooks or data structures that only existed for CICS screen handling
- Build scripts and docs

Exit criteria:

- A documented non-CICS base-app runtime exists
- No remaining required CICS dependency in the migrated slices

Status:

- Completed

## Phase 2: Batch And Storage-Native Completion

Scope:

- Finish the base-app migration beyond the online runtime.
- Keep flat files as the permanent storage model for both online and batch flows.
- Remove the remaining practical dependence on mainframe dataset/JCL setup for the migrated base application.

### Slice 13: Transaction Report Batch Migration

Scope:

- Port `CBTRN03C` to run directly on the ASCII flat files used by the GNUCobol runtime.
- Consume the file-backed request artifacts created by `CORPT00C`, especially `dateparm.txt`.
- Produce report output in a local file-backed format instead of relying on mainframe DD allocation and GDG conventions.

Programs:

- `CBTRN03C`
- interacts with `CORPT00C`

Datasets:

- `dailytran.txt`
- `cardxref.txt`
- `trantype.txt`
- `trancatg.txt`
- `dateparm.txt`
- local report output file

Dependencies removed:

- Mainframe DD-only report launch assumptions
- Legacy `TRANREPT`/`DATEPARM` allocation assumptions in the active GNUCobol path

Exit criteria:

- The transaction report batch can run locally under GNUCobol.
- It consumes the file-backed date parameter contract written by `CORPT00C`.
- It produces a readable local report artifact without mainframe queue or DD setup.

Status:

- Completed

### Slice 14: Batch Transaction And Account Maintenance Migration

Scope:

- Port the remaining batch transaction and account-maintenance flows to the same flat-file runtime.
- Migrate transaction posting and any required account or balance update jobs that still assume VSAM-style or JCL-only execution.
- Keep compatibility with the online transaction add, bill payment, and reporting flows.

Programs:

- `CBTRN02C`
- related batch maintenance programs as needed

Datasets:

- `dailytran.txt`
- `acctdata.txt`
- `cardxref.txt`
- `tcatbal.txt`
- supporting lookup files

Dependencies removed:

- Mainframe-only batch execution assumptions for transaction posting
- Remaining VSAM-style storage assumptions in the active base-app batch path

Exit criteria:

- The remaining base-app transaction/account batch flows run locally under GNUCobol.
- Online and batch flows operate on the same flat-file storage without format drift.
- Required business updates remain consistent across online and batch processing.

Status:

- Completed

### Slice 15: Local Data Initialization And Reset

Scope:

- Replace the JCL-oriented setup story for the migrated base app with local GNUCobol-native data initialization and reset workflows.
- Add repeatable scripts or COBOL utilities to create, reset, and seed the flat-file runtime datasets.
- Document the local initialization path as the primary setup for the GNUCobol runtime.

Targets:

- data initialization utilities or scripts
- sample-data reset workflow
- runtime documentation

Dependencies removed:

- JCL-first setup assumptions for the migrated base-app runtime
- Manual mainframe-style data preparation for local GNUCobol testing

Exit criteria:

- A developer can initialize or reset the GNUCobol runtime data locally without mainframe JCL.
- The initialization process produces the flat files required by both online and migrated batch flows.
- Runtime docs clearly describe local setup, reset, and verification.

Status:

- Completed

## Slice Ordering Rationale

Recommended implementation order:

1. Slice 0
2. Phase 1, Slice 1
3. Phase 1, Slice 2
4. Phase 1, Slice 3
5. Phase 1, Slice 4
6. Phase 1, Slice 5
7. Phase 1, Slice 6
8. Phase 1, Slice 7
9. Phase 1, Slice 8
10. Phase 1, Slice 9
11. Phase 1, Slice 10
12. Phase 1, Slice 11
13. Phase 1, Slice 12
14. Phase 2, Slice 13
15. Phase 2, Slice 14
16. Phase 2, Slice 15

This order reduces risk because:

- Security and menus become stable first.
- Account and card flows establish the reusable file access patterns.
- Transaction flows then reuse that infrastructure.
- Report launching is delayed until the online-to-batch boundary is cleaner.
- Batch migration starts only after the online flat-file contracts are stable.
- Local initialization is last so it can target the final flat-file dataset set, not an intermediate one.

## Definition Of Done Per Slice

A slice is done only when all of the following are true:

- The relevant program path compiles with GNUCobol.
- The migrated path has no required `EXEC CICS` statements.
- The slice runs against file-backed storage in the workspace.
- At least one smoke test demonstrates the happy path.
- The old CICS behavior for that slice is either removed from the active runtime or explicitly isolated as legacy-only.

## Risks

- Some online programs mix UI flow and file logic tightly, so extraction may require more restructuring than expected.
- VSAM browse semantics may not map cleanly to naive sequential-file replacements.
- Some shared copybooks may encode assumptions from BMS or COMMAREA-era navigation.
- There may be hidden dependencies on response-code handling such as `DFHRESP(...)`.

## Recommended Next Step

Phase 2 is complete for the migrated base application. The next work, if needed, is outside this plan: regression automation, optional-module migration, or a UI/runtime modernization beyond GNUCobol console execution.
