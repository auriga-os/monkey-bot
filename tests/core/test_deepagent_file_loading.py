"""Tests for identity/context file loading in build_deep_agent()."""
from unittest.mock import MagicMock, patch

from src.core.deepagent import _estimate_tokens, _load_text_file, build_deep_agent


class TestLoadTextFile:
    def test_returns_content_when_file_exists(self, tmp_path):
        f = tmp_path / "SOUL.md"
        f.write_text("I am X")
        assert _load_text_file(f, "SOUL") == "I am X"

    def test_returns_empty_when_file_missing(self, tmp_path):
        result = _load_text_file(tmp_path / "MISSING.md", "SOUL")
        assert result == ""

    def test_never_raises_on_directory_path(self, tmp_path):
        result = _load_text_file(tmp_path, "test")
        assert result == ""

    def test_returns_empty_string_type(self, tmp_path):
        result = _load_text_file(tmp_path / "MISSING.md", "test")
        assert isinstance(result, str)


class TestEstimateTokens:
    def test_empty_string(self):
        assert _estimate_tokens("") == 0

    def test_400_chars_is_100_tokens(self):
        assert _estimate_tokens("a" * 400) == 100

    def test_rough_estimate(self):
        result = _estimate_tokens("hello world")
        assert isinstance(result, int)
        assert result >= 0


class TestBuildDeepAgentFileLoading:
    @patch("src.core.deepagent._DEEPAGENTS_AVAILABLE", True)
    @patch("src.core.deepagent.create_deep_agent")
    @patch("src.core.deepagent.compose_system_prompt")
    def test_soul_file_loaded_from_cwd(self, mock_compose, mock_create, tmp_path, monkeypatch):
        mock_create.return_value = MagicMock()
        monkeypatch.chdir(tmp_path)
        (tmp_path / "SOUL.md").write_text("I am the bot")
        mock_compose.return_value = "composed"

        build_deep_agent(model="gemini-2.5-flash")

        _, kwargs = mock_compose.call_args
        assert kwargs.get("soul_content") == "I am the bot"

    @patch("src.core.deepagent._DEEPAGENTS_AVAILABLE", True)
    @patch("src.core.deepagent.create_deep_agent")
    @patch("src.core.deepagent.compose_system_prompt")
    def test_missing_soul_passes_empty_string(self, mock_compose, mock_create, tmp_path, monkeypatch):
        mock_create.return_value = MagicMock()
        monkeypatch.chdir(tmp_path)
        mock_compose.return_value = "composed"

        build_deep_agent(model="gemini-2.5-flash")

        _, kwargs = mock_compose.call_args
        assert kwargs.get("soul_content") == ""

    @patch("src.core.deepagent._DEEPAGENTS_AVAILABLE", True)
    @patch("src.core.deepagent.create_deep_agent")
    @patch("src.core.deepagent.compose_system_prompt")
    def test_explicit_soul_file_overrides_cwd(self, mock_compose, mock_create, tmp_path):
        mock_create.return_value = MagicMock()
        soul_path = tmp_path / "custom_soul.md"
        soul_path.write_text("Custom identity")
        mock_compose.return_value = "composed"

        build_deep_agent(model="gemini-2.5-flash", soul_file=str(soul_path))

        _, kwargs = mock_compose.call_args
        assert kwargs.get("soul_content") == "Custom identity"

    @patch("src.core.deepagent._DEEPAGENTS_AVAILABLE", True)
    @patch("src.core.deepagent.create_deep_agent")
    @patch("src.core.deepagent.compose_system_prompt")
    def test_user_md_loaded_from_memory_dir(self, mock_compose, mock_create, tmp_path, monkeypatch):
        mock_create.return_value = MagicMock()
        memory_dir = tmp_path / "data" / "memory"
        memory_dir.mkdir(parents=True)
        (memory_dir / "USER.md").write_text("User prefers Y")
        monkeypatch.setenv("MEMORY_DIR", str(memory_dir))
        monkeypatch.chdir(tmp_path)
        mock_compose.return_value = "composed"

        build_deep_agent(model="gemini-2.5-flash")

        _, kwargs = mock_compose.call_args
        assert kwargs.get("user_content") == "User prefers Y"

    @patch("src.core.deepagent._DEEPAGENTS_AVAILABLE", True)
    @patch("src.core.deepagent.create_deep_agent")
    @patch("src.core.deepagent.compose_system_prompt")
    def test_voice_handler_attached_to_agent(self, mock_compose, mock_create, tmp_path, monkeypatch):
        mock_agent = MagicMock()
        mock_create.return_value = mock_agent
        mock_compose.return_value = "composed"
        monkeypatch.chdir(tmp_path)

        build_deep_agent(model="gemini-2.5-flash")

        assert hasattr(mock_agent, "voice_handler")
        assert mock_agent.voice_handler is None

    @patch("src.core.deepagent._DEEPAGENTS_AVAILABLE", True)
    @patch("src.core.deepagent.create_deep_agent")
    @patch("src.core.deepagent.compose_system_prompt")
    def test_heartbeat_skipped_when_no_scheduler(self, mock_compose, mock_create, tmp_path, monkeypatch):
        """heartbeat config + no scheduler → WARNING logged, no crash."""
        mock_create.return_value = MagicMock()
        mock_compose.return_value = "composed"
        monkeypatch.chdir(tmp_path)

        from src.core.config import HeartbeatConfig
        hb_cfg = HeartbeatConfig()

        agent = build_deep_agent(model="gemini-2.5-flash", heartbeat=hb_cfg, scheduler=None)
        assert agent is not None

    @patch("src.core.deepagent._DEEPAGENTS_AVAILABLE", True)
    @patch("src.core.deepagent.create_deep_agent")
    @patch("src.core.deepagent.compose_system_prompt")
    def test_backward_compat_no_new_params(self, mock_compose, mock_create, tmp_path, monkeypatch):
        """No new params → soul_content/user_content/tools_content are empty strings."""
        mock_create.return_value = MagicMock()
        mock_compose.return_value = "composed"
        monkeypatch.chdir(tmp_path)

        build_deep_agent(model="gemini-2.5-flash")

        _, kwargs = mock_compose.call_args
        assert kwargs.get("soul_content", "") == ""
        assert kwargs.get("user_content", "") == ""
        assert kwargs.get("tools_content", "") == ""
