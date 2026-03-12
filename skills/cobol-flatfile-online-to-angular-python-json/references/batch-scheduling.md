# Batch Scheduling and Monitoring Guidance

Use this guidance when COBOL includes non-interactive programs or paragraphs that represent periodic business processing.

## 1) Identify batch candidates

Classify a program as batch when most of these are true:

- No terminal input loop (`ACCEPT` is absent or only for current date/time).
- Processing is file-pass oriented (`READ ... UNTIL FILE-STATUS = "10"`).
- Logic emphasizes aggregate updates, posting, balancing, or roll-forward tasks.
- Program naming or messages indicate periodic runs (`EOD`, `DAYEND`, `MONTHEND`, `YEAR-END`, `BATCH`).

## 2) Build batch job contracts

For each batch program, define:

- `job_id`: stable kebab-case identifier.
- `description`: business purpose in one sentence.
- `handler`: backend callable implementing one deterministic run.
- `inputs`: optional parameters with defaults (business date, dry-run, account range).
- `outputs`: counters and artifacts (rows read/written, warnings, errors).

Expose each job through API and optionally UI monitoring routes.

## 3) Infer schedules from COBOL semantics

Infer schedule from program intent and evidence in comments/messages. Use defaults only when COBOL does not specify timing.

Recommended defaults:

- Day-end job: daily after business close.
- Week-end job: weekly on the configured week-close day.
- Month-end job: run at `00:01` on day `1` of the new month.

For month-end logic, express default cron as:

- `1 0 1 * *`

Always allow overriding inferred schedules by config.

## 4) Prevent run conflicts and duplicate effects

- Block concurrent runs for the same `job_id`.
- Persist run state transitions: `queued -> running -> succeeded/failed`.
- Record a business key or watermark to prevent duplicate posting when rerun.
- Support explicit rerun behavior with clear idempotency notes.

## 5) Monitoring model

Track run telemetry in durable storage:

- `run_id`, `job_id`, trigger source (schedule/manual), started/ended timestamps.
- Status, error summary, warnings count.
- Domain counters (records scanned, updated, skipped, rejected).
- Optional log location/reference for diagnostics.

Provide API reads for:

- current job definitions and schedules,
- recent runs per job,
- single run detail.

## 6) Test expectations

Add pytest coverage for:

- schedule inference from COBOL naming/paragraph intent,
- month-end default schedule at `00:01` on day `1`,
- conflict blocking for overlapping runs,
- run history and status reporting,
- idempotency/rerun behavior for representative jobs.
