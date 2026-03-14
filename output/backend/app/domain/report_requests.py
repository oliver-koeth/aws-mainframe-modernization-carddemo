"""Shared report-request capture and retrieval service derived from `CORPT00C`."""

from __future__ import annotations

from calendar import monthrange
from collections.abc import Callable
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, ValidationError

from app.domain.transactions_activity import ReportRequestRecord, ReportRequestType
from app.domain.users import UserSecurityRecord
from app.models import StoragePaths
from app.storage import read_store, write_store


class ReportRequestServiceError(RuntimeError):
    """Base error for report-request service failures."""


class ReportRequestValidationError(ReportRequestServiceError):
    """Raised when a report-request input is invalid."""


class ReportRequestStoreConsistencyError(ReportRequestServiceError):
    """Raised when persisted report-request state is inconsistent."""


class ReportRequestCreateRequest(BaseModel):
    """Raw report-request inputs modeled on the `CORPT00C` launcher choices."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    requested_by_user_id: str
    report_type: str
    start_date: str | None = None
    end_date: str | None = None


class ReportRequestService:
    """Storage-backed report-request capture and retrieval behavior for Phase 1."""

    def __init__(
        self,
        paths: StoragePaths,
        *,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._paths = paths
        self._now_provider = now_provider or datetime.now

    def create_report_request(
        self,
        request: ReportRequestCreateRequest,
    ) -> ReportRequestRecord:
        """Validate and append one report request to `report_requests[]`."""
        store = read_store(self._paths)
        users = _validate_collection(
            store["users"],
            UserSecurityRecord,
            collection_name="users",
        )
        existing_requests = _validate_collection(
            store["report_requests"],
            ReportRequestRecord,
            collection_name="report_requests",
        )

        requested_by_user_id = _normalize_user_id(request.requested_by_user_id)
        _require_user(users, requested_by_user_id=requested_by_user_id)

        report_type = _normalize_report_type(request.report_type)
        requested_at = self._now_provider().replace(microsecond=0)
        start_date, end_date = _resolve_date_range(
            report_type,
            start_date=request.start_date,
            end_date=request.end_date,
            today=requested_at.date(),
        )

        created_request = ReportRequestRecord(
            requested_at=requested_at,
            requested_by_user_id=requested_by_user_id,
            report_type=report_type,
            start_date=start_date,
            end_date=end_date,
        )

        # `CORPT00C` appends every confirmed request without duplicate suppression.
        store["report_requests"] = [
            *_existing_requests_to_python(existing_requests),
            created_request.model_dump(mode="python"),
        ]
        write_store(self._paths, store)
        return created_request

    def list_report_requests(
        self,
        *,
        requested_by_user_id: str | None = None,
        report_type: str | ReportRequestType | None = None,
    ) -> list[ReportRequestRecord]:
        """Return persisted report requests in store order with optional filters."""
        store = read_store(self._paths)
        users = _validate_collection(
            store["users"],
            UserSecurityRecord,
            collection_name="users",
        )
        requests = _validate_collection(
            store["report_requests"],
            ReportRequestRecord,
            collection_name="report_requests",
        )
        valid_user_ids = {record.user_id for record in users}
        for index, request_record in enumerate(requests, start=1):
            if request_record.requested_by_user_id not in valid_user_ids:
                raise ReportRequestStoreConsistencyError(
                    "Store report_requests row at index "
                    f"{index} references unknown user ID "
                    f"{request_record.requested_by_user_id!r}."
                )

        normalized_user_id = (
            _normalize_user_id(requested_by_user_id)
            if requested_by_user_id is not None
            else None
        )
        if normalized_user_id is not None:
            _require_user(users, requested_by_user_id=normalized_user_id)

        normalized_report_type = (
            report_type
            if isinstance(report_type, ReportRequestType)
            else (
                _normalize_report_type(report_type)
                if report_type is not None
                else None
            )
        )

        return [
            request_record
            for request_record in requests
            if (
                normalized_user_id is None
                or request_record.requested_by_user_id == normalized_user_id
            )
            and (
                normalized_report_type is None
                or request_record.report_type is normalized_report_type
            )
        ]


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
            raise ReportRequestStoreConsistencyError(
                f"Store {collection_name} row at index {index} is invalid: {error}"
            ) from error
    return records


def _normalize_user_id(value: str) -> str:
    normalized = value.strip().upper()
    if normalized == "":
        raise ReportRequestValidationError("User ID cannot be empty.")
    if len(normalized) > 8:
        raise ReportRequestValidationError("User ID must be 8 characters or fewer.")
    return normalized


def _require_user(
    users: list[UserSecurityRecord],
    *,
    requested_by_user_id: str,
) -> None:
    if any(user.user_id == requested_by_user_id for user in users):
        return
    raise ReportRequestValidationError(
        f"User ID {requested_by_user_id!r} was not found."
    )


def _normalize_report_type(value: str) -> ReportRequestType:
    normalized = value.strip().lower()
    mapping = {
        "monthly": ReportRequestType.MONTHLY,
        "yearly": ReportRequestType.YEARLY,
        "custom": ReportRequestType.CUSTOM,
    }
    try:
        return mapping[normalized]
    except KeyError as error:
        raise ReportRequestValidationError(
            "Report type must be one of: Monthly, Yearly, Custom."
        ) from error


def _resolve_date_range(
    report_type: ReportRequestType,
    *,
    start_date: str | None,
    end_date: str | None,
    today: date,
) -> tuple[date, date]:
    if report_type is ReportRequestType.MONTHLY:
        _reject_explicit_custom_dates(start_date=start_date, end_date=end_date)
        last_day = monthrange(today.year, today.month)[1]
        return (date(today.year, today.month, 1), date(today.year, today.month, last_day))

    if report_type is ReportRequestType.YEARLY:
        _reject_explicit_custom_dates(start_date=start_date, end_date=end_date)
        return (date(today.year, 1, 1), date(today.year, 12, 31))

    resolved_start = _parse_required_date(
        start_date,
        field_name="Start date",
    )
    resolved_end = _parse_required_date(
        end_date,
        field_name="End date",
    )
    if resolved_start > resolved_end:
        raise ReportRequestValidationError(
            "Start date must not be after end date."
        )
    return (resolved_start, resolved_end)


def _reject_explicit_custom_dates(
    *,
    start_date: str | None,
    end_date: str | None,
) -> None:
    if (start_date is not None and start_date.strip() != "") or (
        end_date is not None and end_date.strip() != ""
    ):
        raise ReportRequestValidationError(
            "Start and end dates are only accepted for Custom reports."
        )


def _parse_required_date(value: str | None, *, field_name: str) -> date:
    if value is None or value.strip() == "":
        raise ReportRequestValidationError(
            f"{field_name} is required for Custom reports."
        )
    try:
        return date.fromisoformat(value.strip())
    except ValueError as error:
        raise ReportRequestValidationError(
            f"{field_name} must be in format YYYY-MM-DD."
        ) from error


def _existing_requests_to_python(
    requests: list[ReportRequestRecord],
) -> list[dict[str, object]]:
    """Preserve validated rows when rewriting the append-only request collection."""
    return [request.model_dump(mode="python") for request in requests]
