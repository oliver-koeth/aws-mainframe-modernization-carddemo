from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from app.fixed_width import (
    optional_datetime,
    optional_text,
    prepare_fixed_width_record,
    required_compact_datetime,
    required_date,
    required_datetime,
    required_digits,
    required_int,
    required_signed_amount,
    required_text,
    slice_field,
)


class FixedWidthParseError(ValueError):
    pass


def test_prepare_fixed_width_record_right_pads_line_sequential_rows() -> None:
    record = prepare_fixed_width_record(
        "ABC",
        record_width=5,
        line_number=7,
        error_type=FixedWidthParseError,
    )

    assert record == "ABC  "
    assert slice_field(record, 1, 3) == "BC "


def test_prepare_fixed_width_record_rejects_oversized_lines() -> None:
    with pytest.raises(FixedWidthParseError, match=r"Line 2: expected at most 4 characters, received 5\."):
        prepare_fixed_width_record(
            "ABCDE",
            record_width=4,
            line_number=2,
            error_type=FixedWidthParseError,
        )


def test_text_and_numeric_helpers_normalize_expected_values() -> None:
    assert required_text(
        "FIELD   ",
        field_name="TEST-FIELD",
        line_number=1,
        error_type=FixedWidthParseError,
    ) == "FIELD"
    assert optional_text("   ") is None
    assert required_digits(
        "00123",
        field_name="TEST-DIGITS",
        line_number=1,
        error_type=FixedWidthParseError,
    ) == "00123"
    assert required_int(
        "007",
        field_name="TEST-INT",
        line_number=1,
        error_type=FixedWidthParseError,
    ) == 7


def test_date_and_datetime_helpers_parse_supported_formats() -> None:
    assert required_date(
        "2026-03-13",
        field_name="TEST-DATE",
        line_number=1,
        error_type=FixedWidthParseError,
    ) == date(2026, 3, 13)
    assert required_datetime(
        "2026-03-13T16:20:00.123456",
        field_name="TEST-TS",
        line_number=1,
        error_type=FixedWidthParseError,
    ) == datetime(2026, 3, 13, 16, 20, 0, 123456)
    assert optional_datetime(
        "2026-03-13T16:20:00",
        field_name="TEST-OPTIONAL-TS",
        line_number=1,
        error_type=FixedWidthParseError,
    ) == datetime(2026, 3, 13, 16, 20, 0)
    assert optional_datetime(
        "   ",
        field_name="TEST-OPTIONAL-TS",
        line_number=1,
        error_type=FixedWidthParseError,
    ) is None
    assert required_compact_datetime(
        "2026-03-13 16:20:00",
        field_name="TEST-COMPACT-TS",
        line_number=1,
        error_type=FixedWidthParseError,
    ) == datetime(2026, 3, 13, 16, 20, 0)


def test_required_signed_amount_decodes_signed_and_unsigned_cobol_values() -> None:
    assert required_signed_amount(
        "00000001234{",
        field_name="TEST-AMOUNT",
        line_number=1,
        error_type=FixedWidthParseError,
    ) == Decimal("123.40")
    assert required_signed_amount(
        "00000001234N",
        field_name="TEST-AMOUNT",
        line_number=1,
        error_type=FixedWidthParseError,
    ) == Decimal("-123.45")
    assert required_signed_amount(
        "000000001234",
        field_name="TEST-UNSIGNED",
        line_number=1,
        error_type=FixedWidthParseError,
        expected_width=12,
        allow_unsigned_final_digit=True,
        prefix_error_detail="must contain only digits before the sign nibble",
    ) == Decimal("12.34")


@pytest.mark.parametrize(
    ("raw_value", "expected_message"),
    [
        ("     ", r"Line 4: TEST-FIELD is blank\."),
        ("12A", r"Line 4: TEST-DIGITS must contain only digits, received '12A'\."),
        (
            "00012",
            r"Line 4: TEST-WIDTH must be 6 characters wide, received 5\.",
        ),
        (
            "12A{",
            r"Line 4: TEST-SIGNED must contain digits before the signed suffix, received '12A\{'\.",
        ),
        (
            "12345Z",
            r"Line 4: TEST-SIGNED has unsupported signed-digit suffix 'Z' in '12345Z'\.",
        ),
        (
            "2026/03/13",
            r"Line 4: TEST-DATE must be YYYY-MM-DD, received '2026/03/13'\.",
        ),
        (
            "2026-13-40T16:20:00",
            r"Line 4: TEST-TS must be ISO timestamp text, received '2026-13-40T16:20:00'\.",
        ),
    ],
)
def test_shared_helpers_fail_deterministically(raw_value: str, expected_message: str) -> None:
    def call() -> object:
        if expected_message.startswith("Line 4: TEST-FIELD"):
            return required_text(
                raw_value,
                field_name="TEST-FIELD",
                line_number=4,
                error_type=FixedWidthParseError,
            )
        if expected_message.startswith("Line 4: TEST-DIGITS"):
            return required_digits(
                raw_value,
                field_name="TEST-DIGITS",
                line_number=4,
                error_type=FixedWidthParseError,
            )
        if expected_message.startswith("Line 4: TEST-WIDTH"):
            return required_signed_amount(
                raw_value,
                field_name="TEST-WIDTH",
                line_number=4,
                error_type=FixedWidthParseError,
                expected_width=6,
                allow_unsigned_final_digit=True,
                prefix_error_detail="must contain only digits before the sign nibble",
            )
        if expected_message.startswith("Line 4: TEST-SIGNED must contain"):
            return required_signed_amount(
                raw_value,
                field_name="TEST-SIGNED",
                line_number=4,
                error_type=FixedWidthParseError,
            )
        if expected_message.startswith("Line 4: TEST-SIGNED has unsupported"):
            return required_signed_amount(
                raw_value,
                field_name="TEST-SIGNED",
                line_number=4,
                error_type=FixedWidthParseError,
            )
        if expected_message.startswith("Line 4: TEST-DATE"):
            return required_date(
                raw_value,
                field_name="TEST-DATE",
                line_number=4,
                error_type=FixedWidthParseError,
            )
        return required_datetime(
            raw_value,
            field_name="TEST-TS",
            line_number=4,
            error_type=FixedWidthParseError,
        )

    with pytest.raises(FixedWidthParseError, match=expected_message):
        call()
