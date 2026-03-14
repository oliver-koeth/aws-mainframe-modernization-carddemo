"""Canonical customer models derived from `CVCUS01Y`."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.fixed_width import (
    optional_text,
    prepare_fixed_width_record,
    required_date,
    required_digits,
    required_int,
    required_text,
    slice_field,
)


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
    record = prepare_fixed_width_record(
        line,
        record_width=CUSTOMER_RECORD_WIDTH,
        line_number=line_number,
        error_type=CustomerParseError,
    )
    customer_id = required_digits(
        slice_field(record, 0, 9),
        field_name="CUST-ID",
        line_number=line_number,
        error_type=CustomerParseError,
    )
    first_name = required_text(
        slice_field(record, 9, 25),
        field_name="CUST-FIRST-NAME",
        line_number=line_number,
        error_type=CustomerParseError,
    )
    middle_name = optional_text(slice_field(record, 34, 25))
    last_name = required_text(
        slice_field(record, 59, 25),
        field_name="CUST-LAST-NAME",
        line_number=line_number,
        error_type=CustomerParseError,
    )
    address_line_1 = required_text(
        slice_field(record, 84, 50),
        field_name="CUST-ADDR-LINE-1",
        line_number=line_number,
        error_type=CustomerParseError,
    )
    address_line_2 = optional_text(slice_field(record, 134, 50))
    address_line_3 = optional_text(slice_field(record, 184, 50))
    state_code = required_text(
        slice_field(record, 234, 2),
        field_name="CUST-ADDR-STATE-CD",
        line_number=line_number,
        error_type=CustomerParseError,
    )
    country_code = required_text(
        slice_field(record, 236, 3),
        field_name="CUST-ADDR-COUNTRY-CD",
        line_number=line_number,
        error_type=CustomerParseError,
    )
    postal_code = required_text(
        slice_field(record, 239, 10),
        field_name="CUST-ADDR-ZIP",
        line_number=line_number,
        error_type=CustomerParseError,
    )
    primary_phone = required_text(
        slice_field(record, 249, 15),
        field_name="CUST-PHONE-NUM-1",
        line_number=line_number,
        error_type=CustomerParseError,
    )
    secondary_phone = optional_text(slice_field(record, 264, 15))
    social_security_number = required_digits(
        slice_field(record, 279, 9),
        field_name="CUST-SSN",
        line_number=line_number,
        error_type=CustomerParseError,
    )
    government_issued_id = optional_text(slice_field(record, 288, 20))
    date_of_birth = required_date(
        slice_field(record, 308, 10),
        field_name="CUST-DOB-YYYY-MM-DD",
        line_number=line_number,
        error_type=CustomerParseError,
    )
    eft_account_id = optional_text(slice_field(record, 318, 10))
    primary_indicator = required_text(
        slice_field(record, 328, 1),
        field_name="CUST-PRI-CARD-HOLDER-IND",
        line_number=line_number,
        error_type=CustomerParseError,
    )
    fico_credit_score = required_int(
        slice_field(record, 329, 3),
        field_name="CUST-FICO-CREDIT-SCORE",
        line_number=line_number,
        error_type=CustomerParseError,
    )
    filler = optional_text(slice_field(record, 332, 168))

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
