"""Canonical transaction reference models derived from `CVTRA01Y`-`CVTRA04Y`."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.fixed_width import (
    optional_text,
    prepare_fixed_width_record,
    required_digits,
    required_signed_amount,
    required_text,
    slice_field,
)


CATEGORY_BALANCE_RECORD_WIDTH = 50
DISCLOSURE_GROUP_RECORD_WIDTH = 50
TRANSACTION_TYPE_RECORD_WIDTH = 60
TRANSACTION_CATEGORY_RECORD_WIDTH = 60


class TransactionReferenceParseError(ValueError):
    """Raised when a transaction reference line cannot be normalized deterministically."""


class CategoryBalanceRecord(BaseModel):
    """Canonical JSON representation of one `CVTRA01Y` record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    account_id: str = Field(min_length=11, max_length=11, pattern=r"^\d{11}$")
    transaction_type_code: str = Field(min_length=2, max_length=2)
    transaction_category_code: str = Field(min_length=4, max_length=4, pattern=r"^\d{4}$")
    balance: Decimal = Field(decimal_places=2)
    filler: str | None = None


class DisclosureGroupRecord(BaseModel):
    """Canonical JSON representation of one `CVTRA02Y` record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    account_group_id: str = Field(min_length=1, max_length=10)
    transaction_type_code: str = Field(min_length=2, max_length=2)
    transaction_category_code: str = Field(min_length=4, max_length=4, pattern=r"^\d{4}$")
    interest_rate: Decimal = Field(decimal_places=2)
    filler: str | None = None


class TransactionTypeRecord(BaseModel):
    """Canonical JSON representation of one `CVTRA03Y` record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    transaction_type_code: str = Field(min_length=2, max_length=2)
    description: str = Field(min_length=1, max_length=50)
    filler: str | None = None


class TransactionCategoryRecord(BaseModel):
    """Canonical JSON representation of one `CVTRA04Y` record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    transaction_type_code: str = Field(min_length=2, max_length=2)
    transaction_category_code: str = Field(min_length=4, max_length=4, pattern=r"^\d{4}$")
    description: str = Field(min_length=1, max_length=50)
    filler: str | None = None


def parse_category_balance_record(line: str, *, line_number: int = 1) -> CategoryBalanceRecord:
    """Parse one `tcatbal.txt` line into the canonical category-balance model."""
    record = prepare_fixed_width_record(
        line,
        record_width=CATEGORY_BALANCE_RECORD_WIDTH,
        line_number=line_number,
        error_type=TransactionReferenceParseError,
    )
    account_id = required_digits(
        slice_field(record, 0, 11),
        field_name="TRANCAT-ACCT-ID",
        line_number=line_number,
        error_type=TransactionReferenceParseError,
    )
    transaction_type_code = required_text(
        slice_field(record, 11, 2),
        field_name="TRANCAT-TYPE-CD",
        line_number=line_number,
        error_type=TransactionReferenceParseError,
    )
    transaction_category_code = required_digits(
        slice_field(record, 13, 4),
        field_name="TRANCAT-CD",
        line_number=line_number,
        error_type=TransactionReferenceParseError,
    )
    balance = required_signed_amount(
        slice_field(record, 17, 11),
        field_name="TRAN-CAT-BAL",
        line_number=line_number,
        error_type=TransactionReferenceParseError,
    )
    filler = optional_text(slice_field(record, 28, 22))

    return CategoryBalanceRecord(
        account_id=account_id,
        transaction_type_code=transaction_type_code,
        transaction_category_code=transaction_category_code,
        balance=balance,
        filler=filler,
    )


def parse_disclosure_group_record(line: str, *, line_number: int = 1) -> DisclosureGroupRecord:
    """Parse one `discgrp.txt` line into the canonical disclosure-group model."""
    record = prepare_fixed_width_record(
        line,
        record_width=DISCLOSURE_GROUP_RECORD_WIDTH,
        line_number=line_number,
        error_type=TransactionReferenceParseError,
    )
    account_group_id = required_text(
        slice_field(record, 0, 10),
        field_name="DIS-ACCT-GROUP-ID",
        line_number=line_number,
        error_type=TransactionReferenceParseError,
    )
    transaction_type_code = required_text(
        slice_field(record, 10, 2),
        field_name="DIS-TRAN-TYPE-CD",
        line_number=line_number,
        error_type=TransactionReferenceParseError,
    )
    transaction_category_code = required_digits(
        slice_field(record, 12, 4),
        field_name="DIS-TRAN-CAT-CD",
        line_number=line_number,
        error_type=TransactionReferenceParseError,
    )
    interest_rate = required_signed_amount(
        slice_field(record, 16, 6),
        field_name="DIS-INT-RATE",
        line_number=line_number,
        error_type=TransactionReferenceParseError,
    )
    filler = optional_text(slice_field(record, 22, 28))

    return DisclosureGroupRecord(
        account_group_id=account_group_id,
        transaction_type_code=transaction_type_code,
        transaction_category_code=transaction_category_code,
        interest_rate=interest_rate,
        filler=filler,
    )


def parse_transaction_type_record(line: str, *, line_number: int = 1) -> TransactionTypeRecord:
    """Parse one `trantype.txt` line into the canonical transaction-type model."""
    record = prepare_fixed_width_record(
        line,
        record_width=TRANSACTION_TYPE_RECORD_WIDTH,
        line_number=line_number,
        error_type=TransactionReferenceParseError,
    )
    transaction_type_code = required_text(
        slice_field(record, 0, 2),
        field_name="TRAN-TYPE",
        line_number=line_number,
        error_type=TransactionReferenceParseError,
    )
    description = required_text(
        slice_field(record, 2, 50),
        field_name="TRAN-TYPE-DESC",
        line_number=line_number,
        error_type=TransactionReferenceParseError,
    )
    filler = optional_text(slice_field(record, 52, 8))

    return TransactionTypeRecord(
        transaction_type_code=transaction_type_code,
        description=description,
        filler=filler,
    )


def parse_transaction_category_record(
    line: str,
    *,
    line_number: int = 1,
) -> TransactionCategoryRecord:
    """Parse one `trancatg.txt` line into the canonical transaction-category model."""
    record = prepare_fixed_width_record(
        line,
        record_width=TRANSACTION_CATEGORY_RECORD_WIDTH,
        line_number=line_number,
        error_type=TransactionReferenceParseError,
    )
    transaction_type_code = required_text(
        slice_field(record, 0, 2),
        field_name="TRAN-TYPE-CD",
        line_number=line_number,
        error_type=TransactionReferenceParseError,
    )
    transaction_category_code = required_digits(
        slice_field(record, 2, 4),
        field_name="TRAN-CAT-CD",
        line_number=line_number,
        error_type=TransactionReferenceParseError,
    )
    description = required_text(
        slice_field(record, 6, 50),
        field_name="TRAN-CAT-TYPE-DESC",
        line_number=line_number,
        error_type=TransactionReferenceParseError,
    )
    filler = optional_text(slice_field(record, 56, 4))

    return TransactionCategoryRecord(
        transaction_type_code=transaction_type_code,
        transaction_category_code=transaction_category_code,
        description=description,
        filler=filler,
    )
