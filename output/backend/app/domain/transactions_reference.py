"""Canonical transaction reference models derived from `CVTRA01Y`-`CVTRA04Y`."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


CATEGORY_BALANCE_RECORD_WIDTH = 50
DISCLOSURE_GROUP_RECORD_WIDTH = 50
TRANSACTION_TYPE_RECORD_WIDTH = 60
TRANSACTION_CATEGORY_RECORD_WIDTH = 60

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
    if len(line) > CATEGORY_BALANCE_RECORD_WIDTH:
        raise TransactionReferenceParseError(
            f"Line {line_number}: expected at most {CATEGORY_BALANCE_RECORD_WIDTH} characters, "
            f"received {len(line)}."
        )

    record = line.ljust(CATEGORY_BALANCE_RECORD_WIDTH)
    account_id = _required_digits(_slice(record, 0, 11), "TRANCAT-ACCT-ID", line_number)
    transaction_type_code = _required_text(
        _slice(record, 11, 2),
        "TRANCAT-TYPE-CD",
        line_number,
    )
    transaction_category_code = _required_digits(
        _slice(record, 13, 4),
        "TRANCAT-CD",
        line_number,
    )
    balance = _required_signed_amount(
        _slice(record, 17, 11),
        "TRAN-CAT-BAL",
        line_number,
    )
    filler = _optional_text(_slice(record, 28, 22))

    return CategoryBalanceRecord(
        account_id=account_id,
        transaction_type_code=transaction_type_code,
        transaction_category_code=transaction_category_code,
        balance=balance,
        filler=filler,
    )


def parse_disclosure_group_record(line: str, *, line_number: int = 1) -> DisclosureGroupRecord:
    """Parse one `discgrp.txt` line into the canonical disclosure-group model."""
    if len(line) > DISCLOSURE_GROUP_RECORD_WIDTH:
        raise TransactionReferenceParseError(
            f"Line {line_number}: expected at most {DISCLOSURE_GROUP_RECORD_WIDTH} characters, "
            f"received {len(line)}."
        )

    record = line.ljust(DISCLOSURE_GROUP_RECORD_WIDTH)
    account_group_id = _required_text(_slice(record, 0, 10), "DIS-ACCT-GROUP-ID", line_number)
    transaction_type_code = _required_text(
        _slice(record, 10, 2),
        "DIS-TRAN-TYPE-CD",
        line_number,
    )
    transaction_category_code = _required_digits(
        _slice(record, 12, 4),
        "DIS-TRAN-CAT-CD",
        line_number,
    )
    interest_rate = _required_signed_amount(
        _slice(record, 16, 6),
        "DIS-INT-RATE",
        line_number,
    )
    filler = _optional_text(_slice(record, 22, 28))

    return DisclosureGroupRecord(
        account_group_id=account_group_id,
        transaction_type_code=transaction_type_code,
        transaction_category_code=transaction_category_code,
        interest_rate=interest_rate,
        filler=filler,
    )


def parse_transaction_type_record(line: str, *, line_number: int = 1) -> TransactionTypeRecord:
    """Parse one `trantype.txt` line into the canonical transaction-type model."""
    if len(line) > TRANSACTION_TYPE_RECORD_WIDTH:
        raise TransactionReferenceParseError(
            f"Line {line_number}: expected at most {TRANSACTION_TYPE_RECORD_WIDTH} characters, "
            f"received {len(line)}."
        )

    record = line.ljust(TRANSACTION_TYPE_RECORD_WIDTH)
    transaction_type_code = _required_text(_slice(record, 0, 2), "TRAN-TYPE", line_number)
    description = _required_text(_slice(record, 2, 50), "TRAN-TYPE-DESC", line_number)
    filler = _optional_text(_slice(record, 52, 8))

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
    if len(line) > TRANSACTION_CATEGORY_RECORD_WIDTH:
        raise TransactionReferenceParseError(
            f"Line {line_number}: expected at most {TRANSACTION_CATEGORY_RECORD_WIDTH} characters, "
            f"received {len(line)}."
        )

    record = line.ljust(TRANSACTION_CATEGORY_RECORD_WIDTH)
    transaction_type_code = _required_text(_slice(record, 0, 2), "TRAN-TYPE-CD", line_number)
    transaction_category_code = _required_digits(
        _slice(record, 2, 4),
        "TRAN-CAT-CD",
        line_number,
    )
    description = _required_text(_slice(record, 6, 50), "TRAN-CAT-TYPE-DESC", line_number)
    filler = _optional_text(_slice(record, 56, 4))

    return TransactionCategoryRecord(
        transaction_type_code=transaction_type_code,
        transaction_category_code=transaction_category_code,
        description=description,
        filler=filler,
    )


def _slice(record: str, start: int, length: int) -> str:
    return record[start : start + length]


def _required_text(value: str, field_name: str, line_number: int) -> str:
    normalized = value.rstrip()
    if normalized == "":
        raise TransactionReferenceParseError(f"Line {line_number}: {field_name} is blank.")
    return normalized


def _optional_text(value: str) -> str | None:
    normalized = value.rstrip()
    return normalized or None


def _required_digits(value: str, field_name: str, line_number: int) -> str:
    normalized = _required_text(value, field_name, line_number)
    if not normalized.isdigit():
        raise TransactionReferenceParseError(
            f"Line {line_number}: {field_name} must contain only digits, received {normalized!r}."
        )
    return normalized


def _required_signed_amount(value: str, field_name: str, line_number: int) -> Decimal:
    normalized = _required_text(value, field_name, line_number)
    sign, unsigned_digits = _decode_signed_amount(normalized, field_name, line_number)
    amount = Decimal(unsigned_digits[:-2] or "0") + (Decimal(unsigned_digits[-2:]) / Decimal("100"))
    return amount if sign > 0 else amount.copy_negate()


def _decode_signed_amount(value: str, field_name: str, line_number: int) -> tuple[int, str]:
    prefix = value[:-1]
    suffix = value[-1]
    if not prefix.isdigit():
        raise TransactionReferenceParseError(
            f"Line {line_number}: {field_name} must contain digits before the signed suffix, "
            f"received {value!r}."
        )

    try:
        last_digit, sign = _COBOL_SIGNED_DIGIT_MAP[suffix]
    except KeyError as error:
        raise TransactionReferenceParseError(
            f"Line {line_number}: {field_name} has unsupported signed-digit suffix {suffix!r} "
            f"in {value!r}."
        ) from error

    return sign, prefix + last_digit
