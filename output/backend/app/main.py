"""FastAPI application entrypoint for the CardDemo scaffold."""

from __future__ import annotations

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Build the FastAPI application for local development and tests."""
    return FastAPI(title="CardDemo Backend", version="0.1.0")


app = create_app()
