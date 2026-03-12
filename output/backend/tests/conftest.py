from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app
from app.models import StoragePaths


@pytest.fixture
def backend_app() -> FastAPI:
    """Create a fresh application instance for each backend test."""
    return create_app()


@pytest.fixture
def client(backend_app: FastAPI) -> TestClient:
    """Provide a disposable FastAPI test client."""
    return TestClient(backend_app)


@pytest.fixture
def store_path(tmp_path: Path) -> Path:
    """Provide an isolated scaffold store path for a test."""
    return tmp_path / "store.json"


@pytest.fixture
def schedules_path(tmp_path: Path) -> Path:
    """Provide an isolated scaffold schedules path for a test."""
    return tmp_path / "schedules.json"


@pytest.fixture
def storage_paths(store_path: Path, schedules_path: Path) -> StoragePaths:
    """Bundle the disposable scaffold storage targets."""
    return StoragePaths(store=store_path, schedules=schedules_path)
