"""Voice processing handler: STT + TTS via Google Cloud APIs."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.config import VoiceConfig

logger = logging.getLogger(__name__)

SUPPORTED_MIME_TYPES = {"audio/ogg", "audio/webm", "audio/mp4"}

MIME_TO_STT_ENCODING = {
    "audio/ogg": "OGG_OPUS",
    "audio/webm": "WEBM_OPUS",
    "audio/mp4": "MP3",
}


class VoiceTranscriptionError(Exception):
    """Raised when STT fails or returns empty transcript."""


class VoiceSynthesisError(Exception):
    """Raised when TTS fails."""


class VoiceHandler:
    """Stateless STT + TTS pipeline. Safe to call concurrently."""

    def __init__(self, config: VoiceConfig) -> None:
        """Initialize VoiceHandler.

        Args:
            config: VoiceConfig with STT and TTS settings
        """
        self.config = config

    async def transcribe(self, audio_bytes: bytes, mime_type: str) -> str:
        """Transcribe audio to text via Google Cloud Speech-to-Text.

        Args:
            audio_bytes: Raw audio content
            mime_type: "audio/ogg" | "audio/webm" | "audio/mp4"

        Returns:
            Non-empty transcript string

        Raises:
            VoiceTranscriptionError: If API fails or returns empty transcript
        """
        try:
            from google.cloud import speech
        except ImportError as e:
            raise VoiceTranscriptionError(
                "google-cloud-speech not installed. "
                "pip install 'google-cloud-speech>=2.27.0'"
            ) from e

        try:
            encoding_name = MIME_TO_STT_ENCODING.get(mime_type, "OGG_OPUS")
            encoding = getattr(speech.RecognitionConfig.AudioEncoding, encoding_name)

            client = speech.SpeechAsyncClient()
            audio = speech.RecognitionAudio(content=audio_bytes)
            config = speech.RecognitionConfig(
                encoding=encoding,
                language_code=self.config.language_code,
                model=self.config.stt_model,
            )
            response = await client.recognize(config=config, audio=audio)

            if not response.results:
                raise VoiceTranscriptionError("STT returned no results")

            transcript = response.results[0].alternatives[0].transcript
            if not transcript:
                raise VoiceTranscriptionError("STT returned empty transcript")

            logger.info("STT transcription complete: chars=%d", len(transcript))
            return transcript

        except VoiceTranscriptionError:
            raise
        except Exception as e:
            raise VoiceTranscriptionError(f"STT failed: {e}") from e

    async def synthesize(self, text: str) -> bytes:
        """Synthesize text to OGG_OPUS audio via Google Cloud Text-to-Speech.

        Args:
            text: Response text (truncated to 5000 chars if longer)

        Returns:
            OGG_OPUS encoded audio bytes

        Raises:
            VoiceSynthesisError: If API fails
        """
        try:
            from google.cloud import texttospeech
        except ImportError as e:
            raise VoiceSynthesisError(
                "google-cloud-texttospeech not installed. "
                "pip install 'google-cloud-texttospeech>=2.17.0'"
            ) from e

        try:
            client = texttospeech.TextToSpeechAsyncClient()
            synthesis_input = texttospeech.SynthesisInput(text=text[:5000])
            voice = texttospeech.VoiceSelectionParams(
                language_code=self.config.language_code,
                name=self.config.tts_voice_name,
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.OGG_OPUS
            )
            response = await client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
            logger.info(
                "TTS synthesis complete: bytes=%d", len(response.audio_content)
            )
            return response.audio_content

        except VoiceSynthesisError:
            raise
        except Exception as e:
            raise VoiceSynthesisError(f"TTS failed: {e}") from e
