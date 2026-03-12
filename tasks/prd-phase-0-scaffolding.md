# PRD: Phase 0 Scaffolding

## Introduction

Create the implementation foundation for the CardDemo GNUCobol modernization target: a runnable Angular frontend, a runnable FastAPI backend, the required filesystem layout under `./output`, JSON persistence primitives, and the test harness needed for later migration slices.

This phase does not migrate business behavior yet. Its job is to establish the repository structure, runtime wiring, storage primitives, and verification gates that all later domain, online, and batch slices will use.

This PRD is based on:

- [MIGRATION_PLAN.md](/Users/Oliver.Koeth/work/aws-mainframe-modernization-carddemo/MIGRATION_PLAN.md)
- the `cobol-flatfile-online-to-angular-python-json` skill guidance
- the current GNUCobol flat-file project structure under `app/`

## Goals

- Create the required Angular and FastAPI filesystem structure inside `./output` in this repository.
- Establish a complete frontend/backend development integration strategy using Angular proxying to `/api`.
- Create a minimal runnable backend with JSON-only responses and a `/health` endpoint.
- Create a minimal runnable Angular application shell with routing and a shared API client foundation.
- Introduce JSON persistence primitives using a single `store.json` plus `schedules.json`.
- Add serialization, locking, and test harness capabilities that later slices can reuse.
- Define the initial verification gates so later feature slices inherit stable tooling and conventions.

## User Stories

### US-001: Create backend filesystem scaffold
**Description:** As a developer, I want a canonical FastAPI backend directory structure under `./output/backend` so that later migration slices can add APIs, services, and jobs without redesigning the repo layout.

**Acceptance Criteria:**
- [ ] Create `output/backend/` with `app/`, `tests/`, `README.md`, `pyproject.toml`, `store.json`, and `schedules.json`
- [ ] Create backend application modules at minimum: `main.py`, `__init__.py`, `models.py`, `storage.py`, `services.py`, `jobs.py`, `scheduler.py`
- [ ] Backend file layout matches the modernization skill’s expected output structure
- [ ] Backend imports cleanly in a fresh environment
- [ ] `pytest` can discover backend tests

### US-002: Create frontend filesystem scaffold
**Description:** As a developer, I want a canonical Angular standalone application structure under `./output/frontend` so that later migration slices can add routes and feature screens without reworking the app shell.

**Acceptance Criteria:**
- [ ] Create `output/frontend/` with Angular app source, `e2e/`, `package.json`, `playwright.config.ts`, and `README.md`
- [ ] Create app shell files at minimum: `app.component.ts`, `app.component.html`, `routes.ts`, and a shared jobs placeholder component
- [ ] Angular uses standalone components rather than NgModule-based bootstrapping
- [ ] Frontend build succeeds
- [ ] Verify in browser using dev-browser skill

### US-003: Establish frontend/backend integration strategy
**Description:** As a developer, I want one clear API origin strategy so that frontend API calls work consistently in development and later slices avoid CORS drift.

**Acceptance Criteria:**
- [ ] Use Angular proxying for `/api/*` to the FastAPI backend
- [ ] Frontend API client uses `'/api'` as the base path
- [ ] Do not rely on wildcard CORS with credentials
- [ ] `npm start` or equivalent frontend dev command includes the proxy configuration
- [ ] Add a smoke check proving `/api` JSON responses parse correctly from frontend context

### US-004: Add minimal runnable backend shell
**Description:** As a developer, I want a minimal FastAPI app with stable JSON contracts so that the project can be started and tested before business features are migrated.

**Acceptance Criteria:**
- [ ] Implement `GET /health`
- [ ] All backend endpoints created in this phase return JSON with `application/json`
- [ ] Backend startup instructions are documented in `output/backend/README.md`
- [ ] Minimal configuration for local development is documented
- [ ] Backend import and startup smoke checks pass

### US-005: Add minimal runnable frontend shell
**Description:** As a developer, I want a minimal Angular shell with routing and placeholder views so that future UI slices can plug into stable navigation and shared app structure.

**Acceptance Criteria:**
- [ ] Frontend includes a root layout and route configuration
- [ ] Include placeholder routes for home and jobs surfaces needed by later slices
- [ ] App renders without runtime errors
- [ ] Shared API service foundation exists for future endpoints
- [ ] Verify in browser using dev-browser skill

### US-006: Implement JSON storage primitives
**Description:** As a developer, I want shared JSON persistence helpers so that later domain and batch slices can safely store business data, schedules, and run history.

**Acceptance Criteria:**
- [ ] `output/backend/store.json` is the single persistence file for application data
- [ ] `output/backend/schedules.json` exists for schedule declarations
- [ ] Storage layer writes atomically using temp-file plus rename
- [ ] Storage layer supports `Decimal`, `date`, and `datetime` serialization
- [ ] Storage round-trip tests verify typed values survive write and reload

### US-007: Add locking and concurrency protections
**Description:** As a developer, I want the storage layer to guard writes so that later batch and API slices do not corrupt the JSON store during concurrent updates.

**Acceptance Criteria:**
- [ ] Storage writes are protected by a documented locking strategy
- [ ] Locking behavior is implemented in shared storage code, not duplicated in feature code
- [ ] Failure behavior is deterministic and testable
- [ ] Tests cover at least one concurrent-write or lock-contention scenario

### US-008: Add backend test harness
**Description:** As a developer, I want shared pytest fixtures and smoke tests so that later slices can add tests without rebuilding the test foundation.

**Acceptance Criteria:**
- [ ] Add pytest configuration and baseline tests under `output/backend/tests/`
- [ ] Provide fixtures for disposable `store.json` and `schedules.json`
- [ ] Add tests for storage round-trip and backend import
- [ ] Add tests that confirm JSON responses for health and future placeholder endpoints

### US-009: Add frontend E2E and build harness
**Description:** As a developer, I want the frontend build and Playwright harness in place so that later UI slices can prove browser behavior from the start.

**Acceptance Criteria:**
- [ ] Add Playwright configuration under `output/frontend/`
- [ ] Add a baseline E2E smoke test structure under `output/frontend/e2e/`
- [ ] Add a frontend build command suitable for CI
- [ ] Add a browser smoke test that confirms `/jobs`, `/accounts`, and `/transactions` API responses parse as JSON from the frontend context
- [ ] Verify in browser using dev-browser skill

### US-010: Document the scaffold for later slices
**Description:** As a developer or autonomous agent, I want the repository conventions documented so that future slices can extend the scaffold consistently.

**Acceptance Criteria:**
- [ ] `output/backend/README.md` documents startup, testing, and storage conventions
- [ ] `output/frontend/README.md` documents startup, proxying, build, and test conventions
- [ ] Root-level docs identify this phase as scaffolding only, not business migration
- [ ] Documentation names the out-of-scope items for this phase

## Functional Requirements

1. FR-1: The system must create an `output/backend/` directory that contains the FastAPI application code, tests, `store.json`, and `schedules.json`.
2. FR-2: The system must create an `output/frontend/` directory that contains an Angular standalone application, E2E test folder, package manifest, and Playwright configuration.
3. FR-3: The backend must expose `GET /health` and return valid JSON with `application/json`.
4. FR-4: The frontend must use Angular proxying so frontend API traffic is sent to `/api/*` during development.
5. FR-5: The frontend API layer must use `'/api'` as the base path for backend communication.
6. FR-6: The phase must not introduce business-domain endpoints beyond scaffolding and placeholder smoke-test surfaces.
7. FR-7: The backend persistence layer must use `output/backend/store.json` as the single application data file.
8. FR-8: The backend must create and use `output/backend/schedules.json` for schedule declarations, even though batch jobs are out of scope for this phase.
9. FR-9: The persistence layer must serialize and deserialize `Decimal`, `date`, and `datetime` values.
10. FR-10: The persistence layer must write atomically using a temp-file-and-rename pattern.
11. FR-11: The persistence layer must apply a shared locking strategy to protect writes.
12. FR-12: The backend test suite must include storage round-trip tests and backend import smoke tests.
13. FR-13: The frontend test setup must include Playwright and at least one baseline smoke test.
14. FR-14: The frontend smoke coverage must confirm that `/jobs`, `/accounts`, and `/transactions` can be requested from frontend context and parsed as JSON.
15. FR-15: The scaffold must define route placeholders for later feature work, including a jobs surface.
16. FR-16: The phase must document backend and frontend local startup, build, and test commands.
17. FR-17: The scaffold must be implementation-ready for later slices without changing the chosen proxy strategy.
18. FR-18: The filesystem created in this phase must align with the modernization skill’s expected structure under `output/`, including `output/backend/`, `output/frontend/`, and `output/docs/`.

## Non-Goals

- No migration of domain entities from COBOL copybooks into full business models yet.
- No customer, account, card, transaction, report, or user-management business APIs.
- No sign-in, authorization, or session behavior.
- No batch job implementations.
- No batch admin UI beyond placeholder shell/routes.
- No migration of optional DB2, IMS, or MQ modules.
- No replacement of the existing GNUCobol runtime in this phase.
- No production deployment automation beyond local development/build/test setup.

## Design Considerations

- Preserve the repo’s existing modernization intent and avoid mixing temporary scaffolding patterns with future business architecture.
- Use Angular standalone components and reactive-form-ready structure from the start.
- Keep route naming modern and domain-oriented rather than copying COBOL transaction names directly.
- Include a jobs placeholder early because later phases require a batch admin UI and monitoring surface.

## Technical Considerations

- Source of truth for later business behavior remains the current GNUCobol flat-file runtime, but this phase should not yet encode domain logic.
- The storage layer must be reusable by both interactive APIs and future schedulable batch handlers.
- JSON parsing and response contracts matter in this phase because the skill requires cross-stack validation from the beginning.
- The filesystem structure should follow the skill’s reference layout closely so later PRDs can assume stable paths.
- The scaffold should be compatible with pytest for backend verification and Playwright for frontend verification.
- If placeholder `/jobs`, `/accounts`, or `/transactions` endpoints are needed for smoke tests, they must return valid JSON and be clearly marked as scaffolding-only contracts.

## Success Metrics

- A new developer or Ralph agent can start from this repo and immediately see canonical `output/backend/` and `output/frontend/` workspaces.
- Backend import, pytest discovery, frontend build, and Playwright setup all succeed without requiring business logic to exist.
- Frontend-to-backend development requests use a single `/api` proxy strategy with no ad hoc CORS workarounds.
- Storage primitives are in place before any domain slice starts, avoiding later refactors of persistence mechanics.

## Open Questions

- Should placeholder `/jobs`, `/accounts`, and `/transactions` endpoints return empty arrays/objects, or should they read from a bootstrapped empty store abstraction even in this phase?
- Which exact local commands should be standardized for frontend and backend startup in this repository: plain framework defaults or repo-specific wrapper scripts?
- Should this phase also create a minimal root-level task runner or CI config, or leave CI wiring to a later hardening phase?
