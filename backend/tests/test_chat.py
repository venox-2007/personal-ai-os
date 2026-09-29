"""Tests for chat and orchestrator interaction endpoints."""

from fastapi.testclient import TestClient


def test_chat_endpoint_valid_request(client: TestClient):
    """Verify POST /api/chat returns structured response and observable activity events."""
    payload = {
        "message": "Hello Personal AI OS, test my setup!",
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "conversation_id" in data
    assert "response" in data
    assert "activities" in data
    assert len(data["activities"]) > 0

    # Ensure activity events match required schema
    for activity in data["activities"]:
        assert "id" in activity
        assert "agent" in activity
        assert "activity_type" in activity
        assert "status" in activity
        assert "action" in activity


def test_chat_endpoint_empty_message_validation(client: TestClient):
    """Verify validation error on empty message."""
    payload = {"message": ""}
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 422
