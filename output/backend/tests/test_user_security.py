from __future__ import annotations

import pytest

from app.domain.users import (
    USER_SECURITY_RECORD_WIDTH,
    UserRole,
    UserSecurityParseError,
    parse_user_security_record,
)


def test_parse_user_security_record_from_seed_line() -> None:
    record = parse_user_security_record(
        "ADMIN001ADMIN               USER                PASSWORDA",
    )

    assert record.user_id == "ADMIN001"
    assert record.name.first_name == "ADMIN"
    assert record.name.last_name == "USER"
    assert record.password == "PASSWORD"
    assert record.role is UserRole.ADMIN
    assert record.user_type_code == "A"
    assert record.filler is None


def test_parse_user_security_record_preserves_non_blank_filler() -> None:
    base_line = "USER0001CARD                USER                PASSWORDU"
    filler = "NOTES"

    record = parse_user_security_record(base_line + filler)

    assert len(base_line + filler) < USER_SECURITY_RECORD_WIDTH
    assert record.filler == filler
    assert record.role is UserRole.USER


@pytest.mark.parametrize(
    ("line", "expected_message"),
    [
        (
            "SHORT",
            "Line 1: SEC-USR-FNAME is blank.",
        ),
        (
            "ADMIN001ADMIN               USER                PASSWORDX",
            "Line 1: unsupported SEC-USR-TYPE 'X'; expected 'A' or 'U'.",
        ),
        (
            "TOO-LONG1ADMIN               USER                PASSWORDA" + ("X" * 23),
            "Line 1: expected at most 80 characters, received 81.",
        ),
    ],
)
def test_parse_user_security_record_rejects_malformed_lines(
    line: str,
    expected_message: str,
) -> None:
    with pytest.raises(UserSecurityParseError, match=expected_message):
        parse_user_security_record(line)
