from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from app.models import StoragePaths
from app.storage import (
    get_storage_targets,
    read_json_file,
    read_schedules,
    read_store,
    write_schedules,
    write_store,
)


def test_storage_targets_match_scaffold_paths(tmp_path) -> None:
    paths = StoragePaths(
        store=tmp_path / "store.json",
        schedules=tmp_path / "schedules.json",
    )

    assert get_storage_targets(paths) == (
        str(tmp_path / "store.json"),
        str(tmp_path / "schedules.json"),
    )


def test_store_round_trip_restores_decimal_date_and_datetime(tmp_path) -> None:
    paths = StoragePaths(
        store=tmp_path / "store.json",
        schedules=tmp_path / "schedules.json",
    )
    payload = {
        "balance": Decimal("10.55"),
        "statement_date": date(2026, 3, 12),
        "processed_at": datetime(2026, 3, 12, 19, 30, 45, tzinfo=timezone.utc),
        "entries": [
            {"amount": Decimal("1.25")},
            {"posted_on": date(2026, 3, 13)},
        ],
    }

    write_store(paths, payload)

    assert read_store(paths) == payload


def test_schedules_round_trip_uses_atomic_file_replacement(tmp_path) -> None:
    paths = StoragePaths(
        store=tmp_path / "store.json",
        schedules=tmp_path / "schedules.json",
    )
    payload = [
        {
            "job": "nightly",
            "next_run": datetime(2026, 3, 13, 1, 0, tzinfo=timezone.utc),
            "as_of": date(2026, 3, 12),
        }
    ]

    write_schedules(paths, payload)

    assert read_schedules(paths) == payload
    assert [item.name for item in tmp_path.iterdir()] == ["schedules.json"]
    file_text = paths.schedules.read_text(encoding="utf-8")
    assert "__type__" in file_text
    assert ".tmp" not in file_text


def test_read_json_file_returns_defaults_for_missing_scaffold_files(tmp_path) -> None:
    assert read_json_file(tmp_path / "missing-store.json", default={}) == {}
    assert read_json_file(tmp_path / "missing-schedules.json", default=[]) == []
