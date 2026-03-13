"""Canonical user-security models derived from `CSUSR01Y`."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


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
    if len(line) > USER_SECURITY_RECORD_WIDTH:
        raise UserSecurityParseError(
            f"Line {line_number}: expected at most {USER_SECURITY_RECORD_WIDTH} characters, "
            f"received {len(line)}."
        )

    record = line.ljust(USER_SECURITY_RECORD_WIDTH)
    user_id = _required_text(_slice(record, 0, 8), "SEC-USR-ID", line_number)
    first_name = _required_text(_slice(record, 8, 20), "SEC-USR-FNAME", line_number)
    last_name = _required_text(_slice(record, 28, 20), "SEC-USR-LNAME", line_number)
    password = _required_text(_slice(record, 48, 8), "SEC-USR-PWD", line_number)
    user_type_code = _required_text(_slice(record, 56, 1), "SEC-USR-TYPE", line_number)
    filler = _optional_text(_slice(record, 57, 23))

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


def _slice(record: str, start: int, length: int) -> str:
    return record[start : start + length]


def _required_text(value: str, field_name: str, line_number: int) -> str:
    normalized = value.rstrip()
    if normalized == "":
        raise UserSecurityParseError(f"Line {line_number}: {field_name} is blank.")
    return normalized


def _optional_text(value: str) -> str | None:
    normalized = value.rstrip()
    return normalized or None


def _role_from_code(user_type_code: str) -> UserRole:
    return {
        "A": UserRole.ADMIN,
        "U": UserRole.USER,
    }[user_type_code]
