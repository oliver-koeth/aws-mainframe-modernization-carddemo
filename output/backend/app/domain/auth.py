"""Authentication and session lookup services derived from GNUCobol sign-on behavior."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.domain.users import UserRole, UserSecurityRecord
from app.models import StoragePaths
from app.storage import read_store


class AuthenticationError(RuntimeError):
    """Base error for authentication and authorization failures."""


class InvalidCredentialsError(AuthenticationError):
    """Raised when credentials do not match any persisted user record."""


class UnauthorizedUserError(AuthenticationError):
    """Raised when a valid user does not satisfy the requested role."""


class SessionLookupError(RuntimeError):
    """Base error for session lookup failures."""


class SessionNotFoundError(SessionLookupError):
    """Raised when no persisted session matches the requested session ID."""


class SessionStoreConsistencyError(SessionLookupError):
    """Raised when persisted session data cannot be resolved deterministically."""


class AuthenticatedUser(BaseModel):
    """Resolved user identity returned by the shared sign-on service."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    user_id: str = Field(min_length=1, max_length=8)
    user_type_code: str = Field(min_length=1, max_length=1)
    role: UserRole
    first_name: str = Field(min_length=1, max_length=20)
    last_name: str = Field(min_length=1, max_length=20)


class SessionRecord(BaseModel):
    """Minimal persisted session contract reserved under `operations.sessions`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1, max_length=8)
    created_at: datetime | None = None


class ResolvedSession(BaseModel):
    """Session lookup result with the resolved authenticated user."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str = Field(min_length=1)
    user: AuthenticatedUser
    created_at: datetime | None = None


class AuthenticationService:
    """Storage-backed authentication and session lookup behavior for Phase 1."""

    def __init__(self, paths: StoragePaths) -> None:
        self._paths = paths

    def authenticate(
        self,
        user_id: str,
        password: str,
        *,
        required_role: UserRole | None = None,
    ) -> AuthenticatedUser:
        """Validate credentials using the `COSGN00C` sign-on comparison rules."""
        normalized_user_id = _normalize_sign_on_value(user_id, width=8)
        normalized_password = _normalize_sign_on_value(password, width=8)

        for user_record in self._load_users():
            if (
                user_record.user_id == normalized_user_id
                and user_record.password.upper() == normalized_password
            ):
                authenticated_user = _to_authenticated_user(user_record)
                _assert_role(
                    authenticated_user,
                    required_role=required_role,
                )
                return authenticated_user

        raise InvalidCredentialsError(
            "Sign-on failed: invalid user ID or password."
        )

    def lookup_session(
        self,
        session_id: str,
        *,
        required_role: UserRole | None = None,
    ) -> ResolvedSession:
        """Resolve a persisted session record and its current user identity."""
        for session_record in self._load_sessions():
            if session_record.session_id != session_id:
                continue

            user_record = self._find_user_by_id(session_record.user_id)
            authenticated_user = _to_authenticated_user(user_record)
            _assert_role(
                authenticated_user,
                required_role=required_role,
            )
            return ResolvedSession(
                session_id=session_record.session_id,
                user=authenticated_user,
                created_at=session_record.created_at,
            )

        raise SessionNotFoundError(f"Session {session_id!r} was not found.")

    def _load_users(self) -> list[UserSecurityRecord]:
        store = read_store(self._paths)
        records: list[UserSecurityRecord] = []
        for index, raw_user in enumerate(store["users"], start=1):
            try:
                records.append(UserSecurityRecord.model_validate(raw_user))
            except ValidationError as error:
                raise SessionStoreConsistencyError(
                    f"Store user at index {index} is invalid: {error}"
                ) from error
        return records

    def _load_sessions(self) -> list[SessionRecord]:
        store = read_store(self._paths)
        records: list[SessionRecord] = []
        for index, raw_session in enumerate(store["operations"]["sessions"], start=1):
            try:
                records.append(SessionRecord.model_validate(raw_session))
            except ValidationError as error:
                raise SessionStoreConsistencyError(
                    f"Store session at index {index} is invalid: {error}"
                ) from error
        return records

    def _find_user_by_id(self, user_id: str) -> UserSecurityRecord:
        for user_record in self._load_users():
            if user_record.user_id == user_id:
                return user_record
        raise SessionStoreConsistencyError(
            f"Session references unknown user ID {user_id!r}."
        )


def _normalize_sign_on_value(value: str, *, width: int) -> str:
    """Mirror COBOL sign-on input normalization for fixed-width uppercase fields."""
    return value.upper()[:width]


def _to_authenticated_user(user_record: UserSecurityRecord) -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=user_record.user_id,
        user_type_code=user_record.user_type_code,
        role=user_record.role,
        first_name=user_record.name.first_name,
        last_name=user_record.name.last_name,
    )


def _assert_role(
    authenticated_user: AuthenticatedUser,
    *,
    required_role: UserRole | None,
) -> None:
    if required_role is None:
        return

    if authenticated_user.role != required_role:
        raise UnauthorizedUserError(
            f"User {authenticated_user.user_id!r} is not authorized for role "
            f"{required_role.value!r}."
        )
