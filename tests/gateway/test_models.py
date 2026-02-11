"""
Tests for Gateway Pydantic models.

Tests validation logic for Google Chat webhook/response models and health check.
"""

import pytest
from pydantic import ValidationError

from src.gateway.models import (
    GoogleChatMessage,
    GoogleChatResponse,
    GoogleChatSender,
    GoogleChatWebhook,
    HealthCheckResponse,
)


class TestGoogleChatSender:
    """Tests for GoogleChatSender model."""

    def test_valid_sender(self) -> None:
        """Test valid sender with email."""
        sender = GoogleChatSender(email="user@example.com")
        assert sender.email == "user@example.com"
        assert sender.display_name is None

    def test_sender_with_display_name(self) -> None:
        """Test sender with display name (camelCase alias)."""
        sender = GoogleChatSender(email="user@example.com", displayName="Test User")
        assert sender.email == "user@example.com"
        assert sender.display_name == "Test User"

    def test_sender_missing_email(self) -> None:
        """Test that email is required."""
        with pytest.raises(ValidationError) as exc_info:
            GoogleChatSender()  # type: ignore
        
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("email",) and e["type"] == "missing" for e in errors)


class TestGoogleChatMessage:
    """Tests for GoogleChatMessage model."""

    def test_valid_message(self) -> None:
        """Test valid message with sender and text."""
        message = GoogleChatMessage(
            sender={"email": "user@example.com"},  # type: ignore
            text="Remember that I prefer Python",
        )
        assert message.sender.email == "user@example.com"
        assert message.text == "Remember that I prefer Python"

    def test_message_empty_text(self) -> None:
        """Test that empty text is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            GoogleChatMessage(
                sender={"email": "user@example.com"},  # type: ignore
                text="",
            )
        
        errors = exc_info.value.errors()
        assert any("empty" in str(e["msg"]).lower() for e in errors)

    def test_message_whitespace_only_text(self) -> None:
        """Test that whitespace-only text is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            GoogleChatMessage(
                sender={"email": "user@example.com"},  # type: ignore
                text="   ",
            )
        
        errors = exc_info.value.errors()
        assert any("empty" in str(e["msg"]).lower() for e in errors)

    def test_message_missing_sender(self) -> None:
        """Test that sender is required."""
        with pytest.raises(ValidationError) as exc_info:
            GoogleChatMessage(text="Hello")  # type: ignore
        
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("sender",) and e["type"] == "missing" for e in errors)


class TestGoogleChatWebhook:
    """Tests for GoogleChatWebhook model."""

    def test_valid_webhook(self) -> None:
        """Test valid webhook payload."""
        webhook = GoogleChatWebhook(
            message={  # type: ignore
                "sender": {"email": "user@example.com"},
                "text": "Remember that I prefer Python",
            }
        )
        assert webhook.message.sender.email == "user@example.com"
        assert webhook.message.text == "Remember that I prefer Python"

    def test_webhook_with_extra_metadata(self) -> None:
        """Test that extra Google Chat metadata is accepted but not stored."""
        webhook = GoogleChatWebhook(
            message={  # type: ignore
                "sender": {
                    "email": "user@example.com",
                    "displayName": "Test User",
                },
                "text": "Hello",
                "space": {"name": "spaces/xxx"},  # Extra metadata
                "thread": {"name": "spaces/xxx/threads/yyy"},  # Extra metadata
            }
        )
        
        # Only the fields we defined should be in the model
        assert webhook.message.sender.email == "user@example.com"
        assert webhook.message.text == "Hello"
        
        # Extra metadata should not be in the model dict
        message_dict = webhook.message.model_dump()
        assert "space" not in message_dict
        assert "thread" not in message_dict

    def test_webhook_missing_message(self) -> None:
        """Test that message is required."""
        with pytest.raises(ValidationError) as exc_info:
            GoogleChatWebhook()  # type: ignore
        
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("message",) and e["type"] == "missing" for e in errors)

    def test_webhook_missing_sender_email(self) -> None:
        """Test that sender email is required."""
        with pytest.raises(ValidationError):
            GoogleChatWebhook(
                message={  # type: ignore
                    "sender": {},  # Missing email
                    "text": "Hello",
                }
            )

    def test_webhook_missing_text(self) -> None:
        """Test that message text is required."""
        with pytest.raises(ValidationError):
            GoogleChatWebhook(
                message={  # type: ignore
                    "sender": {"email": "user@example.com"},
                    # Missing text
                }
            )


class TestGoogleChatResponse:
    """Tests for GoogleChatResponse model."""

    def test_valid_response(self) -> None:
        """Test valid response with text."""
        response = GoogleChatResponse(text="✅ Got it!")
        assert response.text == "✅ Got it!"

    def test_response_with_long_text(self) -> None:
        """Test response with maximum allowed text length."""
        long_text = "x" * 4000
        response = GoogleChatResponse(text=long_text)
        assert len(response.text) == 4000

    def test_response_text_too_long(self) -> None:
        """Test that text over 4000 chars is rejected."""
        too_long_text = "x" * 4001
        with pytest.raises(ValidationError) as exc_info:
            GoogleChatResponse(text=too_long_text)
        
        errors = exc_info.value.errors()
        assert any("4000" in str(e["msg"]) for e in errors)


class TestHealthCheckResponse:
    """Tests for HealthCheckResponse model."""

    def test_valid_healthy_response(self) -> None:
        """Test valid healthy health check response."""
        response = HealthCheckResponse(
            status="healthy",
            timestamp="2026-02-11T22:00:00Z",
            checks={"agent_core": "ok"},
        )
        assert response.status == "healthy"
        assert response.timestamp == "2026-02-11T22:00:00Z"
        assert response.version == "1.0.0"
        assert response.checks == {"agent_core": "ok"}

    def test_valid_unhealthy_response(self) -> None:
        """Test valid unhealthy health check response."""
        response = HealthCheckResponse(
            status="unhealthy",
            timestamp="2026-02-11T22:00:00Z",
            checks={"agent_core": "error", "llm": "timeout"},
        )
        assert response.status == "unhealthy"
        assert response.checks == {"agent_core": "error", "llm": "timeout"}

    def test_default_version(self) -> None:
        """Test that version defaults to 1.0.0."""
        response = HealthCheckResponse(
            status="healthy",
            timestamp="2026-02-11T22:00:00Z",
        )
        assert response.version == "1.0.0"

    def test_default_checks(self) -> None:
        """Test that checks defaults to empty dict."""
        response = HealthCheckResponse(
            status="healthy",
            timestamp="2026-02-11T22:00:00Z",
        )
        assert response.checks == {}

    def test_invalid_status(self) -> None:
        """Test that invalid status is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            HealthCheckResponse(
                status="degraded",  # Invalid - must be 'healthy' or 'unhealthy'
                timestamp="2026-02-11T22:00:00Z",
            )
        
        errors = exc_info.value.errors()
        assert any("healthy" in str(e["msg"]).lower() for e in errors)

    def test_invalid_timestamp_format(self) -> None:
        """Test that invalid timestamp format is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            HealthCheckResponse(
                status="healthy",
                timestamp="not-a-timestamp",
            )
        
        errors = exc_info.value.errors()
        assert any("iso8601" in str(e["msg"]).lower() for e in errors)

    def test_valid_timestamp_without_z(self) -> None:
        """Test that timestamp without Z suffix is accepted."""
        response = HealthCheckResponse(
            status="healthy",
            timestamp="2026-02-11T22:00:00+00:00",
        )
        assert response.timestamp == "2026-02-11T22:00:00+00:00"
