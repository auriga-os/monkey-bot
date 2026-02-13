"""Unit tests for CloudStorageBackend base class.

Tests:
- Path normalization (_normalize_path)
- Directory detection (_is_directory)
- Abstract class cannot be instantiated
- Error classes
"""

import pytest

from src.backends.base import (
    CloudStorageBackend,
    CloudStorageError,
    ConcurrencyError,
    FileNotFoundError,
    PermissionError,
    StorageUnavailableError,
)

# ============================================================================
# Test Abstract Class
# ============================================================================


def test_cannot_instantiate_abstract_class():
    """Test that CloudStorageBackend cannot be instantiated directly."""
    with pytest.raises(TypeError):
        CloudStorageBackend(bucket="test-bucket")  # type: ignore


# ============================================================================
# Test Concrete Implementation for Helper Methods
# ============================================================================


class ConcreteBackend(CloudStorageBackend):
    """Concrete implementation for testing helper methods."""

    def ls_info(self, path: str):
        return []

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> str:
        return ""

    def write(self, file_path: str, content: str):
        from src.backends.base import WriteResult
        return WriteResult(path=file_path)

    def edit(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False):
        from src.backends.base import EditResult
        return EditResult(path=file_path)

    def glob_info(self, pattern: str, path: str = "/"):
        return []

    def grep_raw(self, pattern: str, path: str | None = None, glob: str | None = None):
        return []

    def upload_files(self, files: list):
        return []

    def download_files(self, paths: list[str]):
        return []


# ============================================================================
# Test Path Normalization
# ============================================================================


def test_normalize_path_strips_leading_slash():
    """Test that leading slashes are stripped."""
    backend = ConcreteBackend(bucket="test-bucket")
    assert backend._normalize_path("/path/to/file.txt") == "path/to/file.txt"


def test_normalize_path_applies_prefix():
    """Test that prefix is applied to paths."""
    backend = ConcreteBackend(bucket="test-bucket", prefix="workspace")
    assert backend._normalize_path("file.txt") == "workspace/file.txt"


def test_normalize_path_with_trailing_slash_prefix():
    """Test that prefix with trailing slash works correctly."""
    backend = ConcreteBackend(bucket="test-bucket", prefix="workspace/")
    assert backend._normalize_path("file.txt") == "workspace/file.txt"


def test_normalize_path_already_has_prefix():
    """Test that paths already containing prefix are not duplicated."""
    backend = ConcreteBackend(bucket="test-bucket", prefix="workspace")
    assert backend._normalize_path("workspace/file.txt") == "workspace/file.txt"


def test_normalize_path_rejects_traversal():
    """Test that path traversal attempts are rejected."""
    backend = ConcreteBackend(bucket="test-bucket")
    with pytest.raises(ValueError, match="Path traversal not allowed"):
        backend._normalize_path("../etc/passwd")


def test_normalize_path_rejects_traversal_with_prefix():
    """Test that path traversal is rejected even with prefix."""
    backend = ConcreteBackend(bucket="test-bucket", prefix="workspace")
    with pytest.raises(ValueError, match="Path traversal not allowed"):
        backend._normalize_path("workspace/../etc/passwd")


def test_normalize_path_empty_string():
    """Test that empty string is handled correctly."""
    backend = ConcreteBackend(bucket="test-bucket")
    assert backend._normalize_path("") == ""


def test_normalize_path_empty_string_with_prefix():
    """Test that empty string with prefix returns just prefix."""
    backend = ConcreteBackend(bucket="test-bucket", prefix="workspace")
    assert backend._normalize_path("") == "workspace/"


# ============================================================================
# Test Directory Detection
# ============================================================================


def test_is_directory_empty_string():
    """Test that empty string is considered a directory."""
    backend = ConcreteBackend(bucket="test-bucket")
    assert backend._is_directory("")


def test_is_directory_trailing_slash():
    """Test that paths ending with / are directories."""
    backend = ConcreteBackend(bucket="test-bucket")
    assert backend._is_directory("path/to/dir/")


def test_is_directory_file_path():
    """Test that file paths are not directories."""
    backend = ConcreteBackend(bucket="test-bucket")
    assert not backend._is_directory("path/to/file.txt")


def test_is_directory_no_extension():
    """Test that paths without extensions but no trailing slash are not directories."""
    backend = ConcreteBackend(bucket="test-bucket")
    assert not backend._is_directory("path/to/something")


# ============================================================================
# Test Error Classes
# ============================================================================


def test_file_not_found_error():
    """Test FileNotFoundError includes path."""
    error = FileNotFoundError("path/to/file.txt")
    assert error.path == "path/to/file.txt"
    assert "path/to/file.txt" in str(error)


def test_concurrency_error():
    """Test ConcurrencyError includes path."""
    error = ConcurrencyError("path/to/file.txt")
    assert error.path == "path/to/file.txt"
    assert "path/to/file.txt" in str(error)


def test_permission_error():
    """Test PermissionError includes path."""
    error = PermissionError("path/to/file.txt")
    assert error.path == "path/to/file.txt"
    assert "path/to/file.txt" in str(error)


def test_storage_unavailable_error():
    """Test StorageUnavailableError can be raised."""
    error = StorageUnavailableError("Service unavailable")
    assert isinstance(error, CloudStorageError)


def test_cloud_storage_error_base():
    """Test CloudStorageError is base for all errors."""
    assert issubclass(FileNotFoundError, CloudStorageError)
    assert issubclass(StorageUnavailableError, CloudStorageError)
    assert issubclass(ConcurrencyError, CloudStorageError)
    assert issubclass(PermissionError, CloudStorageError)


# ============================================================================
# Test Initialization
# ============================================================================


def test_init_with_bucket_only():
    """Test initialization with just bucket name."""
    backend = ConcreteBackend(bucket="test-bucket")
    assert backend.bucket_name == "test-bucket"
    assert backend.prefix == ""
    assert backend.project_id is None


def test_init_with_prefix():
    """Test initialization with prefix."""
    backend = ConcreteBackend(bucket="test-bucket", prefix="workspace")
    assert backend.bucket_name == "test-bucket"
    assert backend.prefix == "workspace/"


def test_init_with_project_id():
    """Test initialization with project ID."""
    backend = ConcreteBackend(bucket="test-bucket", project_id="my-project")
    assert backend.project_id == "my-project"
