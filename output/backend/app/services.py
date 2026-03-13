"""Shared service wiring for the CardDemo backend workspace."""

from __future__ import annotations

from pathlib import Path

from app.domain.auth import AuthenticationService
from app.domain.lookups import LookupService
from app.domain.posting import PostingService
from app.domain.transactions import TransactionService
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


def build_lookup_service(state: BackendState) -> LookupService:
    """Create the shared account/customer/card lookup service."""
    return LookupService(state.paths)


def build_transaction_service(state: BackendState) -> TransactionService:
    """Create the shared transaction validation and creation service."""
    return TransactionService(state.paths)


def build_posting_service(state: BackendState) -> PostingService:
    """Create the shared posting service for online and batch payment flows."""
    return PostingService(state.paths)
