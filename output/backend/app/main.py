"""FastAPI application entrypoint for the CardDemo scaffold."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse


def create_app() -> FastAPI:
    """Build the FastAPI application for local development and tests."""
    application = FastAPI(title="CardDemo Backend", version="0.1.0")

    @application.get("/health", tags=["scaffold"])
    async def health() -> JSONResponse:
        """Expose a minimal scaffold health check for smoke tests."""
        return JSONResponse(content={"status": "ok"})

    return application


app = create_app()
