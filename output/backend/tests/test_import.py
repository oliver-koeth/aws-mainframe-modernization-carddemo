from __future__ import annotations

from fastapi import FastAPI

from app.main import app


def test_app_imports_cleanly(backend_app: FastAPI) -> None:
    assert isinstance(app, FastAPI)
    assert backend_app.title == "CardDemo Backend"
