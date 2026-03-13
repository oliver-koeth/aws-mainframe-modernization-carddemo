from __future__ import annotations

import threading
import time
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from app.models import (
    STORE_SCHEMA_NAME,
    STORE_SCHEMA_VERSION,
    StoragePaths,
    default_store_document,
)
from app.storage import (
    StoreSchemaError,
    StorageLockTimeoutError,
    get_storage_targets,
    read_json_file,
    read_schedules,
    read_store,
    write_json_file,
    write_schedules,
    write_store,
)


def test_storage_targets_match_scaffold_paths(storage_paths: StoragePaths) -> None:
    assert get_storage_targets(storage_paths) == (
        str(storage_paths.store),
        str(storage_paths.schedules),
    )


def test_store_round_trip_restores_decimal_date_and_datetime(
    storage_paths: StoragePaths,
) -> None:
    payload = default_store_document()
    payload["accounts"] = [
        {
            "account_id": "0000000001",
            "balance": Decimal("10.55"),
            "statement_date": date(2026, 3, 12),
            "processed_at": datetime(2026, 3, 12, 19, 30, 45, tzinfo=timezone.utc),
            "entries": [
                {"amount": Decimal("1.25")},
                {"posted_on": date(2026, 3, 13)},
            ],
        }
    ]

    write_store(storage_paths, payload)

    assert read_store(storage_paths) == payload
    assert payload["metadata"] == {
        "schema_name": STORE_SCHEMA_NAME,
        "schema_version": STORE_SCHEMA_VERSION,
    }


def test_schedules_round_trip_uses_atomic_file_replacement(
    storage_paths: StoragePaths,
) -> None:
    payload = [
        {
            "job": "nightly",
            "next_run": datetime(2026, 3, 13, 1, 0, tzinfo=timezone.utc),
            "as_of": date(2026, 3, 12),
        }
    ]

    write_schedules(storage_paths, payload)

    assert read_schedules(storage_paths) == payload
    assert [item.name for item in storage_paths.schedules.parent.iterdir()] == [
        "schedules.json"
    ]
    file_text = storage_paths.schedules.read_text(encoding="utf-8")
    assert "__type__" in file_text
    assert ".tmp" not in file_text


def test_read_json_file_returns_defaults_for_missing_scaffold_files(
    tmp_path: Path,
) -> None:
    assert read_json_file(tmp_path / "missing-store.json", default={}) == {}
    assert read_json_file(tmp_path / "missing-schedules.json", default=[]) == []


def test_read_store_returns_default_document_for_missing_or_empty_store(
    storage_paths: StoragePaths,
) -> None:
    assert read_store(storage_paths) == default_store_document()

    storage_paths.store.write_text("", encoding="utf-8")

    assert read_store(storage_paths) == default_store_document()


def test_read_store_rejects_unsupported_schema_version(
    storage_paths: StoragePaths,
) -> None:
    payload = default_store_document()
    payload["metadata"]["schema_version"] = 99
    write_json_file(storage_paths.store, payload)

    with pytest.raises(
        StoreSchemaError,
        match="Unsupported store schema version",
    ):
        read_store(storage_paths)


def test_write_json_file_serializes_concurrent_updates(
    storage_paths: StoragePaths,
) -> None:
    tmp_path = storage_paths.store.parent
    write_store(storage_paths, default_store_document())
    write_started = threading.Event()
    release_write = threading.Event()
    original_replace = type(storage_paths.store).replace

    def delayed_replace(self, target) -> None:
        if self.parent == tmp_path and Path(target) == storage_paths.store:
            write_started.set()
            release_write.wait(timeout=2)
        original_replace(self, target)

    results: list[str] = []

    def write_first() -> None:
        payload = default_store_document()
        payload["users"] = [{"user_id": "first"}]
        write_store(storage_paths, payload)
        results.append("first")

    def write_second() -> None:
        payload = default_store_document()
        payload["users"] = [{"user_id": "second"}]
        write_store(storage_paths, payload)
        results.append("second")

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(type(storage_paths.store), "replace", delayed_replace)
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
    assert read_store(storage_paths)["users"] == [{"user_id": "second"}]
    assert [item.name for item in tmp_path.iterdir()] == ["store.json"]


def test_write_json_file_raises_deterministic_timeout_when_lock_is_held(
    tmp_path: Path,
) -> None:
    target = tmp_path / "store.json"
    lock_path = target.with_name(f"{target.name}.lock")
    tmp_path.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("locked", encoding="utf-8")

    start = time.monotonic()
    with pytest.raises(
        StorageLockTimeoutError,
        match="Timed out acquiring storage lock",
    ):
        write_json_file(target, {"status": "blocked"})
    elapsed = time.monotonic() - start

    assert elapsed >= 1
    assert lock_path.exists()
