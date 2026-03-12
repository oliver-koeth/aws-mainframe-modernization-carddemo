"""JSON storage placeholders for the Phase 0 scaffold."""

from __future__ import annotations

from app.models import StoragePaths


def get_storage_targets(paths: StoragePaths) -> tuple[str, str]:
    """Return the current storage file targets for service wiring."""
    return (str(paths.store), str(paths.schedules))
