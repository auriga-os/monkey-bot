"""Abstract base class for cloud storage backends.

This module provides the CloudStorageBackend abstract class that implements
the deep agents BackendProtocol for cloud storage operations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

__all__ = [
    "CloudStorageBackend",
    "CloudStorageError",
    "FileNotFoundError",
    "StorageUnavailableError",
    "ConcurrencyError",
    "PermissionError",
    "FileInfo",
    "WriteResult",
    "EditResult",
    "GrepMatch",
    "FileUploadResponse",
    "FileDownloadResponse",
    "BackendProtocol",
]

# Try to import deep agents types, fall back to defining our own for development
try:
    from deepagents.backends.protocol import (
        BackendProtocol,
        EditResult,
        FileInfo,
        GrepMatch,
        WriteResult,
    )
except ImportError:
    # Define minimal protocol types for development without deepagents
    from typing import Any, TypedDict

    class FileInfo(TypedDict, total=False):  # type: ignore[no-redef]
        """Information about a file or directory."""

        path: str  # Required
        is_dir: bool
        size: int
        modified_at: str

    class WriteResult(TypedDict, total=False):  # type: ignore[no-redef]
        """Result of a write operation."""

        error: str | None
        path: str | None
        files_update: dict[str, Any] | None

    class EditResult(TypedDict, total=False):  # type: ignore[no-redef]
        """Result of an edit operation."""

        error: str | None
        path: str | None
        files_update: dict[str, Any] | None
        occurrences: int | None

    class GrepMatch(TypedDict):  # type: ignore[no-redef]
        """A single grep match result."""

        path: str
        line: int
        text: str

    class BackendProtocol:  # type: ignore[no-redef]
        """Protocol for backend implementations."""

        pass


# Define response types for upload/download (not in deepagents protocol)
from typing import Any, TypedDict  # noqa: F401


class FileUploadResponse(TypedDict, total=False):
    """Response from uploading a file."""

    path: str
    error: str | None


class FileDownloadResponse(TypedDict, total=False):
    """Response from downloading a file."""

    path: str
    content: str
    error: str | None


class CloudStorageError(Exception):
    """Base error for cloud storage operations."""

    pass


class FileNotFoundError(CloudStorageError):
    """File not found in cloud storage."""

    def __init__(self, path: str):
        """Initialize FileNotFoundError.

        Args:
            path: Path to the file that was not found
        """
        self.path = path
        super().__init__(f"File not found: {path}")


class StorageUnavailableError(CloudStorageError):
    """Cloud storage service unavailable."""

    pass


class ConcurrencyError(CloudStorageError):
    """Concurrent modification detected."""

    def __init__(self, path: str):
        """Initialize ConcurrencyError.

        Args:
            path: Path to the file with concurrent modification
        """
        self.path = path
        super().__init__(f"Concurrent modification detected: {path}")


class PermissionError(CloudStorageError):
    """Access denied to cloud storage resource."""

    def __init__(self, path: str):
        """Initialize PermissionError.

        Args:
            path: Path to the resource with permission denied
        """
        self.path = path
        super().__init__(f"Permission denied: {path}")


class CloudStorageBackend(ABC):
    """Abstract cloud storage backend.

    Subclass this to create backends for any cloud provider (GCS, S3, Azure Blob, etc.).
    Implements the deep agents BackendProtocol interface.

    This backend provides:
    - File operations (read, write, edit, list)
    - Pattern matching (glob, grep)
    - Batch operations (upload_files, download_files)
    - Path normalization and security (prevents path traversal)
    - Prefix-based workspace isolation

    Example:
        >>> class MyBackend(CloudStorageBackend):
        ...     def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> str:
        ...         # Implementation
        ...         pass
        ...     # ... implement other abstract methods
    """

    def __init__(self, bucket: str, prefix: str = "", project_id: str | None = None):
        """Initialize CloudStorageBackend.

        Args:
            bucket: Cloud storage bucket name
            prefix: Optional prefix for all paths (workspace isolation)
            project_id: Optional project/account ID for the cloud provider
        """
        self.bucket_name = bucket
        self.prefix = (
            prefix.strip("/") + "/" if prefix and not prefix.endswith("/") else prefix
        )
        self.project_id = project_id

    def _normalize_path(self, path: str) -> str:
        """Normalize path: strip leading /, apply prefix, reject traversal.

        Args:
            path: Input path to normalize

        Returns:
            Normalized path with prefix applied

        Raises:
            ValueError: If path contains path traversal attempts (..)
        """
        # Reject path traversal
        if ".." in path:
            raise ValueError(f"Path traversal not allowed: {path}")

        # Strip leading slash
        clean = path.lstrip("/")

        # Apply prefix
        if self.prefix and clean.startswith(self.prefix):
            return clean  # Already has prefix

        return f"{self.prefix}{clean}" if self.prefix else clean

    def _is_directory(self, path: str) -> bool:
        """Check if path represents a directory.

        Args:
            path: Path to check

        Returns:
            True if path is a directory (empty string or ends with /)
        """
        return path == "" or path.endswith("/")

    @abstractmethod
    def ls_info(self, path: str) -> list[FileInfo]:
        """List files and directories at the given path.

        Args:
            path: Directory path to list

        Returns:
            List of FileInfo objects for files and subdirectories
        """
        ...

    @abstractmethod
    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> str:
        """Read file contents with line-based offset and limit.

        Args:
            file_path: Path to the file to read
            offset: Line number to start reading from (0-indexed)
            limit: Maximum number of lines to read

        Returns:
            File contents as string

        Raises:
            FileNotFoundError: If file does not exist
        """
        ...

    @abstractmethod
    def write(self, file_path: str, content: str) -> WriteResult:
        """Write (create or overwrite) a file.

        Args:
            file_path: Path to the file to write
            content: Content to write to the file

        Returns:
            WriteResult with operation status

        Raises:
            PermissionError: If write access is denied
        """
        ...

    @abstractmethod
    def edit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> EditResult:
        """Edit a file by replacing a string.

        Args:
            file_path: Path to the file to edit
            old_string: String to find and replace
            new_string: Replacement string
            replace_all: If True, replace all occurrences; if False, replace first only

        Returns:
            EditResult with operation status

        Raises:
            FileNotFoundError: If file does not exist
            ValueError: If old_string is not found in file
            ConcurrencyError: If file was modified concurrently
        """
        ...

    @abstractmethod
    def glob_info(self, pattern: str, path: str = "/") -> list[FileInfo]:
        """Find files matching a glob pattern.

        Args:
            pattern: Glob pattern (e.g., "*.py", "test_*.txt")
            path: Base path to search within

        Returns:
            List of FileInfo objects for matching files
        """
        ...

    @abstractmethod
    def grep_raw(
        self,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
    ) -> list[GrepMatch] | str:
        """Search file contents by regex pattern.

        Args:
            pattern: Regular expression pattern to search for
            path: Optional path to limit search scope
            glob: Optional glob pattern to filter files

        Returns:
            List of GrepMatch objects or formatted string with results
        """
        ...

    @abstractmethod
    def upload_files(self, files: list[dict[str, str]]) -> list[FileUploadResponse]:
        """Upload multiple files.

        Args:
            files: List of file dicts with 'path' and 'content' keys

        Returns:
            List of FileUploadResponse objects
        """
        ...

    @abstractmethod
    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        """Download multiple files.

        Args:
            paths: List of file paths to download

        Returns:
            List of FileDownloadResponse objects with file contents
        """
        ...
