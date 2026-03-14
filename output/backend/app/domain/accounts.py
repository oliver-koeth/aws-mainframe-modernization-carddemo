"""Canonical account, card, and xref models derived from `CVACT01Y`-`CVACT03Y`."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.fixed_width import (
    optional_text,
    prepare_fixed_width_record,
    required_date,
    required_digits,
    required_signed_amount,
    required_text,
    slice_field,
)


ACCOUNT_RECORD_WIDTH = 300
CARD_RECORD_WIDTH = 150
CARD_ACCOUNT_XREF_RECORD_WIDTH = 50


class AccountCardParseError(ValueError):
    """Raised when an account, card, or card-xref line cannot be normalized deterministically."""


class AccountActiveStatus(StrEnum):
    """Supported `ACCT-ACTIVE-STATUS` values."""

    ACTIVE = "Y"


class CardActiveStatus(StrEnum):
    """Supported `CARD-ACTIVE-STATUS` values."""

    ACTIVE = "Y"


class AccountRecord(BaseModel):
    """Canonical JSON representation of one `CVACT01Y` record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    account_id: str = Field(min_length=11, max_length=11, pattern=r"^\d{11}$")
    active_status: AccountActiveStatus
    is_active: bool
    current_balance: Decimal = Field(decimal_places=2)
    credit_limit: Decimal = Field(decimal_places=2)
    cash_credit_limit: Decimal = Field(decimal_places=2)
    open_date: date
    expiration_date: date
    reissue_date: date
    current_cycle_credit: Decimal = Field(decimal_places=2)
    current_cycle_debit: Decimal = Field(decimal_places=2)
    billing_postal_code: str = Field(min_length=1, max_length=10)
    group_id: str | None = Field(default=None, max_length=10)
    filler: str | None = None


class CardRecord(BaseModel):
    """Canonical JSON representation of one `CVACT02Y` record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    card_number: str = Field(min_length=16, max_length=16, pattern=r"^\d{16}$")
    account_id: str = Field(min_length=11, max_length=11, pattern=r"^\d{11}$")
    cvv_code: str = Field(min_length=3, max_length=3, pattern=r"^\d{3}$")
    embossed_name: str = Field(min_length=1, max_length=50)
    expiration_date: date
    active_status: CardActiveStatus
    is_active: bool
    filler: str | None = None


class CardAccountXrefRecord(BaseModel):
    """Canonical JSON representation of one `CVACT03Y` record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    card_number: str = Field(min_length=16, max_length=16, pattern=r"^\d{16}$")
    customer_id: str = Field(min_length=9, max_length=9, pattern=r"^\d{9}$")
    account_id: str = Field(min_length=11, max_length=11, pattern=r"^\d{11}$")
    filler: str | None = None


def parse_account_record(line: str, *, line_number: int = 1) -> AccountRecord:
    """Parse one `acctdata.txt` line into the canonical account model."""
    record = prepare_fixed_width_record(
        line,
        record_width=ACCOUNT_RECORD_WIDTH,
        line_number=line_number,
        error_type=AccountCardParseError,
    )
    account_id = required_digits(
        slice_field(record, 0, 11),
        field_name="ACCT-ID",
        line_number=line_number,
        error_type=AccountCardParseError,
    )
    active_status_code = required_text(
        slice_field(record, 11, 1),
        field_name="ACCT-ACTIVE-STATUS",
        line_number=line_number,
        error_type=AccountCardParseError,
    )
    current_balance = required_signed_amount(
        slice_field(record, 12, 12),
        field_name="ACCT-CURR-BAL",
        line_number=line_number,
        error_type=AccountCardParseError,
        expected_width=12,
        allow_unsigned_final_digit=True,
        prefix_error_detail="must contain only digits before the sign nibble",
    )
    credit_limit = required_signed_amount(
        slice_field(record, 24, 12),
        field_name="ACCT-CREDIT-LIMIT",
        line_number=line_number,
        error_type=AccountCardParseError,
        expected_width=12,
        allow_unsigned_final_digit=True,
        prefix_error_detail="must contain only digits before the sign nibble",
    )
    cash_credit_limit = required_signed_amount(
        slice_field(record, 36, 12),
        field_name="ACCT-CASH-CREDIT-LIMIT",
        line_number=line_number,
        error_type=AccountCardParseError,
        expected_width=12,
        allow_unsigned_final_digit=True,
        prefix_error_detail="must contain only digits before the sign nibble",
    )
    open_date = required_date(
        slice_field(record, 48, 10),
        field_name="ACCT-OPEN-DATE",
        line_number=line_number,
        error_type=AccountCardParseError,
    )
    expiration_date = required_date(
        slice_field(record, 58, 10),
        field_name="ACCT-EXPIRAION-DATE",
        line_number=line_number,
        error_type=AccountCardParseError,
    )
    reissue_date = required_date(
        slice_field(record, 68, 10),
        field_name="ACCT-REISSUE-DATE",
        line_number=line_number,
        error_type=AccountCardParseError,
    )
    current_cycle_credit = required_signed_amount(
        slice_field(record, 78, 12),
        field_name="ACCT-CURR-CYC-CREDIT",
        line_number=line_number,
        error_type=AccountCardParseError,
        expected_width=12,
        allow_unsigned_final_digit=True,
        prefix_error_detail="must contain only digits before the sign nibble",
    )
    current_cycle_debit = required_signed_amount(
        slice_field(record, 90, 12),
        field_name="ACCT-CURR-CYC-DEBIT",
        line_number=line_number,
        error_type=AccountCardParseError,
        expected_width=12,
        allow_unsigned_final_digit=True,
        prefix_error_detail="must contain only digits before the sign nibble",
    )
    billing_postal_code = required_text(
        slice_field(record, 102, 10),
        field_name="ACCT-ADDR-ZIP",
        line_number=line_number,
        error_type=AccountCardParseError,
    )
    group_id = optional_text(slice_field(record, 112, 10))
    filler = optional_text(slice_field(record, 122, 178))

    active_status = _account_status_from_code(active_status_code, line_number)

    return AccountRecord(
        account_id=account_id,
        active_status=active_status,
        is_active=active_status is AccountActiveStatus.ACTIVE,
        current_balance=current_balance,
        credit_limit=credit_limit,
        cash_credit_limit=cash_credit_limit,
        open_date=open_date,
        expiration_date=expiration_date,
        reissue_date=reissue_date,
        current_cycle_credit=current_cycle_credit,
        current_cycle_debit=current_cycle_debit,
        billing_postal_code=billing_postal_code,
        group_id=group_id,
        filler=filler,
    )


def parse_card_record(line: str, *, line_number: int = 1) -> CardRecord:
    """Parse one `carddata.txt` line into the canonical card model."""
    record = prepare_fixed_width_record(
        line,
        record_width=CARD_RECORD_WIDTH,
        line_number=line_number,
        error_type=AccountCardParseError,
    )
    card_number = required_digits(
        slice_field(record, 0, 16),
        field_name="CARD-NUM",
        line_number=line_number,
        error_type=AccountCardParseError,
    )
    account_id = required_digits(
        slice_field(record, 16, 11),
        field_name="CARD-ACCT-ID",
        line_number=line_number,
        error_type=AccountCardParseError,
    )
    cvv_code = required_digits(
        slice_field(record, 27, 3),
        field_name="CARD-CVV-CD",
        line_number=line_number,
        error_type=AccountCardParseError,
    )
    embossed_name = required_text(
        slice_field(record, 30, 50),
        field_name="CARD-EMBOSSED-NAME",
        line_number=line_number,
        error_type=AccountCardParseError,
    )
    expiration_date = required_date(
        slice_field(record, 80, 10),
        field_name="CARD-EXPIRAION-DATE",
        line_number=line_number,
        error_type=AccountCardParseError,
    )
    active_status_code = required_text(
        slice_field(record, 90, 1),
        field_name="CARD-ACTIVE-STATUS",
        line_number=line_number,
        error_type=AccountCardParseError,
    )
    filler = optional_text(slice_field(record, 91, 59))

    active_status = _card_status_from_code(active_status_code, line_number)

    return CardRecord(
        card_number=card_number,
        account_id=account_id,
        cvv_code=cvv_code,
        embossed_name=embossed_name,
        expiration_date=expiration_date,
        active_status=active_status,
        is_active=active_status is CardActiveStatus.ACTIVE,
        filler=filler,
    )


def parse_card_account_xref_record(
    line: str,
    *,
    line_number: int = 1,
) -> CardAccountXrefRecord:
    """Parse one `cardxref.txt` line into the canonical card-account xref model."""
    record = prepare_fixed_width_record(
        line,
        record_width=CARD_ACCOUNT_XREF_RECORD_WIDTH,
        line_number=line_number,
        error_type=AccountCardParseError,
    )
    card_number = required_digits(
        slice_field(record, 0, 16),
        field_name="XREF-CARD-NUM",
        line_number=line_number,
        error_type=AccountCardParseError,
    )
    customer_id = required_digits(
        slice_field(record, 16, 9),
        field_name="XREF-CUST-ID",
        line_number=line_number,
        error_type=AccountCardParseError,
    )
    account_id = required_digits(
        slice_field(record, 25, 11),
        field_name="XREF-ACCT-ID",
        line_number=line_number,
        error_type=AccountCardParseError,
    )
    filler = optional_text(slice_field(record, 36, 14))

    return CardAccountXrefRecord(
        card_number=card_number,
        customer_id=customer_id,
        account_id=account_id,
        filler=filler,
    )
def _account_status_from_code(value: str, line_number: int) -> AccountActiveStatus:
    if value != AccountActiveStatus.ACTIVE:
        raise AccountCardParseError(
            f"Line {line_number}: unsupported ACCT-ACTIVE-STATUS {value!r}; expected 'Y'."
        )
    return AccountActiveStatus(value)


def _card_status_from_code(value: str, line_number: int) -> CardActiveStatus:
    if value != CardActiveStatus.ACTIVE:
        raise AccountCardParseError(
            f"Line {line_number}: unsupported CARD-ACTIVE-STATUS {value!r}; expected 'Y'."
        )
    return CardActiveStatus(value)
