"""
Modal sandbox backend for isolated code execution.

This module provides a Modal-based sandbox backend that implements the
SandboxBackendProtocol. It creates isolated environments for running untrusted
code with pre-installed dependencies.

Security Model:
    - Isolated execution environment via Modal containers
    - Configurable resource limits (CPU, memory, timeout)
    - No direct filesystem access to host machine
    - Network access controlled by Modal's security model

Example:
    >>> sandbox = ModalSandboxBackend(
    ...     app_name="my-sandbox",
    ...     timeout=300,
    ...     pip_packages=["requests", "beautifulsoup4"]
    ... )
    >>> result = await sandbox.execute("python -c 'import requests; print(requests.__version__)'")
    >>> print(result.output)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

# Define fallback types (always available)
from dataclasses import dataclass


@dataclass
class ExecuteResponse:
    """Response from command execution."""
    output: str
    exit_code: int
    truncated: bool = False


@dataclass
class FileInfo:
    """File metadata."""
    path: str
    size: int
    is_dir: bool
    modified_time: float


@dataclass
class WriteResult:
    """Result of write operation."""
    success: bool
    path: str
    bytes_written: int


@dataclass
class EditResult:
    """Result of edit operation."""
    success: bool
    path: str
    changes_made: int


@dataclass
class GrepMatch:
    """Grep search result."""
    path: str
    line_number: int
    line_content: str
    match_start: int
    match_end: int


@dataclass
class FileUploadResponse:
    """Response from file upload."""
    success: bool
    path: str
    bytes_uploaded: int


@dataclass
class FileDownloadResponse:
    """Response from file download."""
    success: bool
    path: str
    content: bytes


# Protocol base class
if TYPE_CHECKING:
    from typing import Protocol

    class SandboxBackendProtocol(Protocol):
        """Protocol for sandbox backends."""

        async def execute(
            self, command: str, timeout: int | None = None
        ) -> ExecuteResponse:
            """Execute a command in the sandbox."""
            ...
else:
    SandboxBackendProtocol = object

# Guard modal import
try:
    import modal

    _MODAL_AVAILABLE = True
except ImportError:
    modal = None  # type: ignore[assignment]
    _MODAL_AVAILABLE = False


class SandboxError(Exception):
    """Base sandbox error."""

    pass


class SandboxTimeoutError(SandboxError):
    """Command exceeded timeout."""

    pass


class SandboxUnavailableError(SandboxError):
    """Sandbox service unreachable."""

    pass


DEFAULT_PIP_PACKAGES = [
    "requests",
    "beautifulsoup4",
    "pyyaml",
]


class ModalSandboxBackend:
    """Modal sandbox backend for isolated code execution.

    Creates a Modal sandbox with pre-installed dependencies. The agent
    gets an execute(command) tool for running shell commands in an isolated
    container environment.

    Features:
        - Lazy initialization: Sandbox not started until first execute() call
        - Configurable resources: CPU, memory, timeout
        - Pre-installed packages: pip and apt packages
        - Environment variables: Custom env vars for sandbox
        - Custom image: Bring your own Modal image

    Requirements:
        - modal package: pip install emonk[modal]
        - Modal account: modal token new

    Example:
        >>> sandbox = ModalSandboxBackend(
        ...     app_name="my-sandbox",
        ...     timeout=300,
        ...     cpu=2,
        ...     memory_mb=2048,
        ...     pip_packages=["requests", "pandas"],
        ...     env_vars={"API_KEY": "secret"}
        ... )
        >>>
        >>> # Sandbox starts on first execute() call
        >>> result = await sandbox.execute("python --version")
        >>> print(result.output)
        >>>
        >>> # Cleanup when done
        >>> await sandbox.stop()
    """

    def __init__(
        self,
        app_name: str = "emonk-sandbox",
        *,
        timeout: int = 600,
        cpu: int = 2,
        memory_mb: int = 2048,
        pip_packages: list[str] | None = None,
        apt_packages: list[str] | None = None,
        env_vars: dict[str, str] | None = None,
        image: object | None = None,  # modal.Image
    ):
        """Initialize Modal sandbox backend.

        Args:
            app_name: Name for the Modal app (default: "emonk-sandbox")
            timeout: Maximum execution time in seconds (default: 600)
            cpu: Number of CPU cores (default: 2)
            memory_mb: Memory limit in MB (default: 2048)
            pip_packages: Python packages to install (default: requests, beautifulsoup4, pyyaml)
            apt_packages: System packages to install (default: [])
            env_vars: Environment variables for sandbox (default: {})
            image: Custom Modal image (default: auto-built from packages)

        Raises:
            ImportError: If modal package is not installed
        """
        if not _MODAL_AVAILABLE:
            raise ImportError(
                "modal package required for sandbox execution. "
                "Install with: pip install emonk[modal]"
            )

        self.app_name = app_name
        self.timeout = timeout
        self.cpu = cpu
        self.memory_mb = memory_mb
        self.pip_packages = pip_packages or DEFAULT_PIP_PACKAGES
        self.apt_packages = apt_packages or []
        self.env_vars = env_vars or {}
        self._custom_image = image

        # Lazy initialization - sandbox not started until first execute()
        self._sandbox: Any = None
        self._sandbox_id: str | None = None

        logger.info(
            f"Initialized ModalSandboxBackend: {app_name}",
            extra={
                "component": "modal_sandbox",
                "app_name": app_name,
                "timeout": timeout,
                "cpu": cpu,
                "memory_mb": memory_mb,
                "pip_packages_count": len(self.pip_packages),
                "apt_packages_count": len(self.apt_packages),
            },
        )

    @property
    def id(self) -> str | None:
        """Get sandbox ID.

        Returns:
            Sandbox ID if started, None otherwise
        """
        return self._sandbox_id

    async def execute(
        self, command: str, timeout: int | None = None
    ) -> ExecuteResponse:
        """Execute a shell command in the sandbox.

        This method automatically starts the sandbox on first call (lazy initialization).
        All commands run in the same sandbox instance for the lifetime of this object.

        Args:
            command: Shell command to execute
            timeout: Override default timeout for this command (seconds)

        Returns:
            ExecuteResponse with output, exit_code, and truncated flag

        Raises:
            SandboxTimeoutError: If command exceeds timeout
            SandboxUnavailableError: If sandbox cannot be reached
            SandboxError: For other sandbox errors

        Example:
            >>> result = await sandbox.execute("ls -la /tmp")
            >>> if result.exit_code == 0:
            ...     print(result.output)
        """
        # Ensure sandbox is started (lazy init)
        await self._ensure_started()

        # Use provided timeout or default
        cmd_timeout = timeout or self.timeout

        logger.info(
            f"Executing command in sandbox: {command[:100]}",
            extra={
                "component": "modal_sandbox",
                "sandbox_id": self._sandbox_id,
                "command_length": len(command),
                "timeout": cmd_timeout,
            },
        )

        try:
            # Execute command via Modal sandbox
            result = await self._sandbox.exec(
                command,
                timeout=cmd_timeout,
            )

            # Parse result
            exit_code = result.returncode if hasattr(result, "returncode") else 0
            output = result.stdout if hasattr(result, "stdout") else str(result)

            # Check for truncation (Modal may truncate large outputs)
            truncated = len(output) >= 1024 * 1024  # 1MB threshold

            logger.info(
                "Command executed successfully",
                extra={
                    "component": "modal_sandbox",
                    "sandbox_id": self._sandbox_id,
                    "exit_code": exit_code,
                    "output_length": len(output),
                    "truncated": truncated,
                },
            )

            return ExecuteResponse(
                output=output, exit_code=exit_code, truncated=truncated
            )

        except TimeoutError as e:
            error_msg = f"Command exceeded {cmd_timeout}s timeout"
            logger.error(
                error_msg,
                extra={
                    "component": "modal_sandbox",
                    "sandbox_id": self._sandbox_id,
                    "timeout": cmd_timeout,
                    "error": str(e),
                },
            )
            raise SandboxTimeoutError(error_msg) from e

        except Exception as e:
            error_msg = f"Sandbox execution failed: {e}"
            logger.error(
                error_msg,
                extra={
                    "component": "modal_sandbox",
                    "sandbox_id": self._sandbox_id,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
            )

            # Check if it's a connection/availability error
            if "connection" in str(e).lower() or "unavailable" in str(e).lower():
                raise SandboxUnavailableError(error_msg) from e

            raise SandboxError(error_msg) from e

    async def start(self) -> None:
        """Start the sandbox.

        This method is called automatically on first execute() call.
        You can also call it explicitly to pre-warm the sandbox.

        Raises:
            SandboxError: If sandbox fails to start
        """
        if self._sandbox is not None:
            logger.warning(
                "Sandbox already started",
                extra={"component": "modal_sandbox", "sandbox_id": self._sandbox_id},
            )
            return

        logger.info(
            "Starting Modal sandbox",
            extra={"component": "modal_sandbox", "app_name": self.app_name},
        )

        try:
            # Build image with dependencies
            image = self._custom_image or self._build_image()

            # Create Modal sandbox
            # Note: Modal's Sandbox.create() API may vary by version
            # Try with environment parameter first, fall back to without
            try:
                self._sandbox = modal.Sandbox.create(
                    image=image,
                    cpu=self.cpu,
                    memory=self.memory_mb,
                    timeout=self.timeout,
                    environment=self.env_vars,
                )
            except TypeError:
                # Fallback for older Modal versions without environment parameter
                self._sandbox = modal.Sandbox.create(
                    image=image,
                    cpu=self.cpu,
                    memory=self.memory_mb,
                    timeout=self.timeout,
                )

            self._sandbox_id = getattr(self._sandbox, "object_id", "unknown")

            logger.info(
                "Modal sandbox started",
                extra={
                    "component": "modal_sandbox",
                    "sandbox_id": self._sandbox_id,
                    "app_name": self.app_name,
                },
            )

        except Exception as e:
            error_msg = f"Failed to start sandbox: {e}"
            logger.error(
                error_msg,
                extra={
                    "component": "modal_sandbox",
                    "app_name": self.app_name,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
            )
            raise SandboxError(error_msg) from e

    async def stop(self) -> None:
        """Stop the sandbox and cleanup resources.

        This method should be called when you're done with the sandbox
        to avoid leaving containers running.

        Example:
            >>> try:
            ...     result = await sandbox.execute("echo 'Hello'")
            ... finally:
            ...     await sandbox.stop()
        """
        if self._sandbox is None:
            logger.warning(
                "Sandbox not started, nothing to stop",
                extra={"component": "modal_sandbox"},
            )
            return

        logger.info(
            "Stopping Modal sandbox",
            extra={
                "component": "modal_sandbox",
                "sandbox_id": self._sandbox_id,
            },
        )

        try:
            # Terminate Modal sandbox
            if hasattr(self._sandbox, "terminate"):
                await self._sandbox.terminate()
            elif hasattr(self._sandbox, "stop"):
                await self._sandbox.stop()

            logger.info(
                "Modal sandbox stopped",
                extra={
                    "component": "modal_sandbox",
                    "sandbox_id": self._sandbox_id,
                },
            )

        except Exception as e:
            logger.error(
                f"Error stopping sandbox: {e}",
                extra={
                    "component": "modal_sandbox",
                    "sandbox_id": self._sandbox_id,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
            )

        finally:
            self._sandbox = None
            self._sandbox_id = None

    async def _ensure_started(self) -> None:
        """Ensure sandbox is started (lazy initialization).

        This method is called before every execute() to ensure the sandbox
        is running. It's a no-op if the sandbox is already started.
        """
        if self._sandbox is None:
            await self.start()

    def _build_image(self) -> Any:
        """Build Modal image with dependencies.

        Creates a Debian-based image with:
            - Python 3.11
            - Pip packages from self.pip_packages
            - Apt packages from self.apt_packages

        Returns:
            modal.Image configured with dependencies
        """
        logger.info(
            "Building Modal image",
            extra={
                "component": "modal_sandbox",
                "pip_packages": self.pip_packages,
                "apt_packages": self.apt_packages,
            },
        )

        # Start with Debian Slim base
        image = modal.Image.debian_slim(python_version="3.11")

        # Install apt packages if any
        if self.apt_packages:
            image = image.apt_install(*self.apt_packages)

        # Install pip packages if any
        if self.pip_packages:
            image = image.pip_install(*self.pip_packages)

        return image

    # ========================================================================
    # SandboxBackendProtocol Implementation (Filesystem Methods)
    # ========================================================================
    # These methods delegate to shell commands via execute()

    async def ls_info(self, path: str = ".") -> list[FileInfo]:
        """List directory contents with file metadata.

        Args:
            path: Directory path to list (default: current directory)

        Returns:
            List of FileInfo objects with metadata

        Raises:
            SandboxError: If ls command fails
        """
        # Use ls with JSON output for easy parsing
        command = f"ls -la --time-style=+%s '{path}' 2>&1"
        result = await self.execute(command)

        if result.exit_code != 0:
            raise SandboxError(f"ls failed: {result.output}")

        # Parse ls output into FileInfo objects
        files = []
        lines = result.output.strip().split("\n")

        # Skip first line if it starts with "total"
        start_idx = 1 if lines and lines[0].startswith("total") else 0

        for line in lines[start_idx:]:
            if not line or not line.strip():
                continue

            parts = line.split(None, 8)
            if len(parts) < 9:
                continue

            # Skip . and .. entries
            name = parts[8]
            if name in (".", ".."):
                continue

            is_dir = parts[0].startswith("d")
            size = int(parts[4])
            modified_time = float(parts[5])

            files.append(
                FileInfo(
                    path=f"{path}/{name}".replace("//", "/"),
                    size=size,
                    is_dir=is_dir,
                    modified_time=modified_time,
                )
            )

        return files

    async def read(self, path: str) -> str:
        """Read file contents.

        Args:
            path: File path to read

        Returns:
            File contents as string

        Raises:
            SandboxError: If read fails
        """
        command = f"cat '{path}' 2>&1"
        result = await self.execute(command)

        if result.exit_code != 0:
            raise SandboxError(f"read failed: {result.output}")

        return result.output

    async def write(self, path: str, content: str) -> WriteResult:
        """Write content to file.

        Args:
            path: File path to write
            content: Content to write

        Returns:
            WriteResult with success status and bytes written

        Raises:
            SandboxError: If write fails
        """
        # Escape content for shell
        escaped_content = content.replace("'", "'\\''")
        command = f"echo '{escaped_content}' > '{path}' 2>&1"
        result = await self.execute(command)

        if result.exit_code != 0:
            raise SandboxError(f"write failed: {result.output}")

        return WriteResult(
            success=True, path=path, bytes_written=len(content.encode("utf-8"))
        )

    async def edit(self, path: str, old_str: str, new_str: str) -> EditResult:
        """Edit file by replacing old_str with new_str.

        Args:
            path: File path to edit
            old_str: String to find and replace
            new_str: Replacement string

        Returns:
            EditResult with success status and number of changes

        Raises:
            SandboxError: If edit fails
        """
        # Use sed for in-place editing
        escaped_old = old_str.replace("/", "\\/").replace("'", "'\\''")
        escaped_new = new_str.replace("/", "\\/").replace("'", "'\\''")
        command = f"sed -i 's/{escaped_old}/{escaped_new}/g' '{path}' 2>&1"
        result = await self.execute(command)

        if result.exit_code != 0:
            raise SandboxError(f"edit failed: {result.output}")

        # Count changes (approximate)
        changes_made = 1  # sed doesn't report count easily

        return EditResult(success=True, path=path, changes_made=changes_made)

    async def glob_info(self, pattern: str) -> list[FileInfo]:
        """Find files matching glob pattern.

        Args:
            pattern: Glob pattern (e.g., "*.py", "**/*.txt")

        Returns:
            List of FileInfo objects for matching files

        Raises:
            SandboxError: If glob fails
        """
        # Use find with pattern
        command = f"find . -name '{pattern}' -ls 2>&1"
        result = await self.execute(command)

        if result.exit_code != 0:
            raise SandboxError(f"glob failed: {result.output}")

        # Parse find output
        files = []
        for line in result.output.strip().split("\n"):
            if not line or not line.strip():
                continue

            parts = line.split(None, 10)
            if len(parts) < 11:
                continue

            # find -ls format: inode blocks perms links owner group size date time name
            is_dir = parts[2].startswith("d")
            try:
                size = int(parts[6])
            except (ValueError, IndexError):
                size = 0
            name = parts[10]

            files.append(
                FileInfo(path=name, size=size, is_dir=is_dir, modified_time=0.0)
            )

        return files

    async def grep_raw(
        self, pattern: str, path: str = ".", recursive: bool = True
    ) -> list[GrepMatch]:
        """Search for pattern in files.

        Args:
            pattern: Regex pattern to search
            path: Directory to search (default: current directory)
            recursive: Search recursively (default: True)

        Returns:
            List of GrepMatch objects with line numbers and content

        Raises:
            SandboxError: If grep fails
        """
        # Use grep with line numbers
        recursive_flag = "-r" if recursive else ""
        command = f"grep -n {recursive_flag} '{pattern}' '{path}' 2>&1"
        result = await self.execute(command)

        # grep returns 1 if no matches, which is not an error
        if result.exit_code not in (0, 1):
            raise SandboxError(f"grep failed: {result.output}")

        # Parse grep output
        matches = []
        for line in result.output.strip().split("\n"):
            if not line:
                continue

            # Format: path:line_number:line_content
            parts = line.split(":", 2)
            if len(parts) < 3:
                continue

            file_path = parts[0]
            line_number = int(parts[1])
            line_content = parts[2]

            # Find match position (approximate)
            match_start = line_content.find(pattern)
            match_end = match_start + len(pattern) if match_start >= 0 else 0

            matches.append(
                GrepMatch(
                    path=file_path,
                    line_number=line_number,
                    line_content=line_content,
                    match_start=match_start,
                    match_end=match_end,
                )
            )

        return matches

    async def upload_files(
        self, files: dict[str, bytes]
    ) -> list[FileUploadResponse]:
        """Upload multiple files to sandbox.

        Args:
            files: Dict mapping destination paths to file contents

        Returns:
            List of FileUploadResponse objects

        Raises:
            SandboxError: If upload fails
        """
        responses = []

        for path, content in files.items():
            # Write file via execute
            try:
                result = await self.write(path, content.decode("utf-8"))
                responses.append(
                    FileUploadResponse(
                        success=result.success,
                        path=path,
                        bytes_uploaded=result.bytes_written,
                    )
                )
            except Exception as e:
                logger.error(
                    f"Failed to upload {path}: {e}",
                    extra={"component": "modal_sandbox", "path": path},
                )
                responses.append(
                    FileUploadResponse(success=False, path=path, bytes_uploaded=0)
                )

        return responses

    async def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        """Download multiple files from sandbox.

        Args:
            paths: List of file paths to download

        Returns:
            List of FileDownloadResponse objects

        Raises:
            SandboxError: If download fails
        """
        responses = []

        for path in paths:
            # Read file via execute
            try:
                content = await self.read(path)
                responses.append(
                    FileDownloadResponse(
                        success=True, path=path, content=content.encode("utf-8")
                    )
                )
            except Exception as e:
                logger.error(
                    f"Failed to download {path}: {e}",
                    extra={"component": "modal_sandbox", "path": path},
                )
                responses.append(
                    FileDownloadResponse(success=False, path=path, content=b"")
                )

        return responses
