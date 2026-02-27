"""Unit tests for VoiceHandler STT + TTS pipeline."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.config import VoiceConfig
from src.voice.handler import (
    VoiceHandler,
    VoiceSynthesisError,
    VoiceTranscriptionError,
)

# Mock google.cloud modules since they're not installed in dev environment
mock_speech = MagicMock()
mock_texttospeech = MagicMock()
sys.modules["google.cloud.speech"] = mock_speech
sys.modules["google.cloud.texttospeech"] = mock_texttospeech


@pytest.fixture
def voice_config():
    return VoiceConfig(language_code="en-US", tts_voice_name="en-US-Journey-F")


@pytest.fixture
def handler(voice_config):
    return VoiceHandler(config=voice_config)


class TestVoiceHandlerTranscribe:
    @pytest.mark.asyncio
    async def test_transcribe_success(self, handler):
        mock_client = AsyncMock()
        mock_result = MagicMock()
        mock_result.results = [
            MagicMock(alternatives=[MagicMock(transcript="hello world")])
        ]
        mock_client.recognize = AsyncMock(return_value=mock_result)

        with patch("google.cloud.speech.SpeechAsyncClient", return_value=mock_client):
            result = await handler.transcribe(b"audio-bytes", "audio/ogg")

        assert result == "hello world"

    @pytest.mark.asyncio
    async def test_transcribe_empty_transcript_raises(self, handler):
        mock_client = AsyncMock()
        mock_result = MagicMock()
        mock_result.results = [MagicMock(alternatives=[MagicMock(transcript="")])]
        mock_client.recognize = AsyncMock(return_value=mock_result)

        with patch("google.cloud.speech.SpeechAsyncClient", return_value=mock_client):  # noqa: SIM117
            with pytest.raises(VoiceTranscriptionError, match="empty transcript"):
                await handler.transcribe(b"audio", "audio/ogg")

    @pytest.mark.asyncio
    async def test_transcribe_no_results_raises(self, handler):
        mock_client = AsyncMock()
        mock_result = MagicMock()
        mock_result.results = []
        mock_client.recognize = AsyncMock(return_value=mock_result)

        with patch("google.cloud.speech.SpeechAsyncClient", return_value=mock_client):  # noqa: SIM117
            with pytest.raises(VoiceTranscriptionError, match="no results"):
                await handler.transcribe(b"audio", "audio/ogg")

    @pytest.mark.asyncio
    async def test_transcribe_api_error_raises_transcription_error(self, handler):
        mock_client = AsyncMock()
        mock_client.recognize = AsyncMock(side_effect=Exception("API down"))

        with patch("google.cloud.speech.SpeechAsyncClient", return_value=mock_client):  # noqa: SIM117
            with pytest.raises(VoiceTranscriptionError):
                await handler.transcribe(b"audio", "audio/ogg")


class TestVoiceHandlerSynthesize:
    @pytest.mark.asyncio
    async def test_synthesize_success(self, handler):
        mock_client = AsyncMock()
        mock_response = MagicMock(audio_content=b"audio-bytes-out")
        mock_client.synthesize_speech = AsyncMock(return_value=mock_response)

        with patch(
            "google.cloud.texttospeech.TextToSpeechAsyncClient",
            return_value=mock_client,
        ):
            result = await handler.synthesize("Hello world")

        assert result == b"audio-bytes-out"

    @pytest.mark.asyncio
    async def test_synthesize_truncates_long_text(self, handler):
        long_text = "x" * 6000
        mock_client = AsyncMock()
        mock_response = MagicMock(audio_content=b"audio")
        mock_client.synthesize_speech = AsyncMock(return_value=mock_response)

        with patch(
            "google.cloud.texttospeech.TextToSpeechAsyncClient",
            return_value=mock_client,
        ):
            result = await handler.synthesize(long_text)

        assert mock_client.synthesize_speech.called
        assert result == b"audio"

    @pytest.mark.asyncio
    async def test_synthesize_api_error_raises_synthesis_error(self, handler):
        mock_client = AsyncMock()
        mock_client.synthesize_speech = AsyncMock(side_effect=Exception("TTS down"))

        with patch(
            "google.cloud.texttospeech.TextToSpeechAsyncClient",
            return_value=mock_client,
        ), pytest.raises(VoiceSynthesisError):
            await handler.synthesize("test text")


class TestVoiceHandlerImports:
    def test_voice_handler_importable(self):
        from src.voice import VoiceHandler

        assert VoiceHandler is not None

    def test_exceptions_importable(self):
        from src.voice import VoiceSynthesisError, VoiceTranscriptionError

        assert VoiceTranscriptionError is not None
        assert VoiceSynthesisError is not None
