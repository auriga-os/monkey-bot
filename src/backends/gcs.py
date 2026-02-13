"""Google Cloud Storage backend implementation.

This module provides GCSBackend, a production-ready implementation of
CloudStorageBackend for Google Cloud Storage with:
- Read caching for performance
- Atomic edits using if_generation_match
- Comprehensive error mapping
- Pattern matching (glob, grep)
"""

from __future__ import annotations

import fnmatch
import logging
import re
import time
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from google.api_core import exceptions as gcs_exceptions
    from google.cloud import storage
else:
    try:
        from google.api_core import exceptions as gcs_exceptions
        from google.cloud import storage
    except ImportError:
        storage = None  # type: ignore[misc]
        gcs_exceptions = None  # type: ignore[misc]

from src.backends.base import (
    CloudStorageBackend,
    ConcurrencyError,
    EditResult,
    FileDownloadResponse,
    FileInfo,
    FileNotFoundError,
    FileUploadResponse,
    GrepMatch,
    PermissionError,
    StorageUnavailableError,
    WriteResult,
)

logger = logging.getLogger(__name__)


class GCSBackend(CloudStorageBackend):
    """Google Cloud Storage backend with read caching.

    Features:
    - Read caching with configurable TTL (default 300s)
    - Atomic edits using generation matching
    - Error mapping to backend-agnostic exceptions
    - Efficient directory listing with delimiter
    - Pattern matching with glob and grep

    Example:
        >>> backend = GCSBackend(
        ...     bucket="my-workspace",
        ...     prefix="agent-123",
        ...     project_id="my-project"
        ... )
        >>> content = backend.read("config.yaml")
        >>> backend.write("output.txt", "results")
    """

    def __init__(
        self,
        bucket: str,
        prefix: str = "",
        project_id: str | None = None,
        cache_ttl: int = 300,
    ):
        """Initialize GCSBackend.

        Args:
            bucket: GCS bucket name
            prefix: Optional prefix for all paths (workspace isolation)
            project_id: Optional GCP project ID
            cache_ttl: Cache time-to-live in seconds (default 300)

        Raises:
            ImportError: If google-cloud-storage is not installed
        """
        if storage is None:
            raise ImportError(
                "google-cloud-storage required: pip install google-cloud-storage"
            )

        super().__init__(bucket, prefix, project_id)
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[str, float]] = {}
        self._client = storage.Client(project=project_id)
        self._bucket = self._client.bucket(bucket)

        logger.info(
            f"GCSBackend initialized: bucket={bucket}, prefix={prefix}, project={project_id}",
            extra={"component": "gcs_backend"},
        )

    def _invalidate_cache(self, path: str) -> None:
        """Invalidate cache entry for a path.

        Args:
            path: Path to invalidate in cache
        """
        normalized = self._normalize_path(path)
        if normalized in self._cache:
            del self._cache[normalized]
            logger.debug(
                f"Cache invalidated: {normalized}",
                extra={"component": "gcs_backend"},
            )

    def _get_from_cache(self, path: str) -> str | None:
        """Get content from cache if valid.

        Args:
            path: Path to retrieve from cache

        Returns:
            Cached content if valid, None otherwise
        """
        normalized = self._normalize_path(path)
        if normalized in self._cache:
            content, timestamp = self._cache[normalized]
            if time.time() - timestamp < self.cache_ttl:
                logger.debug(
                    f"Cache hit: {normalized}",
                    extra={"component": "gcs_backend"},
                )
                return content
            else:
                # Cache expired
                del self._cache[normalized]
                logger.debug(
                    f"Cache expired: {normalized}",
                    extra={"component": "gcs_backend"},
                )
        return None

    def _put_in_cache(self, path: str, content: str) -> None:
        """Put content in cache.

        Args:
            path: Path to cache
            content: Content to cache
        """
        normalized = self._normalize_path(path)
        self._cache[normalized] = (content, time.time())
        logger.debug(
            f"Cache updated: {normalized}",
            extra={"component": "gcs_backend"},
        )

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> str:
        """Read file contents with line-based offset and limit.

        Checks cache first, downloads from GCS on cache miss.

        Args:
            file_path: Path to the file to read
            offset: Line number to start reading from (0-indexed)
            limit: Maximum number of lines to read

        Returns:
            File contents as string

        Raises:
            FileNotFoundError: If file does not exist
            StorageUnavailableError: If GCS is unavailable
            PermissionError: If read access is denied
        """
        try:
            # Check cache first
            cached = self._get_from_cache(file_path)
            if cached is not None:
                content = cached
            else:
                # Download from GCS
                normalized = self._normalize_path(file_path)
                blob = self._bucket.blob(normalized)
                content = blob.download_as_text()

                # Cache the content
                self._put_in_cache(file_path, content)

                logger.debug(
                    f"Downloaded file: {normalized}",
                    extra={"component": "gcs_backend"},
                )

            # Apply line offset and limit
            if offset > 0 or limit < 2000:
                lines = content.split("\n")
                selected_lines = lines[offset : offset + limit]
                return "\n".join(selected_lines)

            return content

        except gcs_exceptions.NotFound as e:
            raise FileNotFoundError(file_path) from e
        except gcs_exceptions.Forbidden as e:
            raise PermissionError(file_path) from e
        except gcs_exceptions.ServiceUnavailable as e:
            raise StorageUnavailableError(f"GCS unavailable: {e}") from e

    def write(self, file_path: str, content: str) -> WriteResult:
        """Write (create or overwrite) a file.

        Invalidates cache after successful write.

        Args:
            file_path: Path to the file to write
            content: Content to write to the file

        Returns:
            WriteResult with operation status

        Raises:
            PermissionError: If write access is denied
            StorageUnavailableError: If GCS is unavailable
        """
        try:
            normalized = self._normalize_path(file_path)
            blob = self._bucket.blob(normalized)

            # Upload to GCS
            blob.upload_from_string(content, content_type="text/plain")

            # Invalidate cache
            self._invalidate_cache(file_path)

            logger.info(
                f"Wrote file: {normalized}",
                extra={"component": "gcs_backend"},
            )

            return cast(WriteResult, {"path": file_path, "error": None, "files_update": None})

        except gcs_exceptions.Forbidden as e:
            raise PermissionError(file_path) from e
        except gcs_exceptions.ServiceUnavailable as e:
            raise StorageUnavailableError(f"GCS unavailable: {e}") from e

    def edit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> EditResult:
        """Edit a file by replacing a string.

        Uses if_generation_match for atomic updates to prevent concurrent modifications.

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
            PermissionError: If write access is denied
            StorageUnavailableError: If GCS is unavailable
        """
        try:
            # Read current content and get generation
            normalized = self._normalize_path(file_path)
            blob = self._bucket.blob(normalized)
            content = blob.download_as_text()
            generation = blob.generation

            # Perform replacement
            if replace_all:
                if old_string not in content:
                    raise ValueError(f"String not found in {file_path}: {old_string}")
                new_content = content.replace(old_string, new_string)
            else:
                if old_string not in content:
                    raise ValueError(f"String not found in {file_path}: {old_string}")
                new_content = content.replace(old_string, new_string, 1)

            # Upload with generation match for atomicity
            blob.upload_from_string(
                new_content,
                content_type="text/plain",
                if_generation_match=generation,
            )

            # Invalidate cache
            self._invalidate_cache(file_path)

            logger.info(
                f"Edited file: {normalized}",
                extra={"component": "gcs_backend"},
            )

            # Count occurrences
            occurrences = 1 if not replace_all else content.count(old_string)

            return cast(
                EditResult,
                {
                    "path": file_path,
                    "error": None,
                    "files_update": None,
                    "occurrences": occurrences,
                },
            )

        except gcs_exceptions.NotFound as e:
            raise FileNotFoundError(file_path) from e
        except gcs_exceptions.PreconditionFailed as e:
            raise ConcurrencyError(file_path) from e
        except gcs_exceptions.Forbidden as e:
            raise PermissionError(file_path) from e
        except gcs_exceptions.ServiceUnavailable as e:
            raise StorageUnavailableError(f"GCS unavailable: {e}") from e

    def ls_info(self, path: str) -> list[FileInfo]:
        """List files and directories at the given path.

        Uses delimiter="/" for efficient directory listing.

        Args:
            path: Directory path to list

        Returns:
            List of FileInfo objects for files and subdirectories
        """
        try:
            normalized = self._normalize_path(path)

            # List blobs with delimiter to get directory structure
            iterator = self._client.list_blobs(
                self._bucket.name,
                prefix=normalized,
                delimiter="/",
            )

            results: list[FileInfo] = []

            # Add files
            for blob in iterator:
                # Extract name relative to prefix
                name = blob.name[len(normalized) :]
                if name:  # Skip empty names
                    results.append(
                        {
                            "path": blob.name,
                            "is_dir": False,
                            "size": blob.size or 0,
                            "modified_at": (
                                blob.updated.isoformat() if blob.updated else ""
                            ),
                        }
                    )

            # Add directories (prefixes)
            for prefix in iterator.prefixes:
                # Extract directory name relative to current path
                results.append(
                    {
                        "path": prefix,
                        "is_dir": True,
                        "size": 0,
                        "modified_at": "",
                    }
                )

            logger.debug(
                f"Listed {len(results)} items in: {normalized}",
                extra={"component": "gcs_backend"},
            )

            return results

        except gcs_exceptions.ServiceUnavailable as e:
            raise StorageUnavailableError(f"GCS unavailable: {e}") from e

    def glob_info(self, pattern: str, path: str = "/") -> list[FileInfo]:
        """Find files matching a glob pattern.

        Args:
            pattern: Glob pattern (e.g., "*.py", "test_*.txt")
            path: Base path to search within

        Returns:
            List of FileInfo objects for matching files
        """
        try:
            normalized = self._normalize_path(path)

            # List all blobs under path
            blobs = self._client.list_blobs(
                self._bucket.name,
                prefix=normalized,
            )

            results: list[FileInfo] = []

            for blob in blobs:
                # Extract name relative to prefix
                name = blob.name[len(normalized) :]

                # Match against pattern
                if fnmatch.fnmatch(name, pattern):
                    results.append(
                        {
                            "path": blob.name,
                            "is_dir": False,
                            "size": blob.size or 0,
                            "modified_at": (
                                blob.updated.isoformat() if blob.updated else ""
                            ),
                        }
                    )

            logger.debug(
                f"Glob matched {len(results)} files for pattern: {pattern}",
                extra={"component": "gcs_backend"},
            )

            return results

        except gcs_exceptions.ServiceUnavailable as e:
            raise StorageUnavailableError(f"GCS unavailable: {e}") from e

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
            List of GrepMatch objects with matching lines
        """
        try:
            # Determine search prefix
            normalized = self._normalize_path(path) if path else self.prefix

            # List blobs to search
            blobs = self._client.list_blobs(
                self._bucket.name,
                prefix=normalized,
            )

            # Filter by glob if provided
            if glob:
                blobs = [
                    blob
                    for blob in blobs
                    if fnmatch.fnmatch(blob.name[len(normalized) :], glob)
                ]

            # Compile regex pattern
            regex = re.compile(pattern)

            matches: list[GrepMatch] = []

            # Search each blob
            for blob in blobs:
                try:
                    content = blob.download_as_text()
                    lines = content.split("\n")

                    for line_num, line in enumerate(lines, start=1):
                        if regex.search(line):
                            matches.append(
                                {"path": blob.name, "line": line_num, "text": line}
                            )
                except Exception as e:
                    logger.warning(
                        f"Failed to search blob {blob.name}: {e}",
                        extra={"component": "gcs_backend"},
                    )
                    continue

            logger.debug(
                f"Grep found {len(matches)} matches for pattern: {pattern}",
                extra={"component": "gcs_backend"},
            )

            return matches

        except gcs_exceptions.ServiceUnavailable as e:
            raise StorageUnavailableError(f"GCS unavailable: {e}") from e

    def upload_files(self, files: list[dict[str, str]]) -> list[FileUploadResponse]:
        """Upload multiple files.

        Args:
            files: List of file dicts with 'path' and 'content' keys

        Returns:
            List of FileUploadResponse objects
        """
        responses: list[FileUploadResponse] = []

        for file_dict in files:
            try:
                path = file_dict["path"]
                content = file_dict["content"]

                self.write(path, content)
                responses.append({"path": path, "error": None})
            except Exception as e:
                logger.error(
                    f"Failed to upload file {file_dict.get('path', 'unknown')}: {e}",
                    extra={"component": "gcs_backend"},
                )
                responses.append(
                    {"path": file_dict.get("path", "unknown"), "error": str(e)}
                )

        return responses

    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        """Download multiple files.

        Args:
            paths: List of file paths to download

        Returns:
            List of FileDownloadResponse objects with file contents
        """
        responses: list[FileDownloadResponse] = []

        for path in paths:
            try:
                content = self.read(path)
                responses.append({"path": path, "content": content, "error": None})
            except Exception as e:
                logger.error(
                    f"Failed to download file {path}: {e}",
                    extra={"component": "gcs_backend"},
                )
                responses.append({"path": path, "content": "", "error": str(e)})

        return responses
