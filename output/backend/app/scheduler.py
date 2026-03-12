"""Scheduler glue for future batch job execution."""

from __future__ import annotations

from app.jobs import get_registered_jobs


def get_schedule_snapshot() -> list[str]:
    """Expose the current scaffold scheduler inventory."""
    return get_registered_jobs()
