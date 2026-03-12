"""Shared JSON persistence primitives for the Phase 0 scaffold."""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from app.models import StoragePaths
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, TypeAlias, cast


def get_storage_targets(paths: StoragePaths) -> tuple[str, str]:
    """Return the current storage file targets for service wiring."""
    return (str(paths.store), str(paths.schedules))


JsonScalar: TypeAlias = None | bool | int | float | str
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
StorageScalar: TypeAlias = JsonScalar | Decimal | date | datetime
StorageValue: TypeAlias = StorageScalar | list["StorageValue"] | dict[str, "StorageValue"]

_TYPE_KEY = "__type__"
_VALUE_KEY = "value"
_DECIMAL_TYPE = "decimal"
_DATE_TYPE = "date"
_DATETIME_TYPE = "datetime"


def read_store(paths: StoragePaths) -> StorageValue:
    """Load application data from the scaffold store file."""
    return read_json_file(paths.store, default={})


def write_store(paths: StoragePaths, payload: StorageValue) -> None:
    """Persist application data to the scaffold store file atomically."""
    write_json_file(paths.store, payload)


def read_schedules(paths: StoragePaths) -> StorageValue:
    """Load schedule declarations from the scaffold schedules file."""
    return read_json_file(paths.schedules, default=[])


def write_schedules(paths: StoragePaths, payload: StorageValue) -> None:
    """Persist schedule declarations to the scaffold schedules file atomically."""
    write_json_file(paths.schedules, payload)


def read_json_file(path: Path, *, default: StorageValue) -> StorageValue:
    """Load JSON content from disk and restore supported typed values."""
    if not path.exists():
        return default

    with path.open("r", encoding="utf-8") as handle:
        raw_value = cast(JsonValue, json.load(handle))

    return _decode_typed_values(raw_value)


def write_json_file(path: Path, payload: StorageValue) -> None:
    """Write JSON content atomically using a temp file and rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded_payload = _encode_typed_values(payload)

    with NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(encoded_payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        temp_path = Path(handle.name)

    temp_path.replace(path)


def _encode_typed_values(value: Any) -> JsonValue:
    """Convert Python values into JSON-safe scaffold payloads."""
    if isinstance(value, Decimal):
        return {_TYPE_KEY: _DECIMAL_TYPE, _VALUE_KEY: str(value)}

    if isinstance(value, datetime):
        return {_TYPE_KEY: _DATETIME_TYPE, _VALUE_KEY: value.isoformat()}

    if isinstance(value, date):
        return {_TYPE_KEY: _DATE_TYPE, _VALUE_KEY: value.isoformat()}

    if isinstance(value, dict):
        return {
            str(key): _encode_typed_values(nested_value)
            for key, nested_value in value.items()
        }

    if isinstance(value, list):
        return [_encode_typed_values(item) for item in value]

    if value is None or isinstance(value, bool | int | float | str):
        return value

    raise TypeError(f"Unsupported JSON storage value: {type(value)!r}")


def _decode_typed_values(value: JsonValue) -> StorageValue:
    """Restore supported typed values from scaffold JSON payloads."""
    if isinstance(value, dict):
        type_name = value.get(_TYPE_KEY)
        encoded_value = value.get(_VALUE_KEY)
        if type_name == _DECIMAL_TYPE and isinstance(encoded_value, str):
            return Decimal(encoded_value)
        if type_name == _DATE_TYPE and isinstance(encoded_value, str):
            return date.fromisoformat(encoded_value)
        if type_name == _DATETIME_TYPE and isinstance(encoded_value, str):
            return datetime.fromisoformat(encoded_value)

        return {
            key: _decode_typed_values(nested_value)
            for key, nested_value in value.items()
        }

    if isinstance(value, list):
        return [_decode_typed_values(item) for item in value]

    return value
