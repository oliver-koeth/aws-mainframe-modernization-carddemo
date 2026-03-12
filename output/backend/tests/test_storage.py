from __future__ import annotations

import threading
import time
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from app.models import StoragePaths
from app.storage import (
    StorageLockTimeoutError,
    get_storage_targets,
    read_json_file,
    read_schedules,
    read_store,
    write_json_file,
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


def test_write_json_file_serializes_concurrent_updates(tmp_path) -> None:
    paths = StoragePaths(
        store=tmp_path / "store.json",
        schedules=tmp_path / "schedules.json",
    )
    write_started = threading.Event()
    release_write = threading.Event()
    original_replace = type(paths.store).replace

    def delayed_replace(self, target) -> None:
        if self.parent == tmp_path and Path(target) == paths.store:
            write_started.set()
            release_write.wait(timeout=2)
        original_replace(self, target)

    results: list[str] = []

    def write_first() -> None:
        write_store(paths, {"writer": "first"})
        results.append("first")

    def write_second() -> None:
        write_store(paths, {"writer": "second"})
        results.append("second")

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(type(paths.store), "replace", delayed_replace)
        first = threading.Thread(target=write_first)
        second = threading.Thread(target=write_second)

        first.start()
        assert write_started.wait(timeout=2)
        second.start()
        time.sleep(0.2)
        release_write.set()
        first.join(timeout=2)
        second.join(timeout=2)

    assert not first.is_alive()
    assert not second.is_alive()
    assert sorted(results) == ["first", "second"]
    assert read_store(paths) == {"writer": "second"}
    assert [item.name for item in tmp_path.iterdir()] == ["store.json"]


def test_write_json_file_raises_deterministic_timeout_when_lock_is_held(tmp_path) -> None:
    target = tmp_path / "store.json"
    lock_path = target.with_name(f"{target.name}.lock")
    tmp_path.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("locked", encoding="utf-8")

    start = time.monotonic()
    with pytest.raises(StorageLockTimeoutError, match="Timed out acquiring storage lock"):
        write_json_file(target, {"status": "blocked"})
    elapsed = time.monotonic() - start

    assert elapsed >= 1
    assert lock_path.exists()
