"""Shared service wiring for the CardDemo backend workspace."""

from __future__ import annotations

from pathlib import Path

from app.domain.auth import AuthenticationService
from app.models import BackendState, StoragePaths


def build_backend_state(root: Path) -> BackendState:
    """Create the default scaffold state rooted at the backend workspace."""
    return BackendState(
        paths=StoragePaths(
            store=root / "store.json",
            schedules=root / "schedules.json",
        )
    )


def build_authentication_service(state: BackendState) -> AuthenticationService:
    """Create the shared auth/session service bound to the backend store paths."""
    return AuthenticationService(state.paths)
