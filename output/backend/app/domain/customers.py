"""Canonical customer models derived from `CVCUS01Y`."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


CUSTOMER_RECORD_WIDTH = 500


class CustomerParseError(ValueError):
    """Raised when a customer line cannot be normalized deterministically."""


class PrimaryCardHolderIndicator(StrEnum):
    """Supported `CUST-PRI-CARD-HOLDER-IND` values."""

    YES = "Y"
    NO = "N"


class CustomerName(BaseModel):
    """Normalized customer name fields from the flat-file record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    first_name: str = Field(min_length=1, max_length=25)
    middle_name: str | None = Field(default=None, max_length=25)
    last_name: str = Field(min_length=1, max_length=25)


class CustomerAddress(BaseModel):
    """Normalized customer address fields from the flat-file record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    line_1: str = Field(min_length=1, max_length=50)
    line_2: str | None = Field(default=None, max_length=50)
    line_3: str | None = Field(default=None, max_length=50)
    state_code: str = Field(min_length=2, max_length=2)
    country_code: str = Field(min_length=3, max_length=3)
    postal_code: str = Field(min_length=1, max_length=10)


class CustomerContact(BaseModel):
    """Normalized contact and identity fields from the flat-file record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    primary_phone: str = Field(min_length=1, max_length=15)
    secondary_phone: str | None = Field(default=None, max_length=15)
    social_security_number: str = Field(min_length=9, max_length=9, pattern=r"^\d{9}$")
    government_issued_id: str | None = Field(default=None, max_length=20)
    eft_account_id: str | None = Field(default=None, max_length=10)


class CustomerRecord(BaseModel):
    """Canonical JSON representation of one `CVCUS01Y` record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    customer_id: str = Field(min_length=9, max_length=9, pattern=r"^\d{9}$")
    name: CustomerName
    address: CustomerAddress
    contact: CustomerContact
    date_of_birth: date
    primary_card_holder_indicator: PrimaryCardHolderIndicator
    is_primary_card_holder: bool
    fico_credit_score: int = Field(ge=0, le=999)
    filler: str | None = None


def parse_customer_record(line: str, *, line_number: int = 1) -> CustomerRecord:
    """Parse one `custdata.txt` line into the canonical customer model."""
    if len(line) > CUSTOMER_RECORD_WIDTH:
        raise CustomerParseError(
            f"Line {line_number}: expected at most {CUSTOMER_RECORD_WIDTH} characters, "
            f"received {len(line)}."
        )

    record = line.ljust(CUSTOMER_RECORD_WIDTH)
    customer_id = _required_digits(_slice(record, 0, 9), "CUST-ID", line_number)
    first_name = _required_text(_slice(record, 9, 25), "CUST-FIRST-NAME", line_number)
    middle_name = _optional_text(_slice(record, 34, 25))
    last_name = _required_text(_slice(record, 59, 25), "CUST-LAST-NAME", line_number)
    address_line_1 = _required_text(_slice(record, 84, 50), "CUST-ADDR-LINE-1", line_number)
    address_line_2 = _optional_text(_slice(record, 134, 50))
    address_line_3 = _optional_text(_slice(record, 184, 50))
    state_code = _required_text(_slice(record, 234, 2), "CUST-ADDR-STATE-CD", line_number)
    country_code = _required_text(_slice(record, 236, 3), "CUST-ADDR-COUNTRY-CD", line_number)
    postal_code = _required_text(_slice(record, 239, 10), "CUST-ADDR-ZIP", line_number)
    primary_phone = _required_text(_slice(record, 249, 15), "CUST-PHONE-NUM-1", line_number)
    secondary_phone = _optional_text(_slice(record, 264, 15))
    social_security_number = _required_digits(_slice(record, 279, 9), "CUST-SSN", line_number)
    government_issued_id = _optional_text(_slice(record, 288, 20))
    date_of_birth = _required_date(_slice(record, 308, 10), "CUST-DOB-YYYY-MM-DD", line_number)
    eft_account_id = _optional_text(_slice(record, 318, 10))
    primary_indicator = _required_text(
        _slice(record, 328, 1),
        "CUST-PRI-CARD-HOLDER-IND",
        line_number,
    )
    fico_credit_score = _required_int(_slice(record, 329, 3), "CUST-FICO-CREDIT-SCORE", line_number)
    filler = _optional_text(_slice(record, 332, 168))

    if primary_indicator not in {PrimaryCardHolderIndicator.YES, PrimaryCardHolderIndicator.NO}:
        raise CustomerParseError(
            f"Line {line_number}: unsupported CUST-PRI-CARD-HOLDER-IND "
            f"{primary_indicator!r}; expected 'Y' or 'N'."
        )

    return CustomerRecord(
        customer_id=customer_id,
        name=CustomerName(first_name=first_name, middle_name=middle_name, last_name=last_name),
        address=CustomerAddress(
            line_1=address_line_1,
            line_2=address_line_2,
            line_3=address_line_3,
            state_code=state_code,
            country_code=country_code,
            postal_code=postal_code,
        ),
        contact=CustomerContact(
            primary_phone=primary_phone,
            secondary_phone=secondary_phone,
            social_security_number=social_security_number,
            government_issued_id=government_issued_id,
            eft_account_id=eft_account_id,
        ),
        date_of_birth=date_of_birth,
        primary_card_holder_indicator=PrimaryCardHolderIndicator(primary_indicator),
        is_primary_card_holder=primary_indicator == PrimaryCardHolderIndicator.YES,
        fico_credit_score=fico_credit_score,
        filler=filler,
    )


def _slice(record: str, start: int, length: int) -> str:
    return record[start : start + length]


def _required_text(value: str, field_name: str, line_number: int) -> str:
    normalized = value.rstrip()
    if normalized == "":
        raise CustomerParseError(f"Line {line_number}: {field_name} is blank.")
    return normalized


def _optional_text(value: str) -> str | None:
    normalized = value.rstrip()
    return normalized or None


def _required_digits(value: str, field_name: str, line_number: int) -> str:
    normalized = _required_text(value, field_name, line_number)
    if not normalized.isdigit():
        raise CustomerParseError(
            f"Line {line_number}: {field_name} must contain only digits, received {normalized!r}."
        )
    return normalized


def _required_int(value: str, field_name: str, line_number: int) -> int:
    normalized = _required_digits(value, field_name, line_number)
    return int(normalized)


def _required_date(value: str, field_name: str, line_number: int) -> date:
    normalized = _required_text(value, field_name, line_number)
    try:
        return date.fromisoformat(normalized)
    except ValueError as error:
        raise CustomerParseError(
            f"Line {line_number}: {field_name} must be YYYY-MM-DD, received {normalized!r}."
        ) from error
