"""
Comprehensive tests for Modal Sandbox Backend.

This test suite ensures coverage of:
    - Lazy initialization
    - Command execution
    - Timeout handling
    - Lifecycle management (start/stop)
    - Environment variables
    - ImportError when modal is missing
    - Filesystem operations
    - Error handling
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestModalSandboxImport:
    """Test import behavior when modal is not installed."""

    def test_import_error_when_modal_missing(self) -> None:
        """Test that ImportError is raised when modal is not installed."""
        # Mock modal as unavailable
        with patch.dict("sys.modules", {"modal": None}):
            with patch("src.sandbox.modal._MODAL_AVAILABLE", False):
                from src.sandbox.modal import ModalSandboxBackend

                # Should raise ImportError on initialization
                with pytest.raises(ImportError) as exc_info:
                    ModalSandboxBackend()

                assert "modal package required" in str(exc_info.value).lower()
                assert "pip install emonk[modal]" in str(exc_info.value)

    def test_graceful_import_from_init(self) -> None:
        """Test that __init__.py handles missing modal gracefully."""
        # Mock modal as unavailable
        with patch.dict("sys.modules", {"modal": None}):
            # Should not raise on import
            from src.sandbox import (
                ModalSandboxBackend,
                SandboxError,
                SandboxTimeoutError,
                SandboxUnavailableError,
            )

            # Error classes should be available
            assert issubclass(SandboxError, Exception)
            assert issubclass(SandboxTimeoutError, SandboxError)
            assert issubclass(SandboxUnavailableError, SandboxError)

            # Backend should raise on init
            with pytest.raises(ImportError):
                ModalSandboxBackend()


class TestModalSandboxInitialization:
    """Test sandbox initialization and configuration."""

    @pytest.fixture
    def mock_modal(self) -> Any:
        """Mock modal module."""
        mock = MagicMock()
        mock.Image = MagicMock()
        mock.Image.debian_slim = MagicMock(return_value=MagicMock())
        mock.Sandbox = MagicMock()
        return mock

    @pytest.fixture
    def backend(self, mock_modal: Any) -> Any:
        """Create backend with mocked modal."""
        with patch("src.sandbox.modal.modal", mock_modal):
            with patch("src.sandbox.modal._MODAL_AVAILABLE", True):
                from src.sandbox.modal import ModalSandboxBackend

                return ModalSandboxBackend(
                    app_name="test-sandbox",
                    timeout=300,
                    cpu=2,
                    memory_mb=1024,
                    pip_packages=["requests"],
                    apt_packages=["git"],
                    env_vars={"TEST_VAR": "test_value"},
                )

    def test_initialization_with_defaults(self, mock_modal: Any) -> None:
        """Test initialization with default parameters."""
        with patch("src.sandbox.modal.modal", mock_modal):
            with patch("src.sandbox.modal._MODAL_AVAILABLE", True):
                from src.sandbox.modal import ModalSandboxBackend

                backend = ModalSandboxBackend()

                assert backend.app_name == "emonk-sandbox"
                assert backend.timeout == 600
                assert backend.cpu == 2
                assert backend.memory_mb == 2048
                assert len(backend.pip_packages) > 0
                assert backend.apt_packages == []
                assert backend.env_vars == {}

    def test_initialization_with_custom_params(self, backend: Any) -> None:
        """Test initialization with custom parameters."""
        assert backend.app_name == "test-sandbox"
        assert backend.timeout == 300
        assert backend.cpu == 2
        assert backend.memory_mb == 1024
        assert backend.pip_packages == ["requests"]
        assert backend.apt_packages == ["git"]
        assert backend.env_vars == {"TEST_VAR": "test_value"}

    def test_sandbox_not_started_on_init(self, backend: Any) -> None:
        """Test that sandbox is not started on initialization (lazy init)."""
        assert backend._sandbox is None
        assert backend._sandbox_id is None
        assert backend.id is None

    def test_custom_image(self, mock_modal: Any) -> None:
        """Test initialization with custom Modal image."""
        custom_image = MagicMock()

        with patch("src.sandbox.modal.modal", mock_modal):
            with patch("src.sandbox.modal._MODAL_AVAILABLE", True):
                from src.sandbox.modal import ModalSandboxBackend

                backend = ModalSandboxBackend(image=custom_image)

                assert backend._custom_image is custom_image


class TestModalSandboxLifecycle:
    """Test sandbox lifecycle management (start/stop)."""

    @pytest.fixture
    def mock_modal_patcher(self) -> Any:
        """Create a patcher for modal module."""
        mock = MagicMock()

        # Mock Image
        mock_image = MagicMock()
        mock_image.apt_install = MagicMock(return_value=mock_image)
        mock_image.pip_install = MagicMock(return_value=mock_image)
        mock.Image = MagicMock()
        mock.Image.debian_slim = MagicMock(return_value=mock_image)

        # Mock Sandbox
        mock_sandbox = MagicMock()
        mock_sandbox.object_id = "test-sandbox-123"
        mock_sandbox.terminate = AsyncMock()
        mock.Sandbox = MagicMock()
        mock.Sandbox.create = MagicMock(return_value=mock_sandbox)

        patcher = patch("src.sandbox.modal.modal", mock)
        patcher.start()
        yield mock
        patcher.stop()

    @pytest.fixture
    def backend(self, mock_modal_patcher: Any) -> Any:
        """Create backend with mocked modal."""
        with patch("src.sandbox.modal._MODAL_AVAILABLE", True):
            from src.sandbox.modal import ModalSandboxBackend

            return ModalSandboxBackend(
                app_name="test-sandbox",
                pip_packages=["requests"],
                apt_packages=["git"],
            )

    @pytest.mark.asyncio
    async def test_start_creates_sandbox(self, backend: Any, mock_modal_patcher: Any) -> None:
        """Test that start() creates a Modal sandbox."""
        await backend.start()

        # Should have created sandbox
        assert backend._sandbox is not None
        assert backend._sandbox_id == "test-sandbox-123"
        assert backend.id == "test-sandbox-123"

        # Should have called Modal API
        mock_modal_patcher.Sandbox.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_builds_image_with_packages(
        self, backend: Any, mock_modal_patcher: Any
    ) -> None:
        """Test that start() builds image with pip and apt packages."""
        await backend.start()

        # Should have built image
        mock_modal_patcher.Image.debian_slim.assert_called_once_with(python_version="3.11")

        # Should have installed packages
        mock_image = mock_modal_patcher.Image.debian_slim.return_value
        mock_image.apt_install.assert_called_once_with("git")
        mock_image.pip_install.assert_called_once_with("requests")

    @pytest.mark.asyncio
    async def test_start_idempotent(self, backend: Any, mock_modal_patcher: Any) -> None:
        """Test that calling start() multiple times is safe."""
        await backend.start()
        first_sandbox = backend._sandbox

        # Call start again
        await backend.start()

        # Should be same sandbox (no new creation)
        assert backend._sandbox is first_sandbox
        mock_modal_patcher.Sandbox.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_terminates_sandbox(self, backend: Any) -> None:
        """Test that stop() terminates the sandbox."""
        await backend.start()
        assert backend._sandbox is not None

        # Keep reference to sandbox before stop
        sandbox_ref = backend._sandbox

        await backend.stop()

        # Should have terminated
        sandbox_ref.terminate.assert_called_once()
        assert backend._sandbox is None
        assert backend._sandbox_id is None

    @pytest.mark.asyncio
    async def test_stop_when_not_started(self, backend: Any) -> None:
        """Test that stop() is safe when sandbox not started."""
        # Should not raise
        await backend.stop()

        assert backend._sandbox is None

    @pytest.mark.asyncio
    async def test_stop_handles_errors_gracefully(self, backend: Any) -> None:
        """Test that stop() handles errors during termination."""
        await backend.start()

        # Make terminate raise error
        backend._sandbox.terminate.side_effect = Exception("Termination failed")

        # Should not raise (logs error instead)
        await backend.stop()

        # Should still cleanup
        assert backend._sandbox is None
        assert backend._sandbox_id is None


class TestModalSandboxExecution:
    """Test command execution in sandbox."""

    @pytest.fixture
    def mock_modal_patcher(self) -> Any:
        """Create a patcher for modal module with exec support."""
        mock = MagicMock()

        # Mock Image
        mock_image = MagicMock()
        mock_image.apt_install = MagicMock(return_value=mock_image)
        mock_image.pip_install = MagicMock(return_value=mock_image)
        mock.Image = MagicMock()
        mock.Image.debian_slim = MagicMock(return_value=mock_image)

        # Mock Sandbox with exec
        mock_sandbox = MagicMock()
        mock_sandbox.object_id = "test-sandbox-123"
        mock_sandbox.terminate = AsyncMock()

        # Mock exec result
        mock_exec_result = MagicMock()
        mock_exec_result.returncode = 0
        mock_exec_result.stdout = "Hello from sandbox"
        mock_sandbox.exec = AsyncMock(return_value=mock_exec_result)

        mock.Sandbox = MagicMock()
        mock.Sandbox.create = MagicMock(return_value=mock_sandbox)

        patcher = patch("src.sandbox.modal.modal", mock)
        patcher.start()
        yield mock
        patcher.stop()

    @pytest.fixture
    def backend(self, mock_modal_patcher: Any) -> Any:
        """Create backend with mocked modal."""
        with patch("src.sandbox.modal._MODAL_AVAILABLE", True):
            from src.sandbox.modal import ModalSandboxBackend

            return ModalSandboxBackend(app_name="test-sandbox")

    @pytest.mark.asyncio
    async def test_execute_starts_sandbox_lazily(
        self, backend: Any, mock_modal_patcher: Any
    ) -> None:
        """Test that execute() starts sandbox on first call (lazy init)."""
        assert backend._sandbox is None

        await backend.execute("echo 'test'")

        # Should have started sandbox
        assert backend._sandbox is not None
        mock_modal_patcher.Sandbox.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_returns_output(self, backend: Any, mock_modal_patcher: Any) -> None:
        """Test that execute() returns command output."""
        result = await backend.execute("echo 'Hello'")

        assert result.output == "Hello from sandbox"
        assert result.exit_code == 0
        assert result.truncated is False

    @pytest.mark.asyncio
    async def test_execute_with_custom_timeout(self, backend: Any, mock_modal_patcher: Any) -> None:
        """Test that execute() respects custom timeout."""
        await backend.execute("sleep 1", timeout=5)

        # Should have called exec with timeout
        backend._sandbox.exec.assert_called_once()
        call_args = backend._sandbox.exec.call_args
        assert call_args[1]["timeout"] == 5

    @pytest.mark.asyncio
    async def test_execute_with_default_timeout(self, backend: Any, mock_modal_patcher: Any) -> None:
        """Test that execute() uses default timeout when not specified."""
        await backend.execute("echo 'test'")

        # Should have used default timeout
        call_args = backend._sandbox.exec.call_args
        assert call_args[1]["timeout"] == backend.timeout

    @pytest.mark.asyncio
    async def test_execute_handles_non_zero_exit_code(
        self, backend: Any, mock_modal_patcher: Any
    ) -> None:
        """Test that execute() handles non-zero exit codes."""
        # Mock failed command
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "Error occurred"
        backend._sandbox = mock_modal_patcher.Sandbox.create.return_value
        backend._sandbox.exec = AsyncMock(return_value=mock_result)

        result = await backend.execute("false")

        assert result.exit_code == 1
        assert result.output == "Error occurred"

    @pytest.mark.asyncio
    async def test_execute_detects_truncation(self, backend: Any, mock_modal_patcher: Any) -> None:
        """Test that execute() detects truncated output."""
        # Mock large output (>1MB)
        large_output = "x" * (1024 * 1024 + 1)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = large_output
        backend._sandbox = mock_modal_patcher.Sandbox.create.return_value
        backend._sandbox.exec = AsyncMock(return_value=mock_result)

        result = await backend.execute("echo 'large'")

        assert result.truncated is True


class TestModalSandboxErrors:
    """Test error handling in sandbox."""

    @pytest.fixture
    def mock_modal(self) -> Any:
        """Mock modal module."""
        mock = MagicMock()

        # Mock Image
        mock_image = MagicMock()
        mock_image.apt_install = MagicMock(return_value=mock_image)
        mock_image.pip_install = MagicMock(return_value=mock_image)
        mock.Image = MagicMock()
        mock.Image.debian_slim = MagicMock(return_value=mock_image)

        # Mock Sandbox
        mock_sandbox = MagicMock()
        mock_sandbox.object_id = "test-sandbox-123"
        mock_sandbox.terminate = AsyncMock()
        mock_sandbox.exec = AsyncMock()

        mock.Sandbox = MagicMock()
        mock.Sandbox.create = MagicMock(return_value=mock_sandbox)

        return mock

    @pytest.fixture
    def backend(self, mock_modal: Any) -> Any:
        """Create backend with mocked modal."""
        with patch("src.sandbox.modal.modal", mock_modal):
            with patch("src.sandbox.modal._MODAL_AVAILABLE", True):
                from src.sandbox.modal import ModalSandboxBackend

                return ModalSandboxBackend(app_name="test-sandbox")

    @pytest.mark.asyncio
    async def test_execute_timeout_raises_error(self, backend: Any) -> None:
        """Test that timeout raises SandboxTimeoutError."""
        from src.sandbox.modal import SandboxTimeoutError

        # Mock timeout
        backend._sandbox = backend._sandbox or MagicMock()
        backend._sandbox.exec = AsyncMock(side_effect=TimeoutError("Timeout"))
        backend._sandbox_id = "test-123"

        with pytest.raises(SandboxTimeoutError) as exc_info:
            await backend.execute("sleep 999")

        assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_execute_connection_error_raises_unavailable(
        self, backend: Any
    ) -> None:
        """Test that connection errors raise SandboxUnavailableError."""
        from src.sandbox.modal import SandboxUnavailableError

        # Mock connection error
        backend._sandbox = backend._sandbox or MagicMock()
        backend._sandbox.exec = AsyncMock(
            side_effect=Exception("Connection refused")
        )
        backend._sandbox_id = "test-123"

        with pytest.raises(SandboxUnavailableError) as exc_info:
            await backend.execute("echo 'test'")

        assert "unavailable" in str(exc_info.value).lower() or "connection" in str(
            exc_info.value
        ).lower()

    @pytest.mark.asyncio
    async def test_execute_generic_error_raises_sandbox_error(
        self, backend: Any
    ) -> None:
        """Test that generic errors raise SandboxError."""
        from src.sandbox.modal import SandboxError

        # Mock generic error
        backend._sandbox = backend._sandbox or MagicMock()
        backend._sandbox.exec = AsyncMock(side_effect=Exception("Unknown error"))
        backend._sandbox_id = "test-123"

        with pytest.raises(SandboxError) as exc_info:
            await backend.execute("echo 'test'")

        assert "failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_start_error_raises_sandbox_error(
        self, backend: Any, mock_modal: Any
    ) -> None:
        """Test that start errors raise SandboxError."""
        from src.sandbox.modal import SandboxError

        # Mock start failure
        mock_modal.Sandbox.create.side_effect = Exception("Start failed")

        with pytest.raises(SandboxError) as exc_info:
            await backend.start()

        assert "failed to start" in str(exc_info.value).lower()


class TestModalSandboxFilesystemOperations:
    """Test filesystem operations via shell delegation."""

    @pytest.fixture
    def backend(self) -> Any:
        """Create backend with mocked execute."""
        with patch("src.sandbox.modal._MODAL_AVAILABLE", True):
            from src.sandbox.modal import ExecuteResponse, ModalSandboxBackend

            backend = ModalSandboxBackend(app_name="test-sandbox")

            # Mock execute to avoid actual sandbox
            async def mock_execute(
                command: str, timeout: int | None = None
            ) -> ExecuteResponse:
                # Simulate different commands
                if "ls -la" in command:
                    # Format with --time-style=+%s: perms links owner group size timestamp . filename
                    # The . is needed because split(None, 8) expects 9 parts
                    return ExecuteResponse(
                        output="total 8\n-rw-r--r-- 1 user user 4096 1234567890 . . file.txt\n",
                        exit_code=0,
                        truncated=False,
                    )
                elif "cat" in command:
                    return ExecuteResponse(
                        output="file contents", exit_code=0, truncated=False
                    )
                elif "echo" in command and ">" in command or "sed" in command:
                    return ExecuteResponse(output="", exit_code=0, truncated=False)
                elif "find" in command and "-ls" in command:
                    # Format: inode blocks perms links owner group size date time name
                    return ExecuteResponse(
                        output="12345 8 -rw-r--r-- 1 user user 4096 Jan 1 12:00 ./test.txt\n",
                        exit_code=0,
                        truncated=False,
                    )
                elif "grep" in command:
                    return ExecuteResponse(
                        output="file.txt:10:matching line\n",
                        exit_code=0,
                        truncated=False,
                    )
                else:
                    return ExecuteResponse(output="", exit_code=0, truncated=False)

            backend.execute = mock_execute  # type: ignore[method-assign]
            return backend

    @pytest.mark.asyncio
    async def test_ls_info(self, backend: Any) -> None:
        """Test ls_info returns file metadata."""
        files = await backend.ls_info("/tmp")

        assert len(files) == 1
        assert files[0].path == "/tmp/file.txt"
        assert files[0].size == 4096
        assert files[0].is_dir is False

    @pytest.mark.asyncio
    async def test_read(self, backend: Any) -> None:
        """Test read returns file contents."""
        content = await backend.read("/tmp/test.txt")

        assert content == "file contents"

    @pytest.mark.asyncio
    async def test_write(self, backend: Any) -> None:
        """Test write creates file."""
        result = await backend.write("/tmp/test.txt", "Hello World")

        assert result.success is True
        assert result.path == "/tmp/test.txt"
        assert result.bytes_written > 0

    @pytest.mark.asyncio
    async def test_edit(self, backend: Any) -> None:
        """Test edit replaces text in file."""
        result = await backend.edit("/tmp/test.txt", "old", "new")

        assert result.success is True
        assert result.path == "/tmp/test.txt"
        assert result.changes_made > 0

    @pytest.mark.asyncio
    async def test_glob_info(self, backend: Any) -> None:
        """Test glob_info finds matching files."""
        files = await backend.glob_info("*.txt")

        assert len(files) == 1
        assert files[0].path == "./test.txt"

    @pytest.mark.asyncio
    async def test_grep_raw(self, backend: Any) -> None:
        """Test grep_raw searches for pattern."""
        matches = await backend.grep_raw("pattern", "/tmp")

        assert len(matches) == 1
        assert matches[0].path == "file.txt"
        assert matches[0].line_number == 10
        assert matches[0].line_content == "matching line"

    @pytest.mark.asyncio
    async def test_upload_files(self, backend: Any) -> None:
        """Test upload_files writes multiple files."""
        files = {
            "/tmp/file1.txt": b"content1",
            "/tmp/file2.txt": b"content2",
        }

        responses = await backend.upload_files(files)

        assert len(responses) == 2
        assert all(r.success for r in responses)

    @pytest.mark.asyncio
    async def test_download_files(self, backend: Any) -> None:
        """Test download_files reads multiple files."""
        paths = ["/tmp/file1.txt", "/tmp/file2.txt"]

        responses = await backend.download_files(paths)

        assert len(responses) == 2
        assert all(r.success for r in responses)


class TestModalSandboxEnvironmentVariables:
    """Test environment variable handling."""

    @pytest.fixture
    def mock_modal(self) -> Any:
        """Mock modal module."""
        mock = MagicMock()

        # Mock Image
        mock_image = MagicMock()
        mock_image.apt_install = MagicMock(return_value=mock_image)
        mock_image.pip_install = MagicMock(return_value=mock_image)
        mock.Image = MagicMock()
        mock.Image.debian_slim = MagicMock(return_value=mock_image)

        # Mock Sandbox
        mock_sandbox = MagicMock()
        mock_sandbox.object_id = "test-sandbox-123"
        mock.Sandbox = MagicMock()
        mock.Sandbox.create = MagicMock(return_value=mock_sandbox)

        return mock

    @pytest.mark.asyncio
    async def test_env_vars_passed_to_sandbox(self, mock_modal: Any) -> None:
        """Test that environment variables are passed to sandbox."""
        with patch("src.sandbox.modal.modal", mock_modal):
            with patch("src.sandbox.modal._MODAL_AVAILABLE", True):
                from src.sandbox.modal import ModalSandboxBackend

                env_vars = {"API_KEY": "secret", "DEBUG": "true"}
                backend = ModalSandboxBackend(env_vars=env_vars)

                await backend.start()

                # Should have passed env vars to sandbox
                call_kwargs = mock_modal.Sandbox.create.call_args[1]
                assert call_kwargs["environment"] == env_vars


class TestModalSandboxEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def backend(self) -> Any:
        """Create backend with mocked execute."""
        with patch("src.sandbox.modal._MODAL_AVAILABLE", True):
            from src.sandbox.modal import ExecuteResponse, ModalSandboxBackend

            backend = ModalSandboxBackend(app_name="test-sandbox")

            # Mock execute
            async def mock_execute(
                command: str, timeout: int | None = None
            ) -> ExecuteResponse:
                if "error" in command:
                    return ExecuteResponse(
                        output="Error message", exit_code=1, truncated=False
                    )
                return ExecuteResponse(output="", exit_code=0, truncated=False)

            backend.execute = mock_execute  # type: ignore[method-assign]
            return backend

    @pytest.mark.asyncio
    async def test_ls_info_handles_error(self, backend: Any) -> None:
        """Test that ls_info raises error on failure."""
        from src.sandbox.modal import SandboxError

        with pytest.raises(SandboxError) as exc_info:
            await backend.ls_info("error")

        assert "ls failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_read_handles_error(self, backend: Any) -> None:
        """Test that read raises error on failure."""
        from src.sandbox.modal import SandboxError

        with pytest.raises(SandboxError) as exc_info:
            await backend.read("error")

        assert "read failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_write_handles_error(self, backend: Any) -> None:
        """Test that write raises error on failure."""
        from src.sandbox.modal import SandboxError

        with pytest.raises(SandboxError) as exc_info:
            await backend.write("error", "content")

        assert "write failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_upload_files_handles_partial_failure(self, backend: Any) -> None:
        """Test that upload_files handles partial failures."""
        files = {
            "good.txt": b"content",
            "error": b"content",
        }

        responses = await backend.upload_files(files)

        assert len(responses) == 2
        # At least one should fail
        assert not all(r.success for r in responses)

    @pytest.mark.asyncio
    async def test_download_files_handles_partial_failure(self, backend: Any) -> None:
        """Test that download_files handles partial failures."""
        paths = ["good.txt", "error"]

        responses = await backend.download_files(paths)

        assert len(responses) == 2
        # At least one should fail
        assert not all(r.success for r in responses)
