"""Canonical transaction, report-request, and job-telemetry models."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


TRANSACTION_RECORD_WIDTH = 350
TRANSACTION_REPORT_DETAIL_WIDTH = 115
REPORT_REQUEST_FIELD_COUNT = 5

_COBOL_SIGNED_DIGIT_MAP: dict[str, tuple[str, int]] = {
    "{": ("0", 1),
    "A": ("1", 1),
    "B": ("2", 1),
    "C": ("3", 1),
    "D": ("4", 1),
    "E": ("5", 1),
    "F": ("6", 1),
    "G": ("7", 1),
    "H": ("8", 1),
    "I": ("9", 1),
    "}": ("0", -1),
    "J": ("1", -1),
    "K": ("2", -1),
    "L": ("3", -1),
    "M": ("4", -1),
    "N": ("5", -1),
    "O": ("6", -1),
    "P": ("7", -1),
    "Q": ("8", -1),
    "R": ("9", -1),
}


class TransactionActivityParseError(ValueError):
    """Raised when a transaction or report-request line cannot be normalized."""


class ReportRequestType(StrEnum):
    """Supported report-request names written by `CORPT00C`."""

    MONTHLY = "Monthly"
    YEARLY = "Yearly"
    CUSTOM = "Custom"


class JobRunStatus(StrEnum):
    """Canonical lifecycle states for persisted job runs."""

    QUEUED = "queued"
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
    queued_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


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
    if len(line) > TRANSACTION_RECORD_WIDTH:
        raise TransactionActivityParseError(
            f"Line {line_number}: expected at most {TRANSACTION_RECORD_WIDTH} characters, "
            f"received {len(line)}."
        )

    record = line.ljust(TRANSACTION_RECORD_WIDTH)
    transaction_id = _required_text(_slice(record, 0, 16), "TRAN-ID", line_number)
    transaction_type_code = _required_text(_slice(record, 16, 2), "TRAN-TYPE-CD", line_number)
    transaction_category_code = _required_digits(_slice(record, 18, 4), "TRAN-CAT-CD", line_number)
    source = _required_text(_slice(record, 22, 10), "TRAN-SOURCE", line_number)
    description = _required_text(_slice(record, 32, 100), "TRAN-DESC", line_number)
    amount = _required_signed_amount(_slice(record, 132, 11), "TRAN-AMT", line_number)
    merchant_id = _required_digits(_slice(record, 143, 9), "TRAN-MERCHANT-ID", line_number)
    merchant_name = _required_text(_slice(record, 152, 50), "TRAN-MERCHANT-NAME", line_number)
    merchant_city = _required_text(_slice(record, 202, 50), "TRAN-MERCHANT-CITY", line_number)
    merchant_postal_code = _required_text(_slice(record, 252, 10), "TRAN-MERCHANT-ZIP", line_number)
    card_number = _required_digits(_slice(record, 262, 16), "TRAN-CARD-NUM", line_number)
    originated_at = _required_datetime(_slice(record, 278, 26), "TRAN-ORIG-TS", line_number)
    processed_at = _optional_datetime(_slice(record, 304, 26), "TRAN-PROC-TS", line_number)
    filler = _optional_text(_slice(record, 330, 20))

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

    requested_at = _required_compact_datetime(parts[0], "REQUEST-TIMESTAMP", line_number)
    requested_by_user_id = _required_text(parts[1], "REQUEST-USER-ID", line_number)
    report_type = _report_type_from_name(parts[2], line_number)
    start_date = _required_date(parts[3], "REQUEST-START-DATE", line_number)
    end_date = _required_date(parts[4], "REQUEST-END-DATE", line_number)
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


def _slice(record: str, start: int, length: int) -> str:
    return record[start : start + length]


def _required_text(value: str, field_name: str, line_number: int) -> str:
    normalized = value.rstrip()
    if normalized == "":
        raise TransactionActivityParseError(f"Line {line_number}: {field_name} is blank.")
    return normalized


def _optional_text(value: str) -> str | None:
    normalized = value.rstrip()
    return normalized or None


def _required_digits(value: str, field_name: str, line_number: int) -> str:
    normalized = _required_text(value, field_name, line_number)
    if not normalized.isdigit():
        raise TransactionActivityParseError(
            f"Line {line_number}: {field_name} must contain only digits, received {normalized!r}."
        )
    return normalized


def _required_date(value: str, field_name: str, line_number: int) -> date:
    normalized = _required_text(value, field_name, line_number)
    try:
        return date.fromisoformat(normalized)
    except ValueError as error:
        raise TransactionActivityParseError(
            f"Line {line_number}: {field_name} must be YYYY-MM-DD, received {normalized!r}."
        ) from error


def _required_datetime(value: str, field_name: str, line_number: int) -> datetime:
    normalized = _required_text(value, field_name, line_number)
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as error:
        raise TransactionActivityParseError(
            f"Line {line_number}: {field_name} must be ISO timestamp text, received {normalized!r}."
        ) from error


def _optional_datetime(value: str, field_name: str, line_number: int) -> datetime | None:
    normalized = value.rstrip()
    if normalized == "":
        return None
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as error:
        raise TransactionActivityParseError(
            f"Line {line_number}: {field_name} must be ISO timestamp text, received {normalized!r}."
        ) from error


def _required_compact_datetime(value: str, field_name: str, line_number: int) -> datetime:
    normalized = _required_text(value, field_name, line_number)
    try:
        return datetime.strptime(normalized, "%Y-%m-%d %H:%M:%S")
    except ValueError as error:
        raise TransactionActivityParseError(
            f"Line {line_number}: {field_name} must be YYYY-MM-DD HH:MM:SS, received {normalized!r}."
        ) from error


def _required_signed_amount(value: str, field_name: str, line_number: int) -> Decimal:
    normalized = _required_text(value, field_name, line_number)
    sign, unsigned_digits = _decode_signed_amount(normalized, field_name, line_number)
    amount = Decimal(unsigned_digits[:-2] or "0") + (Decimal(unsigned_digits[-2:]) / Decimal("100"))
    return amount if sign > 0 else amount.copy_negate()


def _decode_signed_amount(value: str, field_name: str, line_number: int) -> tuple[int, str]:
    prefix = value[:-1]
    suffix = value[-1]
    if not prefix.isdigit():
        raise TransactionActivityParseError(
            f"Line {line_number}: {field_name} must contain digits before the signed suffix, "
            f"received {value!r}."
        )

    try:
        last_digit, sign = _COBOL_SIGNED_DIGIT_MAP[suffix]
    except KeyError as error:
        raise TransactionActivityParseError(
            f"Line {line_number}: {field_name} has unsupported signed-digit suffix {suffix!r} "
            f"in {value!r}."
        ) from error

    return sign, prefix + last_digit


def _report_type_from_name(value: str, line_number: int) -> ReportRequestType:
    normalized = _required_text(value, "REQUEST-REPORT-NAME", line_number)
    try:
        return ReportRequestType(normalized)
    except ValueError as error:
        supported = ", ".join(member.value for member in ReportRequestType)
        raise TransactionActivityParseError(
            f"Line {line_number}: unsupported REQUEST-REPORT-NAME {normalized!r}; "
            f"expected one of {supported}."
        ) from error
