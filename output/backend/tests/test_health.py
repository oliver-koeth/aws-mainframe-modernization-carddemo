from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok_payload() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"status": "ok"}


def test_placeholder_collections_return_empty_arrays() -> None:
    client = TestClient(app)

    for endpoint in ("/jobs", "/accounts", "/transactions"):
        response = client.get(endpoint)

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        assert response.json() == []
