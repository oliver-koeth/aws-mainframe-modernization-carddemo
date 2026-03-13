"""Shared parsing primitives for fixed-width GNUCobol flat files."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

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


def prepare_fixed_width_record(
    line: str,
    *,
    record_width: int,
    line_number: int,
    error_type: type[ValueError],
) -> str:
    """Right-pad line-sequential records to their logical copybook width."""
    if len(line) > record_width:
        raise error_type(
            f"Line {line_number}: expected at most {record_width} characters, received {len(line)}."
        )
    return line.ljust(record_width)


def slice_field(record: str, start: int, length: int) -> str:
    """Return one fixed-width field slice from a padded record."""
    return record[start : start + length]


def required_text(
    value: str,
    *,
    field_name: str,
    line_number: int,
    error_type: type[ValueError],
) -> str:
    """Trim trailing filler and reject blank required text fields."""
    normalized = value.rstrip()
    if normalized == "":
        raise error_type(f"Line {line_number}: {field_name} is blank.")
    return normalized


def optional_text(value: str) -> str | None:
    """Trim trailing filler and normalize blank optional text to None."""
    normalized = value.rstrip()
    return normalized or None


def required_digits(
    value: str,
    *,
    field_name: str,
    line_number: int,
    error_type: type[ValueError],
) -> str:
    """Reject non-digit fixed-width identifiers while preserving leading zeroes."""
    normalized = required_text(
        value,
        field_name=field_name,
        line_number=line_number,
        error_type=error_type,
    )
    if not normalized.isdigit():
        raise error_type(
            f"Line {line_number}: {field_name} must contain only digits, received {normalized!r}."
        )
    return normalized


def required_int(
    value: str,
    *,
    field_name: str,
    line_number: int,
    error_type: type[ValueError],
) -> int:
    """Parse a required numeric field as an integer."""
    return int(
        required_digits(
            value,
            field_name=field_name,
            line_number=line_number,
            error_type=error_type,
        )
    )


def required_date(
    value: str,
    *,
    field_name: str,
    line_number: int,
    error_type: type[ValueError],
) -> date:
    """Parse a required ISO date field."""
    normalized = required_text(
        value,
        field_name=field_name,
        line_number=line_number,
        error_type=error_type,
    )
    try:
        return date.fromisoformat(normalized)
    except ValueError as error:
        raise error_type(
            f"Line {line_number}: {field_name} must be YYYY-MM-DD, received {normalized!r}."
        ) from error


def required_datetime(
    value: str,
    *,
    field_name: str,
    line_number: int,
    error_type: type[ValueError],
) -> datetime:
    """Parse a required ISO datetime field."""
    normalized = required_text(
        value,
        field_name=field_name,
        line_number=line_number,
        error_type=error_type,
    )
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as error:
        raise error_type(
            f"Line {line_number}: {field_name} must be ISO timestamp text, received {normalized!r}."
        ) from error


def optional_datetime(
    value: str,
    *,
    field_name: str,
    line_number: int,
    error_type: type[ValueError],
) -> datetime | None:
    """Parse an optional ISO datetime field."""
    normalized = value.rstrip()
    if normalized == "":
        return None
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as error:
        raise error_type(
            f"Line {line_number}: {field_name} must be ISO timestamp text, received {normalized!r}."
        ) from error


def required_compact_datetime(
    value: str,
    *,
    field_name: str,
    line_number: int,
    error_type: type[ValueError],
) -> datetime:
    """Parse a required second-resolution runtime timestamp."""
    normalized = required_text(
        value,
        field_name=field_name,
        line_number=line_number,
        error_type=error_type,
    )
    try:
        return datetime.strptime(normalized, "%Y-%m-%d %H:%M:%S")
    except ValueError as error:
        raise error_type(
            f"Line {line_number}: {field_name} must be YYYY-MM-DD HH:MM:SS, received {normalized!r}."
        ) from error


def required_signed_amount(
    value: str,
    *,
    field_name: str,
    line_number: int,
    error_type: type[ValueError],
    implied_decimal_places: int = 2,
    expected_width: int | None = None,
    allow_unsigned_final_digit: bool = False,
    prefix_error_detail: str = "must contain digits before the signed suffix",
    suffix_error_detail: str = "has unsupported signed-digit suffix",
) -> Decimal:
    """Decode COBOL signed zoned-decimal text into Decimal."""
    normalized = required_text(
        value,
        field_name=field_name,
        line_number=line_number,
        error_type=error_type,
    )
    if expected_width is not None and len(normalized) != expected_width:
        raise error_type(
            f"Line {line_number}: {field_name} must be {expected_width} characters wide, "
            f"received {len(normalized)}."
        )

    digits, sign = decode_signed_digits(
        normalized,
        field_name=field_name,
        line_number=line_number,
        error_type=error_type,
        allow_unsigned_final_digit=allow_unsigned_final_digit,
        prefix_error_detail=prefix_error_detail,
        suffix_error_detail=suffix_error_detail,
    )
    amount = Decimal(digits).scaleb(-implied_decimal_places)
    return amount if sign > 0 else -amount


def decode_signed_digits(
    value: str,
    *,
    field_name: str,
    line_number: int,
    error_type: type[ValueError],
    allow_unsigned_final_digit: bool = False,
    prefix_error_detail: str = "must contain digits before the signed suffix",
    suffix_error_detail: str = "has unsupported signed-digit suffix",
) -> tuple[str, int]:
    """Decode a COBOL signed-digit suffix into unsigned digits and sign."""
    prefix = value[:-1]
    suffix = value[-1]
    if not prefix.isdigit():
        raise error_type(
            f"Line {line_number}: {field_name} {prefix_error_detail}, received {value!r}."
        )

    if suffix.isdigit():
        if allow_unsigned_final_digit:
            return value, 1
        raise error_type(f"Line {line_number}: {field_name} {suffix_error_detail} {suffix!r} in {value!r}.")

    try:
        last_digit, sign = _COBOL_SIGNED_DIGIT_MAP[suffix]
    except KeyError as error:
        raise error_type(
            f"Line {line_number}: {field_name} {suffix_error_detail} {suffix!r} in {value!r}."
        ) from error

    return prefix + last_digit, sign
