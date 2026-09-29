"""Tests for health check endpoints."""

from fastapi.testclient import TestClient


def test_health_check_root(client: TestClient):
    """Verify GET /health returns 200 OK and healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "Personal AI OS"
    assert "components" in data
    assert "api" in data["components"]
    assert "database" in data["components"]
    assert "llm_provider" in data["components"]


def test_health_check_api_prefix(client: TestClient):
    """Verify GET /api/health also returns 200 OK."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
