"""Shared job telemetry write service for persisted run history."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.domain.transactions_activity import (
    JobRunDetailLevel,
    JobRunDetailRecord,
    JobRunRecord,
    JobRunStatus,
)
from app.models import StoragePaths
from app.storage import read_store, write_store


class JobTelemetryServiceError(RuntimeError):
    """Base error for job telemetry persistence failures."""


class JobTelemetryValidationError(JobTelemetryServiceError):
    """Raised when a requested telemetry mutation is invalid."""


class JobTelemetryNotFoundError(JobTelemetryServiceError):
    """Raised when a requested job run does not exist."""


class JobTelemetryStoreConsistencyError(JobTelemetryServiceError):
    """Raised when persisted telemetry rows are malformed or ambiguous."""


class JobTelemetryCreateRequest(BaseModel):
    """Inputs for creating a pending job-run header."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    job_run_id: str = Field(min_length=1, max_length=64)
    job_name: str = Field(min_length=1, max_length=100)
    summary: str | None = Field(default=None, max_length=500)


class JobTelemetryDetailCreateRequest(BaseModel):
    """Inputs for appending one job-run detail event."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    level: JobRunDetailLevel
    message: str = Field(min_length=1, max_length=500)
    context: dict[str, Any] | None = None
    recorded_at: datetime | None = None


class JobTelemetryService:
    """Storage-backed job-run and detail write behavior for Phase 1 telemetry."""

    def __init__(
        self,
        paths: StoragePaths,
        *,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._paths = paths
        self._now_provider = now_provider or datetime.now

    def create_job_run(
        self,
        request: JobTelemetryCreateRequest,
    ) -> JobRunRecord:
        """Append one new pending job run to `operations.job_runs`."""
        store = read_store(self._paths)
        job_runs = _validate_collection(
            store["operations"]["job_runs"],
            JobRunRecord,
            collection_name="operations.job_runs",
        )
        details = _validate_collection(
            store["operations"]["job_run_details"],
            JobRunDetailRecord,
            collection_name="operations.job_run_details",
        )
        _validate_detail_references(details, job_runs)
        _assert_unique_job_run_id(job_runs, request.job_run_id)

        created_run = JobRunRecord(
            job_run_id=request.job_run_id.strip(),
            job_name=request.job_name.strip(),
            status=JobRunStatus.PENDING,
            started_at=None,
            ended_at=None,
            summary=_normalize_optional_summary(request.summary),
        )

        store["operations"]["job_runs"] = [
            *[job_run.model_dump(mode="python") for job_run in job_runs],
            created_run.model_dump(mode="python"),
        ]
        write_store(self._paths, store)
        return created_run

    def start_job_run(
        self,
        job_run_id: str,
        *,
        started_at: datetime | None = None,
        summary: str | None = None,
    ) -> JobRunRecord:
        """Transition one persisted job run from pending to running."""
        return self._update_job_run(
            job_run_id,
            next_status=JobRunStatus.RUNNING,
            started_at=started_at,
            ended_at=None,
            summary=summary,
        )

    def complete_job_run(
        self,
        job_run_id: str,
        *,
        ended_at: datetime | None = None,
        summary: str | None = None,
    ) -> JobRunRecord:
        """Transition one persisted job run from running to succeeded."""
        return self._update_job_run(
            job_run_id,
            next_status=JobRunStatus.SUCCEEDED,
            started_at=None,
            ended_at=ended_at,
            summary=summary,
        )

    def fail_job_run(
        self,
        job_run_id: str,
        *,
        ended_at: datetime | None = None,
        summary: str | None = None,
    ) -> JobRunRecord:
        """Transition one persisted job run from pending/running to failed."""
        return self._update_job_run(
            job_run_id,
            next_status=JobRunStatus.FAILED,
            started_at=None,
            ended_at=ended_at,
            summary=summary,
        )

    def append_job_run_detail(
        self,
        job_run_id: str,
        request: JobTelemetryDetailCreateRequest,
    ) -> JobRunDetailRecord:
        """Append one detail record in persisted order for an existing run."""
        store = read_store(self._paths)
        job_runs = _validate_collection(
            store["operations"]["job_runs"],
            JobRunRecord,
            collection_name="operations.job_runs",
        )
        details = _validate_collection(
            store["operations"]["job_run_details"],
            JobRunDetailRecord,
            collection_name="operations.job_run_details",
        )
        normalized_job_run_id = _normalize_job_run_id(job_run_id)
        _validate_detail_references(details, job_runs)
        _find_job_run(job_runs, normalized_job_run_id)

        next_sequence = 1
        for detail in details:
            if detail.job_run_id == normalized_job_run_id:
                next_sequence = detail.sequence_number + 1

        created_detail = JobRunDetailRecord(
            job_run_id=normalized_job_run_id,
            sequence_number=next_sequence,
            recorded_at=(request.recorded_at or self._now_provider()).replace(
                microsecond=0
            ),
            level=request.level,
            message=request.message.strip(),
            context=request.context,
        )

        store["operations"]["job_run_details"] = [
            *[detail.model_dump(mode="python") for detail in details],
            created_detail.model_dump(mode="python"),
        ]
        write_store(self._paths, store)
        return created_detail

    def _update_job_run(
        self,
        job_run_id: str,
        *,
        next_status: JobRunStatus,
        started_at: datetime | None,
        ended_at: datetime | None,
        summary: str | None,
    ) -> JobRunRecord:
        store = read_store(self._paths)
        job_runs = _validate_collection(
            store["operations"]["job_runs"],
            JobRunRecord,
            collection_name="operations.job_runs",
        )
        details = _validate_collection(
            store["operations"]["job_run_details"],
            JobRunDetailRecord,
            collection_name="operations.job_run_details",
        )
        normalized_job_run_id = _normalize_job_run_id(job_run_id)
        current_run = _find_job_run(job_runs, normalized_job_run_id)
        _validate_detail_references(details, job_runs)

        _assert_transition_allowed(current_run.status, next_status)
        timestamp = self._now_provider().replace(microsecond=0)

        resolved_started_at = current_run.started_at
        resolved_ended_at = current_run.ended_at

        if next_status is JobRunStatus.RUNNING:
            resolved_started_at = (started_at or timestamp).replace(microsecond=0)
            resolved_ended_at = None
        elif next_status is JobRunStatus.SUCCEEDED:
            if current_run.started_at is None:
                raise JobTelemetryValidationError(
                    f"Job run {normalized_job_run_id!r} cannot succeed before it starts."
                )
            resolved_ended_at = (ended_at or timestamp).replace(microsecond=0)
        elif next_status is JobRunStatus.FAILED:
            if current_run.status is JobRunStatus.PENDING:
                resolved_started_at = current_run.started_at
            resolved_ended_at = (ended_at or timestamp).replace(microsecond=0)

        if (
            resolved_started_at is not None
            and resolved_ended_at is not None
            and resolved_ended_at < resolved_started_at
        ):
            raise JobTelemetryValidationError(
                "Job run end time must not be before its start time."
            )

        updated_run = JobRunRecord(
            job_run_id=current_run.job_run_id,
            job_name=current_run.job_name,
            status=next_status,
            started_at=resolved_started_at,
            ended_at=resolved_ended_at,
            summary=(
                _normalize_optional_summary(summary)
                if summary is not None
                else current_run.summary
            ),
        )

        store["operations"]["job_runs"] = [
            updated_run.model_dump(mode="python")
            if job_run.job_run_id == normalized_job_run_id
            else job_run.model_dump(mode="python")
            for job_run in job_runs
        ]
        write_store(self._paths, store)
        return updated_run


def _validate_collection[T: BaseModel](
    raw_collection: list[dict[str, object]],
    model_type: type[T],
    *,
    collection_name: str,
) -> list[T]:
    records: list[T] = []
    for index, raw_record in enumerate(raw_collection, start=1):
        try:
            records.append(model_type.model_validate(raw_record))
        except ValidationError as error:
            raise JobTelemetryStoreConsistencyError(
                f"Store {collection_name} row at index {index} is invalid: {error}"
            ) from error
    return records


def _normalize_job_run_id(value: str) -> str:
    normalized = value.strip()
    if normalized == "":
        raise JobTelemetryValidationError("Job run ID cannot be empty.")
    if len(normalized) > 64:
        raise JobTelemetryValidationError("Job run ID must be 64 characters or fewer.")
    return normalized


def _normalize_optional_summary(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _assert_unique_job_run_id(
    job_runs: list[JobRunRecord],
    job_run_id: str,
) -> None:
    normalized_job_run_id = _normalize_job_run_id(job_run_id)
    matches = [job_run for job_run in job_runs if job_run.job_run_id == normalized_job_run_id]
    if len(matches) > 1:
        raise JobTelemetryStoreConsistencyError(
            f"Store contains multiple job runs with ID {normalized_job_run_id!r}."
        )
    if matches:
        raise JobTelemetryValidationError(
            f"Job run ID {normalized_job_run_id!r} already exists."
        )


def _find_job_run(job_runs: list[JobRunRecord], job_run_id: str) -> JobRunRecord:
    matches = [job_run for job_run in job_runs if job_run.job_run_id == job_run_id]
    if len(matches) > 1:
        raise JobTelemetryStoreConsistencyError(
            f"Store contains multiple job runs with ID {job_run_id!r}."
        )
    if not matches:
        raise JobTelemetryNotFoundError(f"Job run {job_run_id!r} was not found.")
    return matches[0]


def _validate_detail_references(
    details: list[JobRunDetailRecord],
    job_runs: list[JobRunRecord],
) -> None:
    valid_ids = {job_run.job_run_id for job_run in job_runs}
    for index, detail in enumerate(details, start=1):
        if detail.job_run_id not in valid_ids:
            raise JobTelemetryStoreConsistencyError(
                "Store operations.job_run_details row at index "
                f"{index} references unknown job_run_id {detail.job_run_id!r}."
            )


def _assert_transition_allowed(
    current_status: JobRunStatus,
    next_status: JobRunStatus,
) -> None:
    allowed_transitions = {
        JobRunStatus.PENDING: {JobRunStatus.RUNNING, JobRunStatus.FAILED},
        JobRunStatus.RUNNING: {JobRunStatus.SUCCEEDED, JobRunStatus.FAILED},
        JobRunStatus.SUCCEEDED: set(),
        JobRunStatus.FAILED: set(),
    }
    if next_status not in allowed_transitions[current_status]:
        raise JobTelemetryValidationError(
            f"Job run status cannot transition from {current_status.value!r} "
            f"to {next_status.value!r}."
        )
