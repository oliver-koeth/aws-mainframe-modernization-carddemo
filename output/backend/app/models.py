"""Shared typed models for the Phase 0 backend scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class StoragePaths:
    """Filesystem locations for the scaffold JSON stores."""

    store: Path
    schedules: Path


@dataclass(slots=True)
class BackendState:
    """Mutable in-memory state for scaffold services."""

    paths: StoragePaths
    jobs: list[str] = field(default_factory=list)
