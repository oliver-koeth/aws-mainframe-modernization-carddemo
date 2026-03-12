"""Service layer placeholders for the Phase 0 scaffold."""

from __future__ import annotations

from pathlib import Path

from app.models import BackendState, StoragePaths


def build_backend_state(root: Path) -> BackendState:
    """Create the default scaffold state rooted at the backend workspace."""
    return BackendState(
        paths=StoragePaths(
            store=root / "store.json",
            schedules=root / "schedules.json",
        )
    )
