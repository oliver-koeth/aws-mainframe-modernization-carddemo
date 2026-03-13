"""Shared JSON persistence primitives for the Phase 0 scaffold."""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from json import JSONDecodeError
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Iterator, TypeAlias, cast

from app.models import (
    STORE_COLLECTION_NAMES,
    STORE_OPERATION_COLLECTION_NAMES,
    STORE_SCHEMA_NAME,
    SUPPORTED_STORE_SCHEMA_VERSIONS,
    StoragePaths,
    StoreDocument,
    default_store_document,
)


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
_LOCK_SUFFIX = ".lock"
_LOCK_TIMEOUT_SECONDS = 1.0
_LOCK_POLL_INTERVAL_SECONDS = 0.05


class StorageLockTimeoutError(RuntimeError):
    """Raised when a scaffold storage write cannot acquire its shared lock."""


class StoreSchemaError(RuntimeError):
    """Raised when `store.json` does not match the supported schema contract."""


def read_store(paths: StoragePaths) -> StoreDocument:
    """Load application data from the canonical store file."""
    payload = read_json_file(
        paths.store,
        default=cast(StorageValue, default_store_document()),
    )
    return _validate_store_document(payload)


def write_store(paths: StoragePaths, payload: StoreDocument) -> None:
    """Persist application data to the canonical store file atomically."""
    _validate_store_document(payload)
    write_json_file(paths.store, cast(StorageValue, payload))


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
        try:
            raw_value = cast(JsonValue, json.load(handle))
        except JSONDecodeError as error:
            handle.seek(0)
            if handle.read().strip() == "":
                return default
            raise error

    return _decode_typed_values(raw_value)


def write_json_file(path: Path, payload: StorageValue) -> None:
    """Write JSON content atomically using a shared lock, temp file, and rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded_payload = _encode_typed_values(payload)

    with _acquire_write_lock(path):
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


@contextmanager
def _acquire_write_lock(path: Path) -> Iterator[None]:
    """Serialize writes per storage file with a same-directory lock file."""
    lock_path = _lock_path_for(path)
    deadline = time.monotonic() + _LOCK_TIMEOUT_SECONDS

    while True:
        try:
            descriptor = os.open(
                lock_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o600,
            )
            break
        except FileExistsError as error:
            if time.monotonic() >= deadline:
                raise StorageLockTimeoutError(
                    f"Timed out acquiring storage lock for {path}"
                ) from error
            time.sleep(_LOCK_POLL_INTERVAL_SECONDS)

    try:
        os.close(descriptor)
        yield
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _lock_path_for(path: Path) -> Path:
    """Place the lock file next to the target JSON file."""
    return path.with_name(f"{path.name}{_LOCK_SUFFIX}")


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


def _validate_store_document(payload: object) -> StoreDocument:
    """Validate the canonical top-level `store.json` envelope."""
    if not isinstance(payload, dict):
        raise StoreSchemaError("Store payload must be a JSON object")

    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        raise StoreSchemaError("Store metadata must be present")

    schema_name = metadata.get("schema_name")
    if schema_name != STORE_SCHEMA_NAME:
        raise StoreSchemaError(
            f"Unsupported store schema name: {schema_name!r}"
        )

    schema_version = metadata.get("schema_version")
    if (
        not isinstance(schema_version, int)
        or schema_version not in SUPPORTED_STORE_SCHEMA_VERSIONS
    ):
        raise StoreSchemaError(
            f"Unsupported store schema version: {schema_version!r}"
        )

    for collection_name in STORE_COLLECTION_NAMES:
        collection = payload.get(collection_name)
        if not isinstance(collection, list):
            raise StoreSchemaError(
                f"Store collection {collection_name!r} must be a list"
            )

    operations = payload.get("operations")
    if not isinstance(operations, dict):
        raise StoreSchemaError("Store operations collection must be present")

    for collection_name in STORE_OPERATION_COLLECTION_NAMES:
        collection = operations.get(collection_name)
        if not isinstance(collection, list):
            raise StoreSchemaError(
                "Store operations collection "
                f"{collection_name!r} must be a list"
            )

    return cast(StoreDocument, payload)
