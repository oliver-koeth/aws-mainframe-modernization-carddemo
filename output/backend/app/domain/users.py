"""Canonical user-security models derived from `CSUSR01Y`."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.fixed_width import optional_text, prepare_fixed_width_record, required_text, slice_field

USER_SECURITY_RECORD_WIDTH = 80


class UserSecurityParseError(ValueError):
    """Raised when a user-security line cannot be normalized deterministically."""


class UserRole(StrEnum):
    """Normalized role semantics from `SEC-USR-TYPE`."""

    ADMIN = "admin"
    USER = "user"


class UserName(BaseModel):
    """Normalized user name fields from the flat-file record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    first_name: str = Field(min_length=1, max_length=20)
    last_name: str = Field(min_length=1, max_length=20)


class UserSecurityRecord(BaseModel):
    """Canonical JSON representation of one `CSUSR01Y` record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    user_id: str = Field(min_length=1, max_length=8)
    name: UserName
    password: str = Field(min_length=1, max_length=8)
    role: UserRole
    user_type_code: str = Field(min_length=1, max_length=1)
    filler: str | None = None


def parse_user_security_record(line: str, *, line_number: int = 1) -> UserSecurityRecord:
    """Parse one `usrsec.dat` line into the canonical user-security model."""
    record = prepare_fixed_width_record(
        line,
        record_width=USER_SECURITY_RECORD_WIDTH,
        line_number=line_number,
        error_type=UserSecurityParseError,
    )
    user_id = required_text(
        slice_field(record, 0, 8),
        field_name="SEC-USR-ID",
        line_number=line_number,
        error_type=UserSecurityParseError,
    )
    first_name = required_text(
        slice_field(record, 8, 20),
        field_name="SEC-USR-FNAME",
        line_number=line_number,
        error_type=UserSecurityParseError,
    )
    last_name = required_text(
        slice_field(record, 28, 20),
        field_name="SEC-USR-LNAME",
        line_number=line_number,
        error_type=UserSecurityParseError,
    )
    password = required_text(
        slice_field(record, 48, 8),
        field_name="SEC-USR-PWD",
        line_number=line_number,
        error_type=UserSecurityParseError,
    )
    user_type_code = required_text(
        slice_field(record, 56, 1),
        field_name="SEC-USR-TYPE",
        line_number=line_number,
        error_type=UserSecurityParseError,
    )
    filler = optional_text(slice_field(record, 57, 23))

    try:
        role = _role_from_code(user_type_code)
    except KeyError as error:
        raise UserSecurityParseError(
            f"Line {line_number}: unsupported SEC-USR-TYPE {user_type_code!r}; expected 'A' or 'U'."
        ) from error

    return UserSecurityRecord(
        user_id=user_id,
        name=UserName(first_name=first_name, last_name=last_name),
        password=password,
        role=role,
        user_type_code=user_type_code,
        filler=filler,
    )
def _role_from_code(user_type_code: str) -> UserRole:
    return {
        "A": UserRole.ADMIN,
        "U": UserRole.USER,
    }[user_type_code]
