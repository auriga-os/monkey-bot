"""Tests for POST /voice endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.gateway.server import app


@pytest.fixture
def client():
    return TestClient(app)


class TestVoiceEndpoint:
    def test_voice_disabled_returns_404(self, client, monkeypatch):
        monkeypatch.delenv("VOICE_ENABLED", raising=False)
        response = client.post(
            "/voice",
            data={"user_email": "test@test.com"},
            files={"audio": ("test.ogg", b"bytes", "audio/ogg")},
        )
        assert response.status_code == 404

    def test_voice_disabled_explicit_false_returns_404(self, client, monkeypatch):
        monkeypatch.setenv("VOICE_ENABLED", "false")
        response = client.post(
            "/voice",
            data={"user_email": "test@test.com"},
            files={"audio": ("test.ogg", b"bytes", "audio/ogg")},
        )
        assert response.status_code == 404

    def test_unauthorized_user_returns_401(self, client, monkeypatch):
        monkeypatch.setenv("VOICE_ENABLED", "true")
        monkeypatch.setenv("ALLOWED_USERS", "allowed@test.com")
        response = client.post(
            "/voice",
            data={"user_email": "other@test.com"},
            files={"audio": ("test.ogg", b"bytes", "audio/ogg")},
        )
        assert response.status_code == 401

    def test_unsupported_mime_type_returns_415(self, client, monkeypatch):
        monkeypatch.setenv("VOICE_ENABLED", "true")
        monkeypatch.setenv("ALLOWED_USERS", "user@test.com")
        response = client.post(
            "/voice",
            data={"user_email": "user@test.com", "mime_type": "audio/wav"},
            files={"audio": ("test.wav", b"bytes", "audio/wav")},
        )
        assert response.status_code == 415

    def test_missing_audio_content_returns_400(self, client, monkeypatch):
        monkeypatch.setenv("VOICE_ENABLED", "true")
        monkeypatch.setenv("ALLOWED_USERS", "user@test.com")

        mock_voice_handler = AsyncMock()
        mock_voice_handler.transcribe = AsyncMock(return_value="hello")
        mock_agent = MagicMock()
        mock_agent.voice_handler = mock_voice_handler

        with patch("src.gateway.server.agent_core", mock_agent):
            response = client.post(
                "/voice",
                data={"user_email": "user@test.com"},
                files={"audio": ("empty.ogg", b"", "audio/ogg")},
            )
        assert response.status_code == 400

    def test_successful_voice_request_returns_200_with_headers(
        self, client, monkeypatch
    ):
        monkeypatch.setenv("VOICE_ENABLED", "true")
        monkeypatch.setenv("ALLOWED_USERS", "user@test.com")

        mock_voice_handler = AsyncMock()
        mock_voice_handler.transcribe = AsyncMock(return_value="hello agent")
        mock_voice_handler.synthesize = AsyncMock(return_value=b"ogg-audio-bytes")

        mock_agent = MagicMock()
        mock_agent.voice_handler = mock_voice_handler
        mock_agent.ainvoke = AsyncMock(
            return_value={"messages": [MagicMock(content="hello user")]}
        )

        with patch("src.gateway.server.agent_core", mock_agent):
            response = client.post(
                "/voice",
                data={"user_email": "user@test.com"},
                files={"audio": ("test.ogg", b"real-audio-data", "audio/ogg")},
            )

        assert response.status_code == 200
        assert "audio/ogg" in response.headers.get("content-type", "")
        assert "X-Transcript-In" in response.headers
        assert "X-Trace-Id" in response.headers
        assert response.content == b"ogg-audio-bytes"

    def test_no_voice_handler_returns_503(self, client, monkeypatch):
        monkeypatch.setenv("VOICE_ENABLED", "true")
        monkeypatch.setenv("ALLOWED_USERS", "user@test.com")

        mock_agent = MagicMock()
        mock_agent.voice_handler = None

        with patch("src.gateway.server.agent_core", mock_agent):
            response = client.post(
                "/voice",
                data={"user_email": "user@test.com"},
                files={"audio": ("test.ogg", b"audio", "audio/ogg")},
            )
        assert response.status_code == 503
