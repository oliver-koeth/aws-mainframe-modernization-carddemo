from __future__ import annotations

from fastapi import FastAPI

from app.main import app, create_app


def test_app_imports_cleanly() -> None:
    assert isinstance(app, FastAPI)
    assert create_app().title == "CardDemo Backend"
