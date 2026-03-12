# API Baseline and Extension Rules

## Baseline endpoints

Use these endpoints as the default foundation. Extend only when COBOL logic indicates additional actions.

- `GET /health`
- `GET /accounts`
- `POST /accounts`
- `GET /accounts/{id}`
- `PUT /accounts/{id}`
- `DELETE /accounts/{id}`
- `POST /accounts/{id}/deposit`
- `POST /accounts/{id}/withdraw`
- `GET /accounts/{id}/statement`
- `POST /accounts/{id}/apply-interest`
- `GET /transactions`
- `POST /transactions`
- `GET /transactions/{id}`

If batch COBOL programs are detected, include this baseline job control surface:

- `GET /jobs`
- `GET /jobs/{job_id}`
- `POST /jobs/{job_id}/run`
- `GET /jobs/{job_id}/runs`
- `GET /jobs/runs/{run_id}`

## Extension rules

1. Add endpoints only if a COBOL menu option or paragraph describes a unique action.
2. Prefer `POST /resource/{id}/action` for mutating operations.
3. Prefer `GET /resource/{id}` for read-only details.
4. For batch flows, expose job-level controls and run-level monitoring with immutable run records.
5. Use modernized UI route naming; keep REST paths concise and domain-oriented.

## Defaults

- Money handled as Decimal.
- Use skill defaults only when COBOL is silent.
