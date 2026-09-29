"""Test configuration and fixtures for Personal AI OS."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Synchronous test client for FastAPI routes."""
    with TestClient(app) as test_client:
        yield test_client
