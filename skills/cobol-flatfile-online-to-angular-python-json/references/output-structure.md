# Expected Output Structure

Produce a runnable repository with this minimum tree:

```
output/
  backend/
    app/
      __init__.py
      main.py
      models.py
      storage.py
      services.py
      jobs.py
      scheduler.py
    tests/
      test_storage.py
      test_api.py
      test_jobs.py
    store.json
    schedules.json
    pyproject.toml
    README.md
  frontend/
    src/
      app/
        app.component.ts
        app.component.html
        routes.ts
        jobs.component.ts
    e2e/
      account-flows.spec.ts
      jobs-flows.spec.ts
    package.json
    playwright.config.ts
    README.md
  docs/
    mapping.md
    record-layouts.md
    job-schedules.md (if batch jobs exist)
    unsupported-features.md (only if needed)
```

Notes:

- Add or rename files if COBOL flows require it, but keep `backend/`, `frontend/`, and `docs/`.
- `store.json` must be the single persistence file.
- `schedules.json` stores schedule declarations and can be overridden by deployment config.
- `docs/mapping.md` must map COBOL paragraphs/files to REST endpoints, UI routes, and batch jobs.
