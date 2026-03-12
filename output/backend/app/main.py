"""FastAPI application entrypoint for the CardDemo scaffold."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse


def create_app() -> FastAPI:
    """Build the FastAPI application for local development and tests."""
    application = FastAPI(title="CardDemo Backend", version="0.1.0")

    def empty_collection_response() -> JSONResponse:
        """Return the temporary Phase 0 placeholder collection contract."""
        return JSONResponse(content=[])

    @application.get("/health", tags=["scaffold"])
    async def health() -> JSONResponse:
        """Expose a minimal scaffold health check for smoke tests."""
        return JSONResponse(content={"status": "ok"})

    @application.get("/jobs", tags=["scaffold"])
    async def list_jobs() -> JSONResponse:
        """Expose a temporary empty collection until job APIs are implemented."""
        return empty_collection_response()

    @application.get("/accounts", tags=["scaffold"])
    async def list_accounts() -> JSONResponse:
        """Expose a temporary empty collection until account APIs are implemented."""
        return empty_collection_response()

    @application.get("/transactions", tags=["scaffold"])
    async def list_transactions() -> JSONResponse:
        """Expose a temporary empty collection until transaction APIs are implemented."""
        return empty_collection_response()

    return application


app = create_app()
