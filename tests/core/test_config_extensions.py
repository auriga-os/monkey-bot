"""Tests for HeartbeatConfig, VoiceConfig dataclasses and loader functions."""
from src.core.config import (
    CONFIG_MAPPING,
    HeartbeatConfig,
    VoiceConfig,
    load_bot_config,
    load_heartbeat_config,
    load_voice_config,
)


class TestHeartbeatConfig:
    def test_default_values(self):
        cfg = HeartbeatConfig()
        assert cfg.cron == "*/30 * * * *"
        assert cfg.active_hours_start == "09:00"
        assert cfg.active_hours_timezone == "America/New_York"
        assert cfg.heartbeat_md_path is None

    def test_load_heartbeat_config_disabled(self, monkeypatch):
        monkeypatch.delenv("HEARTBEAT_ENABLED", raising=False)
        assert load_heartbeat_config() is None

    def test_load_heartbeat_config_false(self, monkeypatch):
        monkeypatch.setenv("HEARTBEAT_ENABLED", "false")
        assert load_heartbeat_config() is None

    def test_load_heartbeat_config_enabled(self, monkeypatch):
        monkeypatch.setenv("HEARTBEAT_ENABLED", "true")
        monkeypatch.setenv("HEARTBEAT_CRON", "*/15 * * * *")
        monkeypatch.setenv("HEARTBEAT_ACTIVE_HOURS_START", "08:00")
        cfg = load_heartbeat_config()
        assert cfg is not None
        assert isinstance(cfg, HeartbeatConfig)
        assert cfg.cron == "*/15 * * * *"
        assert cfg.active_hours_start == "08:00"

    def test_load_heartbeat_config_defaults_when_enabled(self, monkeypatch):
        monkeypatch.setenv("HEARTBEAT_ENABLED", "true")
        for key in ["HEARTBEAT_CRON", "HEARTBEAT_ACTIVE_HOURS_START", "HEARTBEAT_ACTIVE_HOURS_END"]:
            monkeypatch.delenv(key, raising=False)
        cfg = load_heartbeat_config()
        assert cfg.cron == "*/30 * * * *"


class TestVoiceConfig:
    def test_default_values(self):
        cfg = VoiceConfig()
        assert cfg.language_code == "en-US"
        assert cfg.tts_voice_name == "en-US-Journey-F"
        assert cfg.tts_audio_encoding == "OGG_OPUS"

    def test_load_voice_config_disabled(self, monkeypatch):
        monkeypatch.delenv("VOICE_ENABLED", raising=False)
        assert load_voice_config() is None

    def test_load_voice_config_enabled(self, monkeypatch):
        monkeypatch.setenv("VOICE_ENABLED", "true")
        monkeypatch.setenv("VOICE_TTS_VOICE_NAME", "en-US-Journey-D")
        cfg = load_voice_config()
        assert cfg is not None
        assert isinstance(cfg, VoiceConfig)
        assert cfg.tts_voice_name == "en-US-Journey-D"

    def test_load_voice_config_defaults_when_enabled(self, monkeypatch):
        monkeypatch.setenv("VOICE_ENABLED", "true")
        for key in ["VOICE_STT_LANGUAGE_CODE", "VOICE_TTS_VOICE_NAME"]:
            monkeypatch.delenv(key, raising=False)
        cfg = load_voice_config()
        assert cfg.language_code == "en-US"
        assert cfg.tts_voice_name == "en-US-Journey-F"


class TestConfigMappingExtensions:
    def test_heartbeat_keys_in_mapping(self):
        assert "heartbeat.enabled" in CONFIG_MAPPING
        assert CONFIG_MAPPING["heartbeat.enabled"] == "HEARTBEAT_ENABLED"
        assert "heartbeat.active_hours.start" in CONFIG_MAPPING
        assert CONFIG_MAPPING["heartbeat.active_hours.start"] == "HEARTBEAT_ACTIVE_HOURS_START"

    def test_voice_keys_in_mapping(self):
        assert "voice.enabled" in CONFIG_MAPPING
        assert CONFIG_MAPPING["voice.enabled"] == "VOICE_ENABLED"
        assert "voice.text_to_speech.voice_name" in CONFIG_MAPPING

    def test_load_bot_config_with_heartbeat_yaml(self, tmp_path, monkeypatch):
        import os

        import src.core.config as cfg_mod
        bot_yaml = tmp_path / "bot.yaml"
        bot_yaml.write_text(
            "agent:\n  name: test\n"
            "heartbeat:\n  enabled: true\n  cron: '*/30 * * * *'\n"
        )
        monkeypatch.chdir(tmp_path)
        cfg_mod._config_loaded = False
        monkeypatch.delenv("HEARTBEAT_ENABLED", raising=False)
        load_bot_config()
        assert os.environ.get("HEARTBEAT_ENABLED").lower() == "true"
        assert os.environ.get("HEARTBEAT_CRON") == "*/30 * * * *"
        cfg_mod._config_loaded = False

    def test_bot_yaml_without_heartbeat_no_error(self, tmp_path, monkeypatch):
        import src.core.config as cfg_mod
        bot_yaml = tmp_path / "bot.yaml"
        bot_yaml.write_text("agent:\n  name: test\nmodel:\n  provider: google_vertexai\n")
        monkeypatch.chdir(tmp_path)
        cfg_mod._config_loaded = False
        load_bot_config()
        cfg_mod._config_loaded = False
