from __future__ import annotations

from datetime import datetime

import pytest

from app.domain.job_telemetry import (
    JobTelemetryCreateRequest,
    JobTelemetryDetailCreateRequest,
    JobTelemetryService,
    JobTelemetryStoreConsistencyError,
    JobTelemetryValidationError,
)
from app.domain.transactions_activity import JobRunDetailLevel, JobRunStatus
from app.models import default_store_document
from app.storage import read_store, write_store


def test_create_start_complete_job_run_persists_header_and_detail(storage_paths) -> None:
    service = JobTelemetryService(
        storage_paths,
        now_provider=lambda: datetime(2026, 3, 14, 9, 30, 45),
    )

    created = service.create_job_run(
        JobTelemetryCreateRequest(
            job_run_id=" nightly-20260314-01 ",
            job_name=" nightly-settlement ",
            summary=" queued by scheduler ",
        )
    )
    started = service.start_job_run(
        "nightly-20260314-01",
        started_at=datetime(2026, 3, 14, 9, 31, 0),
        summary="Importing pending transactions",
    )
    detail = service.append_job_run_detail(
        "nightly-20260314-01",
        JobTelemetryDetailCreateRequest(
            level=JobRunDetailLevel.INFO,
            message="Imported pending transactions",
            context={"phase": "import"},
        ),
    )
    completed = service.complete_job_run(
        "nightly-20260314-01",
        ended_at=datetime(2026, 3, 14, 9, 45, 0),
        summary="Completed successfully",
    )
    payload = read_store(storage_paths)

    assert created.job_run_id == "nightly-20260314-01"
    assert created.job_name == "nightly-settlement"
    assert created.status is JobRunStatus.PENDING
    assert created.started_at is None
    assert created.ended_at is None
    assert created.summary == "queued by scheduler"

    assert started.status is JobRunStatus.RUNNING
    assert started.started_at == datetime(2026, 3, 14, 9, 31, 0)
    assert started.ended_at is None
    assert started.summary == "Importing pending transactions"

    assert detail.sequence_number == 1
    assert detail.recorded_at == datetime(2026, 3, 14, 9, 30, 45)
    assert detail.context == {"phase": "import"}

    assert completed.status is JobRunStatus.SUCCEEDED
    assert completed.started_at == datetime(2026, 3, 14, 9, 31, 0)
    assert completed.ended_at == datetime(2026, 3, 14, 9, 45, 0)
    assert completed.summary == "Completed successfully"
    assert payload["operations"]["job_runs"] == [completed.model_dump(mode="python")]
    assert payload["operations"]["job_run_details"] == [
        detail.model_dump(mode="python")
    ]


def test_fail_job_run_allows_pending_or_running_failure(storage_paths) -> None:
    service = JobTelemetryService(
        storage_paths,
        now_provider=lambda: datetime(2026, 3, 14, 10, 0, 0),
    )

    service.create_job_run(
        JobTelemetryCreateRequest(
            job_run_id="nightly-20260314-02",
            job_name="nightly-settlement",
        )
    )
    failed_before_start = service.fail_job_run(
        "nightly-20260314-02",
        summary="Configuration missing",
    )

    service.create_job_run(
        JobTelemetryCreateRequest(
            job_run_id="nightly-20260314-03",
            job_name="nightly-settlement",
        )
    )
    service.start_job_run(
        "nightly-20260314-03",
        started_at=datetime(2026, 3, 14, 10, 5, 0),
    )
    failed_after_start = service.fail_job_run(
        "nightly-20260314-03",
        ended_at=datetime(2026, 3, 14, 10, 6, 0),
        summary="Posting step failed",
    )

    assert failed_before_start.status is JobRunStatus.FAILED
    assert failed_before_start.started_at is None
    assert failed_before_start.ended_at == datetime(2026, 3, 14, 10, 0, 0)
    assert failed_before_start.summary == "Configuration missing"

    assert failed_after_start.status is JobRunStatus.FAILED
    assert failed_after_start.started_at == datetime(2026, 3, 14, 10, 5, 0)
    assert failed_after_start.ended_at == datetime(2026, 3, 14, 10, 6, 0)
    assert failed_after_start.summary == "Posting step failed"


def test_job_telemetry_service_rejects_duplicate_ids_and_invalid_transitions(
    storage_paths,
) -> None:
    service = JobTelemetryService(storage_paths)
    service.create_job_run(
        JobTelemetryCreateRequest(
            job_run_id="nightly-20260314-04",
            job_name="nightly-settlement",
        )
    )

    with pytest.raises(
        JobTelemetryValidationError,
        match="Job run ID 'nightly-20260314-04' already exists.",
    ):
        service.create_job_run(
            JobTelemetryCreateRequest(
                job_run_id="nightly-20260314-04",
                job_name="nightly-settlement",
            )
        )

    with pytest.raises(
        JobTelemetryValidationError,
        match="Job run status cannot transition from 'pending' to 'succeeded'.",
    ):
        service.complete_job_run("nightly-20260314-04")

    service.start_job_run("nightly-20260314-04")
    service.complete_job_run("nightly-20260314-04")

    with pytest.raises(
        JobTelemetryValidationError,
        match="Job run status cannot transition from 'succeeded' to 'failed'.",
    ):
        service.fail_job_run("nightly-20260314-04")


def test_job_telemetry_service_rejects_invalid_or_dangling_store_rows(
    storage_paths,
) -> None:
    payload = default_store_document()
    payload["operations"]["job_runs"] = [
        {
            "job_run_id": "nightly-20260314-05",
            "job_name": "nightly-settlement",
            "status": "pending",
            "started_at": None,
            "ended_at": None,
            "summary": None,
        }
    ]
    payload["operations"]["job_run_details"] = [
        {
            "job_run_id": "missing-run",
            "sequence_number": 1,
            "recorded_at": datetime(2026, 3, 14, 10, 30, 0),
            "level": "error",
            "message": "Dangling detail",
            "context": None,
        }
    ]
    write_store(storage_paths, payload)

    service = JobTelemetryService(storage_paths)

    with pytest.raises(
        JobTelemetryStoreConsistencyError,
        match=(
            "Store operations.job_run_details row at index 1 references unknown "
            "job_run_id 'missing-run'."
        ),
    ):
        service.start_job_run("nightly-20260314-05")
