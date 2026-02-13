"""Cloud storage backends for deep agents integration.

This package provides abstract and concrete implementations of cloud storage
backends that implement the deep agents BackendProtocol.

Available backends:
- GCSBackend: Google Cloud Storage implementation with caching

Example:
    >>> from src.backends import GCSBackend
    >>> backend = GCSBackend(bucket="my-workspace", prefix="agent-123")
    >>> content = backend.read("config.yaml")
"""

from src.backends.base import (
    CloudStorageBackend,
    CloudStorageError,
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
from src.backends.gcs import GCSBackend

__all__ = [
    # Base classes
    "CloudStorageBackend",
    # Concrete implementations
    "GCSBackend",
    # Error classes
    "CloudStorageError",
    "FileNotFoundError",
    "StorageUnavailableError",
    "ConcurrencyError",
    "PermissionError",
    # Data classes
    "FileInfo",
    "WriteResult",
    "EditResult",
    "GrepMatch",
    "FileUploadResponse",
    "FileDownloadResponse",
]
