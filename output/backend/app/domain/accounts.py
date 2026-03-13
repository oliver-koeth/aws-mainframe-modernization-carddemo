"""Canonical account, card, and xref models derived from `CVACT01Y`-`CVACT03Y`."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


ACCOUNT_RECORD_WIDTH = 300
CARD_RECORD_WIDTH = 150
CARD_ACCOUNT_XREF_RECORD_WIDTH = 50

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
    if len(line) > ACCOUNT_RECORD_WIDTH:
        raise AccountCardParseError(
            f"Line {line_number}: expected at most {ACCOUNT_RECORD_WIDTH} characters, "
            f"received {len(line)}."
        )

    record = line.ljust(ACCOUNT_RECORD_WIDTH)
    account_id = _required_digits(_slice(record, 0, 11), "ACCT-ID", line_number)
    active_status_code = _required_text(_slice(record, 11, 1), "ACCT-ACTIVE-STATUS", line_number)
    current_balance = _required_signed_amount(
        _slice(record, 12, 12),
        "ACCT-CURR-BAL",
        line_number,
    )
    credit_limit = _required_signed_amount(
        _slice(record, 24, 12),
        "ACCT-CREDIT-LIMIT",
        line_number,
    )
    cash_credit_limit = _required_signed_amount(
        _slice(record, 36, 12),
        "ACCT-CASH-CREDIT-LIMIT",
        line_number,
    )
    open_date = _required_date(_slice(record, 48, 10), "ACCT-OPEN-DATE", line_number)
    expiration_date = _required_date(_slice(record, 58, 10), "ACCT-EXPIRAION-DATE", line_number)
    reissue_date = _required_date(_slice(record, 68, 10), "ACCT-REISSUE-DATE", line_number)
    current_cycle_credit = _required_signed_amount(
        _slice(record, 78, 12),
        "ACCT-CURR-CYC-CREDIT",
        line_number,
    )
    current_cycle_debit = _required_signed_amount(
        _slice(record, 90, 12),
        "ACCT-CURR-CYC-DEBIT",
        line_number,
    )
    billing_postal_code = _required_text(_slice(record, 102, 10), "ACCT-ADDR-ZIP", line_number)
    group_id = _optional_text(_slice(record, 112, 10))
    filler = _optional_text(_slice(record, 122, 178))

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
    if len(line) > CARD_RECORD_WIDTH:
        raise AccountCardParseError(
            f"Line {line_number}: expected at most {CARD_RECORD_WIDTH} characters, "
            f"received {len(line)}."
        )

    record = line.ljust(CARD_RECORD_WIDTH)
    card_number = _required_digits(_slice(record, 0, 16), "CARD-NUM", line_number)
    account_id = _required_digits(_slice(record, 16, 11), "CARD-ACCT-ID", line_number)
    cvv_code = _required_digits(_slice(record, 27, 3), "CARD-CVV-CD", line_number)
    embossed_name = _required_text(_slice(record, 30, 50), "CARD-EMBOSSED-NAME", line_number)
    expiration_date = _required_date(_slice(record, 80, 10), "CARD-EXPIRAION-DATE", line_number)
    active_status_code = _required_text(_slice(record, 90, 1), "CARD-ACTIVE-STATUS", line_number)
    filler = _optional_text(_slice(record, 91, 59))

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
    if len(line) > CARD_ACCOUNT_XREF_RECORD_WIDTH:
        raise AccountCardParseError(
            f"Line {line_number}: expected at most {CARD_ACCOUNT_XREF_RECORD_WIDTH} characters, "
            f"received {len(line)}."
        )

    record = line.ljust(CARD_ACCOUNT_XREF_RECORD_WIDTH)
    card_number = _required_digits(_slice(record, 0, 16), "XREF-CARD-NUM", line_number)
    customer_id = _required_digits(_slice(record, 16, 9), "XREF-CUST-ID", line_number)
    account_id = _required_digits(_slice(record, 25, 11), "XREF-ACCT-ID", line_number)
    filler = _optional_text(_slice(record, 36, 14))

    return CardAccountXrefRecord(
        card_number=card_number,
        customer_id=customer_id,
        account_id=account_id,
        filler=filler,
    )


def _slice(record: str, start: int, length: int) -> str:
    return record[start : start + length]


def _required_text(value: str, field_name: str, line_number: int) -> str:
    normalized = value.rstrip()
    if normalized == "":
        raise AccountCardParseError(f"Line {line_number}: {field_name} is blank.")
    return normalized


def _optional_text(value: str) -> str | None:
    normalized = value.rstrip()
    return normalized or None


def _required_digits(value: str, field_name: str, line_number: int) -> str:
    normalized = _required_text(value, field_name, line_number)
    if not normalized.isdigit():
        raise AccountCardParseError(
            f"Line {line_number}: {field_name} must contain only digits, received {normalized!r}."
        )
    return normalized


def _required_date(value: str, field_name: str, line_number: int) -> date:
    normalized = _required_text(value, field_name, line_number)
    try:
        return date.fromisoformat(normalized)
    except ValueError as error:
        raise AccountCardParseError(
            f"Line {line_number}: {field_name} must be YYYY-MM-DD, received {normalized!r}."
        ) from error


def _required_signed_amount(value: str, field_name: str, line_number: int) -> Decimal:
    normalized = _required_text(value, field_name, line_number)
    if len(normalized) != 12:
        raise AccountCardParseError(
            f"Line {line_number}: {field_name} must be 12 characters wide, "
            f"received {len(normalized)}."
        )
    if not normalized[:-1].isdigit():
        raise AccountCardParseError(
            f"Line {line_number}: {field_name} must contain only digits before the sign nibble, "
            f"received {normalized!r}."
        )

    final_char = normalized[-1]
    if final_char.isdigit():
        digits = normalized
        sign = 1
    else:
        try:
            signed_digit, sign = _COBOL_SIGNED_DIGIT_MAP[final_char]
        except KeyError as error:
            raise AccountCardParseError(
                f"Line {line_number}: {field_name} has unsupported signed-digit suffix "
                f"{final_char!r} in {normalized!r}."
            ) from error
        digits = f"{normalized[:-1]}{signed_digit}"

    amount = Decimal(digits).scaleb(-2)
    return amount if sign > 0 else -amount


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
