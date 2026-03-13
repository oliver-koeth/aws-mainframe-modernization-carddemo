from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.domain.auth import (
    InvalidCredentialsError,
    SessionNotFoundError,
    SessionStoreConsistencyError,
    UnauthorizedUserError,
)
from app.domain.users import UserName, UserRole, UserSecurityRecord
from app.models import default_store_document
from app.services import build_authentication_service, build_backend_state
from app.storage import write_store


def test_authenticate_matches_cosgn00c_uppercase_sign_on_semantics(tmp_path) -> None:
    backend_state = build_backend_state(tmp_path)
    payload = default_store_document()
    payload["users"] = [
        UserSecurityRecord(
            user_id="ADMIN001",
            name=UserName(first_name="ADMIN", last_name="USER"),
            password="PASSword",
            role=UserRole.ADMIN,
            user_type_code="A",
        ).model_dump(mode="python")
    ]
    write_store(backend_state.paths, payload)

    service = build_authentication_service(backend_state)
    authenticated_user = service.authenticate("admin001", "password")

    assert authenticated_user.user_id == "ADMIN001"
    assert authenticated_user.role is UserRole.ADMIN
    assert authenticated_user.user_type_code == "A"
    assert authenticated_user.first_name == "ADMIN"
    assert authenticated_user.last_name == "USER"


def test_authenticate_rejects_invalid_credentials_with_shared_message(tmp_path) -> None:
    backend_state = build_backend_state(tmp_path)
    payload = default_store_document()
    payload["users"] = [
        UserSecurityRecord(
            user_id="USER0001",
            name=UserName(first_name="CARD", last_name="USER"),
            password="PASSWORD",
            role=UserRole.USER,
            user_type_code="U",
        ).model_dump(mode="python")
    ]
    write_store(backend_state.paths, payload)

    service = build_authentication_service(backend_state)

    with pytest.raises(
        InvalidCredentialsError,
        match="Sign-on failed: invalid user ID or password.",
    ):
        service.authenticate("user0001", "wrongpwd")

    with pytest.raises(
        InvalidCredentialsError,
        match="Sign-on failed: invalid user ID or password.",
    ):
        service.authenticate("missing01", "PASSWORD")


def test_authenticate_supports_role_based_authorization(tmp_path) -> None:
    backend_state = build_backend_state(tmp_path)
    payload = default_store_document()
    payload["users"] = [
        UserSecurityRecord(
            user_id="USER0001",
            name=UserName(first_name="CARD", last_name="USER"),
            password="PASSWORD",
            role=UserRole.USER,
            user_type_code="U",
        ).model_dump(mode="python")
    ]
    write_store(backend_state.paths, payload)

    service = build_authentication_service(backend_state)

    with pytest.raises(
        UnauthorizedUserError,
        match="User 'USER0001' is not authorized for role 'admin'.",
    ):
        service.authenticate(
            "USER0001",
            "PASSWORD",
            required_role=UserRole.ADMIN,
        )


def test_lookup_session_resolves_session_to_authenticated_user(tmp_path) -> None:
    backend_state = build_backend_state(tmp_path)
    created_at = datetime(2026, 3, 13, 18, 30, tzinfo=timezone.utc)
    payload = default_store_document()
    payload["users"] = [
        UserSecurityRecord(
            user_id="ADMIN001",
            name=UserName(first_name="ADMIN", last_name="USER"),
            password="PASSWORD",
            role=UserRole.ADMIN,
            user_type_code="A",
        ).model_dump(mode="python")
    ]
    payload["operations"]["sessions"] = [
        {
            "session_id": "sess-001",
            "user_id": "ADMIN001",
            "created_at": created_at,
        }
    ]
    write_store(backend_state.paths, payload)

    service = build_authentication_service(backend_state)
    session = service.lookup_session("sess-001", required_role=UserRole.ADMIN)

    assert session.session_id == "sess-001"
    assert session.created_at == created_at
    assert session.user.user_id == "ADMIN001"
    assert session.user.role is UserRole.ADMIN


def test_lookup_session_rejects_missing_or_dangling_sessions(tmp_path) -> None:
    backend_state = build_backend_state(tmp_path)
    payload = default_store_document()
    payload["operations"]["sessions"] = [
        {
            "session_id": "dangling-001",
            "user_id": "UNKNOWN1",
        }
    ]
    write_store(backend_state.paths, payload)

    service = build_authentication_service(backend_state)

    with pytest.raises(SessionNotFoundError, match="Session 'missing' was not found."):
        service.lookup_session("missing")

    with pytest.raises(
        SessionStoreConsistencyError,
        match="Session references unknown user ID 'UNKNOWN1'.",
    ):
        service.lookup_session("dangling-001")
