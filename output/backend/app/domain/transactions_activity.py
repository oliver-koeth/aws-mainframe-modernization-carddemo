"""Canonical transaction, report-request, and job-telemetry models."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.fixed_width import (
    optional_datetime,
    optional_text,
    prepare_fixed_width_record,
    required_compact_datetime,
    required_date,
    required_datetime,
    required_digits,
    required_signed_amount,
    required_text,
    slice_field,
)


TRANSACTION_RECORD_WIDTH = 350
TRANSACTION_REPORT_DETAIL_WIDTH = 115
REPORT_REQUEST_FIELD_COUNT = 5


class TransactionActivityParseError(ValueError):
    """Raised when a transaction or report-request line cannot be normalized."""


class ReportRequestType(StrEnum):
    """Supported report-request names written by `CORPT00C`."""

    MONTHLY = "Monthly"
    YEARLY = "Yearly"
    CUSTOM = "Custom"


class JobRunStatus(StrEnum):
    """Canonical lifecycle states for persisted job runs."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class JobRunDetailLevel(StrEnum):
    """Canonical severity levels for persisted job-run detail entries."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class TransactionRecord(BaseModel):
    """Canonical JSON representation of one `CVTRA05Y`/`CVTRA06Y` transaction row."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    transaction_id: str = Field(min_length=1, max_length=16)
    transaction_type_code: str = Field(min_length=2, max_length=2)
    transaction_category_code: str = Field(min_length=4, max_length=4, pattern=r"^\d{4}$")
    source: str = Field(min_length=1, max_length=10)
    description: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(decimal_places=2)
    merchant_id: str = Field(min_length=9, max_length=9, pattern=r"^\d{9}$")
    merchant_name: str = Field(min_length=1, max_length=50)
    merchant_city: str = Field(min_length=1, max_length=50)
    merchant_postal_code: str = Field(min_length=1, max_length=10)
    card_number: str = Field(min_length=16, max_length=16, pattern=r"^\d{16}$")
    originated_at: datetime
    processed_at: datetime | None = None
    filler: str | None = None


class TransactionReportDetailRecord(BaseModel):
    """Canonical report-detail projection derived from `CVTRA07Y`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    transaction_id: str = Field(min_length=1, max_length=16)
    account_id: str = Field(min_length=11, max_length=11, pattern=r"^\d{11}$")
    transaction_type_code: str = Field(min_length=2, max_length=2)
    transaction_type_description: str = Field(min_length=1, max_length=15)
    transaction_category_code: str = Field(min_length=4, max_length=4, pattern=r"^\d{4}$")
    transaction_category_description: str = Field(min_length=1, max_length=29)
    source: str = Field(min_length=1, max_length=10)
    amount: Decimal = Field(decimal_places=2)


class ReportRequestRecord(BaseModel):
    """Canonical JSON representation of one `tranrept_requests.txt` line."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    requested_at: datetime
    requested_by_user_id: str = Field(min_length=1, max_length=8)
    report_type: ReportRequestType
    start_date: date
    end_date: date


class JobRunRecord(BaseModel):
    """Canonical JSON representation of one persisted job run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    job_run_id: str = Field(min_length=1, max_length=64)
    job_name: str = Field(min_length=1, max_length=100)
    status: JobRunStatus
    started_at: datetime | None = None
    ended_at: datetime | None = None
    summary: str | None = Field(default=None, max_length=500)


class JobRunDetailRecord(BaseModel):
    """Canonical JSON representation of one persisted job-run detail event."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    job_run_id: str = Field(min_length=1, max_length=64)
    sequence_number: int = Field(ge=1)
    recorded_at: datetime
    level: JobRunDetailLevel
    message: str = Field(min_length=1, max_length=500)
    context: dict[str, Any] | None = None


def parse_transaction_record(line: str, *, line_number: int = 1) -> TransactionRecord:
    """Parse one `dailytran.txt`/`CVTRA05Y` line into the canonical transaction model."""
    record = prepare_fixed_width_record(
        line,
        record_width=TRANSACTION_RECORD_WIDTH,
        line_number=line_number,
        error_type=TransactionActivityParseError,
    )
    transaction_id = required_text(
        slice_field(record, 0, 16),
        field_name="TRAN-ID",
        line_number=line_number,
        error_type=TransactionActivityParseError,
    )
    transaction_type_code = required_text(
        slice_field(record, 16, 2),
        field_name="TRAN-TYPE-CD",
        line_number=line_number,
        error_type=TransactionActivityParseError,
    )
    transaction_category_code = required_digits(
        slice_field(record, 18, 4),
        field_name="TRAN-CAT-CD",
        line_number=line_number,
        error_type=TransactionActivityParseError,
    )
    source = required_text(
        slice_field(record, 22, 10),
        field_name="TRAN-SOURCE",
        line_number=line_number,
        error_type=TransactionActivityParseError,
    )
    description = required_text(
        slice_field(record, 32, 100),
        field_name="TRAN-DESC",
        line_number=line_number,
        error_type=TransactionActivityParseError,
    )
    amount = required_signed_amount(
        slice_field(record, 132, 11),
        field_name="TRAN-AMT",
        line_number=line_number,
        error_type=TransactionActivityParseError,
    )
    merchant_id = required_digits(
        slice_field(record, 143, 9),
        field_name="TRAN-MERCHANT-ID",
        line_number=line_number,
        error_type=TransactionActivityParseError,
    )
    merchant_name = required_text(
        slice_field(record, 152, 50),
        field_name="TRAN-MERCHANT-NAME",
        line_number=line_number,
        error_type=TransactionActivityParseError,
    )
    merchant_city = required_text(
        slice_field(record, 202, 50),
        field_name="TRAN-MERCHANT-CITY",
        line_number=line_number,
        error_type=TransactionActivityParseError,
    )
    merchant_postal_code = required_text(
        slice_field(record, 252, 10),
        field_name="TRAN-MERCHANT-ZIP",
        line_number=line_number,
        error_type=TransactionActivityParseError,
    )
    card_number = required_digits(
        slice_field(record, 262, 16),
        field_name="TRAN-CARD-NUM",
        line_number=line_number,
        error_type=TransactionActivityParseError,
    )
    originated_at = required_datetime(
        slice_field(record, 278, 26),
        field_name="TRAN-ORIG-TS",
        line_number=line_number,
        error_type=TransactionActivityParseError,
    )
    processed_at = optional_datetime(
        slice_field(record, 304, 26),
        field_name="TRAN-PROC-TS",
        line_number=line_number,
        error_type=TransactionActivityParseError,
    )
    filler = optional_text(slice_field(record, 330, 20))

    return TransactionRecord(
        transaction_id=transaction_id,
        transaction_type_code=transaction_type_code,
        transaction_category_code=transaction_category_code,
        source=source,
        description=description,
        amount=amount,
        merchant_id=merchant_id,
        merchant_name=merchant_name,
        merchant_city=merchant_city,
        merchant_postal_code=merchant_postal_code,
        card_number=card_number,
        originated_at=originated_at,
        processed_at=processed_at,
        filler=filler,
    )


def parse_report_request_record(line: str, *, line_number: int = 1) -> ReportRequestRecord:
    """Parse one `tranrept_requests.txt` line into the canonical report-request model."""
    parts = line.split("|")
    if len(parts) != REPORT_REQUEST_FIELD_COUNT:
        raise TransactionActivityParseError(
            f"Line {line_number}: expected {REPORT_REQUEST_FIELD_COUNT} pipe-delimited fields, "
            f"received {len(parts)}."
        )

    requested_at = required_compact_datetime(
        parts[0],
        field_name="REQUEST-TIMESTAMP",
        line_number=line_number,
        error_type=TransactionActivityParseError,
    )
    requested_by_user_id = required_text(
        parts[1],
        field_name="REQUEST-USER-ID",
        line_number=line_number,
        error_type=TransactionActivityParseError,
    )
    report_type = _report_type_from_name(parts[2], line_number)
    start_date = required_date(
        parts[3],
        field_name="REQUEST-START-DATE",
        line_number=line_number,
        error_type=TransactionActivityParseError,
    )
    end_date = required_date(
        parts[4],
        field_name="REQUEST-END-DATE",
        line_number=line_number,
        error_type=TransactionActivityParseError,
    )
    if start_date > end_date:
        raise TransactionActivityParseError(
            f"Line {line_number}: REQUEST-START-DATE must not be after REQUEST-END-DATE."
        )

    return ReportRequestRecord(
        requested_at=requested_at,
        requested_by_user_id=requested_by_user_id,
        report_type=report_type,
        start_date=start_date,
        end_date=end_date,
    )
def _report_type_from_name(value: str, line_number: int) -> ReportRequestType:
    normalized = required_text(
        value,
        field_name="REQUEST-REPORT-NAME",
        line_number=line_number,
        error_type=TransactionActivityParseError,
    )
    try:
        return ReportRequestType(normalized)
    except ValueError as error:
        supported = ", ".join(member.value for member in ReportRequestType)
        raise TransactionActivityParseError(
            f"Line {line_number}: unsupported REQUEST-REPORT-NAME {normalized!r}; "
            f"expected one of {supported}."
        ) from error
