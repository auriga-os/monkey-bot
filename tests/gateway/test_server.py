"""
Tests for Gateway FastAPI server.

Tests both endpoints:
- POST /webhook: Google Chat message handling
- GET /health: Health check
"""

import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.gateway.interfaces import AgentError
from src.gateway.server import app


class TestWebhookEndpoint:
    """Tests for POST /webhook endpoint."""

    @pytest.fixture
    def allowed_users_env(self) -> None:
        """Set ALLOWED_USERS env var for tests."""
        os.environ["ALLOWED_USERS"] = "user@example.com,admin@example.com"

    def test_webhook_success(self, allowed_users_env: None) -> None:
        """Test successful webhook processing with allowed user."""
        payload = {
            "message": {
                "sender": {"email": "user@example.com"},
                "text": "Hello, agent!",
            }
        }

        client = TestClient(app)
        response = client.post("/webhook", json=payload)

        assert response.status_code == 200
        assert "text" in response.json()
        assert "Hello, agent!" in response.json()["text"]
        assert "trace:" in response.json()["text"]  # MockAgentCore includes trace_id

    def test_webhook_unauthorized_user(self, allowed_users_env: None) -> None:
        """Test webhook with unauthorized user (not in allowlist)."""
        payload = {
            "message": {
                "sender": {"email": "unauthorized@example.com"},
                "text": "Hello",
            }
        }

        client = TestClient(app)
        response = client.post("/webhook", json=payload)

        assert response.status_code == 401
        assert "detail" in response.json()
        assert "unauthorized" in response.json()["detail"].lower()

    def test_webhook_malformed_payload_missing_sender(self, allowed_users_env: None) -> None:
        """Test webhook with malformed payload (missing sender)."""
        payload = {
            "message": {
                # Missing sender
                "text": "Hello",
            }
        }

        client = TestClient(app)
        response = client.post("/webhook", json=payload)

        # Pydantic validation should catch this
        assert response.status_code == 422

    def test_webhook_malformed_payload_missing_text(self, allowed_users_env: None) -> None:
        """Test webhook with malformed payload (missing text)."""
        payload = {
            "message": {
                "sender": {"email": "user@example.com"},
                # Missing text
            }
        }

        client = TestClient(app)
        response = client.post("/webhook", json=payload)

        # Pydantic validation should catch this
        assert response.status_code == 422

    def test_webhook_empty_text(self, allowed_users_env: None) -> None:
        """Test webhook with empty text (should be rejected by Pydantic)."""
        payload = {
            "message": {
                "sender": {"email": "user@example.com"},
                "text": "",
            }
        }

        client = TestClient(app)
        response = client.post("/webhook", json=payload)

        # Pydantic validation should reject empty text
        assert response.status_code == 422

    def test_webhook_missing_allowed_users_env(self) -> None:
        """Test webhook when ALLOWED_USERS env var is not set."""
        # Clear ALLOWED_USERS env var
        if "ALLOWED_USERS" in os.environ:
            del os.environ["ALLOWED_USERS"]

        payload = {
            "message": {
                "sender": {"email": "user@example.com"},
                "text": "Hello",
            }
        }

        client = TestClient(app)
        response = client.post("/webhook", json=payload)

        # Should return 500 (server configuration error)
        assert response.status_code == 500
        assert "configuration" in response.json()["detail"].lower()

    def test_webhook_with_google_chat_metadata(self, allowed_users_env: None) -> None:
        """Test that Google Chat metadata is accepted but stripped."""
        payload = {
            "message": {
                "sender": {
                    "email": "user@example.com",
                    "displayName": "Test User",
                },
                "text": "Hello",
                "space": {"name": "spaces/xxx"},
                "thread": {"name": "spaces/xxx/threads/yyy"},
            }
        }

        client = TestClient(app)
        response = client.post("/webhook", json=payload)

        # Should succeed (metadata is accepted by Pydantic, then stripped by PII filter)
        assert response.status_code == 200
        assert "text" in response.json()

    def test_webhook_agent_error(self, allowed_users_env: None) -> None:
        """Test webhook when Agent Core raises AgentError."""
        payload = {
            "message": {
                "sender": {"email": "user@example.com"},
                "text": "Trigger error",
            }
        }

        # Mock Agent Core to raise AgentError
        with patch("src.gateway.server.agent_core") as mock_agent:
            mock_agent.process_message = AsyncMock(
                side_effect=AgentError("Processing failed", trace_id="test-trace-id")
            )

            client = TestClient(app)
            response = client.post("/webhook", json=payload)

        # Should return 500 (agent processing failed)
        assert response.status_code == 500
        assert "detail" in response.json()

    def test_webhook_truncates_long_response(self, allowed_users_env: None) -> None:
        """Test that responses over 4000 chars are truncated."""
        payload = {
            "message": {
                "sender": {"email": "user@example.com"},
                "text": "Generate long response",
            }
        }

        # Mock Agent Core to return very long response
        long_response = "x" * 5000
        with patch("src.gateway.server.agent_core") as mock_agent:
            mock_agent.process_message = AsyncMock(return_value=long_response)

            client = TestClient(app)
            response = client.post("/webhook", json=payload)

        # Should succeed with truncated response
        assert response.status_code == 200
        response_text = response.json()["text"]
        assert len(response_text) <= 4030  # 4000 + truncation message
        assert "truncated" in response_text.lower()

    def test_webhook_multiple_allowed_users(self) -> None:
        """Test that multiple users in ALLOWED_USERS are all accepted."""
        os.environ["ALLOWED_USERS"] = "user1@example.com, user2@example.com, user3@example.com"

        client = TestClient(app)

        for email in ["user1@example.com", "user2@example.com", "user3@example.com"]:
            payload = {
                "message": {
                    "sender": {"email": email},
                    "text": "Hello",
                }
            }

            response = client.post("/webhook", json=payload)
            assert response.status_code == 200, f"Failed for {email}"


class TestHealthEndpoint:
    """Tests for GET /health endpoint."""

    def test_health_success(self) -> None:
        """Test successful health check."""
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"
        assert "checks" in data
        assert data["checks"]["agent_core"] == "ok"

    def test_health_returns_valid_timestamp(self) -> None:
        """Test that health check returns valid ISO8601 timestamp."""
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200

        data = response.json()
        timestamp = data["timestamp"]

        # Should be in ISO8601 format (can be parsed)
        from datetime import datetime

        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    def test_health_multiple_calls(self) -> None:
        """Test that health check can be called multiple times."""
        client = TestClient(app)

        response1 = client.get("/health")
        response2 = client.get("/health")
        response3 = client.get("/health")

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200


class TestTruncateResponse:
    """Tests for truncate_response helper function."""

    def test_truncate_short_response(self) -> None:
        """Test that short responses are not truncated."""
        from src.gateway.server import truncate_response

        text = "Short response"
        result = truncate_response(text)

        assert result == text
        assert len(result) == len(text)

    def test_truncate_exact_length(self) -> None:
        """Test response exactly at max_length is not truncated."""
        from src.gateway.server import truncate_response

        text = "x" * 4000
        result = truncate_response(text)

        assert result == text
        assert len(result) == 4000

    def test_truncate_long_response(self) -> None:
        """Test that long responses are truncated."""
        from src.gateway.server import truncate_response

        text = "x" * 5000
        result = truncate_response(text)

        assert len(result) <= 4030  # 4000 + truncation message
        assert result.startswith("xxx")
        assert "truncated" in result.lower()

    def test_truncate_custom_max_length(self) -> None:
        """Test truncation with custom max_length."""
        from src.gateway.server import truncate_response

        text = "x" * 1000
        result = truncate_response(text, max_length=500)

        assert len(result) <= 530  # 500 + truncation message
        assert "truncated" in result.lower()
