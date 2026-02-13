"""Unit tests for GCSBackend.

Tests all GCSBackend methods with mocked google.cloud.storage.Client:
- read() with caching
- write() with cache invalidation
- edit() with atomic updates
- ls_info() with directory listing
- glob_info() with pattern matching
- grep_raw() with regex search
- upload_files() and download_files()
- Error mapping (NotFound, Forbidden, PreconditionFailed, ServiceUnavailable)
"""

from unittest.mock import Mock, patch

import pytest

from src.backends.base import (
    ConcurrencyError,
    FileNotFoundError,
    PermissionError,
    StorageUnavailableError,
)

# ============================================================================
# Test Initialization
# ============================================================================


@patch("src.backends.gcs.storage")
def test_gcs_backend_init(mock_storage):
    """Test GCSBackend initialization."""
    from src.backends.gcs import GCSBackend

    mock_client = Mock()
    mock_bucket = Mock()
    mock_client.bucket.return_value = mock_bucket
    mock_storage.Client.return_value = mock_client

    backend = GCSBackend(bucket="test-bucket", prefix="workspace", project_id="test-project")

    assert backend.bucket_name == "test-bucket"
    assert backend.prefix == "workspace/"
    assert backend.project_id == "test-project"
    assert backend.cache_ttl == 300
    mock_storage.Client.assert_called_once_with(project="test-project")
    mock_client.bucket.assert_called_once_with("test-bucket")


@patch("src.backends.gcs.storage")
def test_gcs_backend_init_custom_cache_ttl(mock_storage):
    """Test GCSBackend initialization with custom cache TTL."""
    from src.backends.gcs import GCSBackend

    mock_client = Mock()
    mock_bucket = Mock()
    mock_client.bucket.return_value = mock_bucket
    mock_storage.Client.return_value = mock_client

    backend = GCSBackend(bucket="test-bucket", cache_ttl=600)

    assert backend.cache_ttl == 600


def test_gcs_backend_import_error(monkeypatch):
    """Test that ImportError is raised when google-cloud-storage is not available."""
    import src.backends.gcs
    
    # Mock the storage module to be None (simulating ImportError)
    monkeypatch.setattr('src.backends.gcs.storage', None)
    
    # Try to create GCSBackend - should raise ImportError
    with pytest.raises(ImportError, match="google-cloud-storage required"):
        src.backends.gcs.GCSBackend(bucket="test-bucket")


# ============================================================================
# Test read() with caching
# ============================================================================


@patch("src.backends.gcs.storage")
def test_read_file_cache_miss(mock_storage):
    """Test reading a file when cache is empty."""
    from src.backends.gcs import GCSBackend

    mock_client = Mock()
    mock_bucket = Mock()
    mock_blob = Mock()

    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    mock_blob.download_as_text.return_value = "line1\nline2\nline3\nline4\nline5"
    mock_storage.Client.return_value = mock_client

    backend = GCSBackend(bucket="test-bucket")
    result = backend.read("test.txt")

    assert result == "line1\nline2\nline3\nline4\nline5"
    mock_blob.download_as_text.assert_called_once()


@patch("src.backends.gcs.storage")
@patch("src.backends.gcs.time.time")
def test_read_file_cache_hit(mock_time, mock_storage):
    """Test reading a file when cache is valid."""
    from src.backends.gcs import GCSBackend

    mock_client = Mock()
    mock_bucket = Mock()
    mock_blob = Mock()

    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    mock_blob.download_as_text.return_value = "cached content"
    mock_storage.Client.return_value = mock_client

    # Mock time to control cache expiry
    mock_time.return_value = 1000.0

    backend = GCSBackend(bucket="test-bucket", cache_ttl=300)

    # First read - cache miss
    result1 = backend.read("test.txt")
    assert result1 == "cached content"
    assert mock_blob.download_as_text.call_count == 1

    # Second read - cache hit (time hasn't advanced)
    result2 = backend.read("test.txt")
    assert result2 == "cached content"
    assert mock_blob.download_as_text.call_count == 1  # Still only called once


@patch("src.backends.gcs.storage")
@patch("src.backends.gcs.time.time")
def test_read_file_cache_expired(mock_time, mock_storage):
    """Test reading a file when cache has expired."""
    from src.backends.gcs import GCSBackend

    mock_client = Mock()
    mock_bucket = Mock()
    mock_blob = Mock()

    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    mock_blob.download_as_text.side_effect = ["old content", "new content"]
    mock_storage.Client.return_value = mock_client

    backend = GCSBackend(bucket="test-bucket", cache_ttl=300)

    # First read at time 1000
    mock_time.return_value = 1000.0
    result1 = backend.read("test.txt")
    assert result1 == "old content"

    # Second read at time 1400 (cache expired)
    mock_time.return_value = 1400.0
    result2 = backend.read("test.txt")
    assert result2 == "new content"
    assert mock_blob.download_as_text.call_count == 2


@patch("src.backends.gcs.storage")
def test_read_file_with_offset_and_limit(mock_storage):
    """Test reading a file with line offset and limit."""
    from src.backends.gcs import GCSBackend

    mock_client = Mock()
    mock_bucket = Mock()
    mock_blob = Mock()

    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    mock_blob.download_as_text.return_value = "line1\nline2\nline3\nline4\nline5"
    mock_storage.Client.return_value = mock_client

    backend = GCSBackend(bucket="test-bucket")

    # Read lines 2-3 (offset=1, limit=2)
    result = backend.read("test.txt", offset=1, limit=2)
    assert result == "line2\nline3"


@patch("src.backends.gcs.storage")
def test_read_file_not_found(mock_storage):
    """Test reading a non-existent file raises FileNotFoundError."""
    from google.api_core import exceptions as gcs_exceptions

    from src.backends.gcs import GCSBackend

    mock_client = Mock()
    mock_bucket = Mock()
    mock_blob = Mock()

    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    mock_blob.download_as_text.side_effect = gcs_exceptions.NotFound("File not found")
    mock_storage.Client.return_value = mock_client

    backend = GCSBackend(bucket="test-bucket")

    with pytest.raises(FileNotFoundError, match="test.txt"):
        backend.read("test.txt")


# ============================================================================
# Test write() with cache invalidation
# ============================================================================


@patch("src.backends.gcs.storage")
def test_write_file(mock_storage):
    """Test writing a file."""
    from src.backends.gcs import GCSBackend

    mock_client = Mock()
    mock_bucket = Mock()
    mock_blob = Mock()

    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    mock_storage.Client.return_value = mock_client

    backend = GCSBackend(bucket="test-bucket")
    result = backend.write("test.txt", "new content")

    assert isinstance(result, dict)
    assert result["path"] == "test.txt"
    assert result["error"] is None
    mock_blob.upload_from_string.assert_called_once_with("new content", content_type="text/plain")


@patch("src.backends.gcs.storage")
@patch("src.backends.gcs.time.time")
def test_write_invalidates_cache(mock_time, mock_storage):
    """Test that writing a file invalidates the cache."""
    from src.backends.gcs import GCSBackend

    mock_client = Mock()
    mock_bucket = Mock()
    mock_blob = Mock()

    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    mock_blob.download_as_text.side_effect = ["old content", "new content"]
    mock_storage.Client.return_value = mock_client

    mock_time.return_value = 1000.0

    backend = GCSBackend(bucket="test-bucket")

    # Read to populate cache
    result1 = backend.read("test.txt")
    assert result1 == "old content"

    # Write to invalidate cache
    backend.write("test.txt", "new content")

    # Read again - should fetch from GCS, not cache
    result2 = backend.read("test.txt")
    assert result2 == "new content"
    assert mock_blob.download_as_text.call_count == 2


@patch("src.backends.gcs.storage")
def test_write_permission_denied(mock_storage):
    """Test writing a file with permission denied raises PermissionError."""
    from google.api_core import exceptions as gcs_exceptions

    from src.backends.gcs import GCSBackend

    mock_client = Mock()
    mock_bucket = Mock()
    mock_blob = Mock()

    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    mock_blob.upload_from_string.side_effect = gcs_exceptions.Forbidden("Permission denied")
    mock_storage.Client.return_value = mock_client

    backend = GCSBackend(bucket="test-bucket")

    with pytest.raises(PermissionError, match="test.txt"):
        backend.write("test.txt", "content")


# ============================================================================
# Test edit() with atomic updates
# ============================================================================


@patch("src.backends.gcs.storage")
def test_edit_file_single_replace(mock_storage):
    """Test editing a file with single string replacement."""
    from src.backends.gcs import GCSBackend

    mock_client = Mock()
    mock_bucket = Mock()
    mock_blob = Mock()

    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    mock_blob.download_as_text.return_value = "Hello world\nHello universe"
    mock_blob.generation = 123
    mock_storage.Client.return_value = mock_client

    backend = GCSBackend(bucket="test-bucket")
    result = backend.edit("test.txt", "Hello world", "Goodbye world")

    assert isinstance(result, dict)
    assert result["path"] == "test.txt"
    assert result["error"] is None
    assert result["occurrences"] == 1
    mock_blob.upload_from_string.assert_called_once_with(
        "Goodbye world\nHello universe",
        content_type="text/plain",
        if_generation_match=123,
    )


@patch("src.backends.gcs.storage")
def test_edit_file_replace_all(mock_storage):
    """Test editing a file with replace_all=True."""
    from src.backends.gcs import GCSBackend

    mock_client = Mock()
    mock_bucket = Mock()
    mock_blob = Mock()

    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    mock_blob.download_as_text.return_value = "Hello world\nHello universe\nHello galaxy"
    mock_blob.generation = 456
    mock_storage.Client.return_value = mock_client

    backend = GCSBackend(bucket="test-bucket")
    result = backend.edit("test.txt", "Hello", "Goodbye", replace_all=True)

    assert result["path"] == "test.txt"
    assert result["occurrences"] == 3
    mock_blob.upload_from_string.assert_called_once_with(
        "Goodbye world\nGoodbye universe\nGoodbye galaxy",
        content_type="text/plain",
        if_generation_match=456,
    )


@patch("src.backends.gcs.storage")
def test_edit_file_string_not_found(mock_storage):
    """Test editing a file when old_string is not found."""
    from src.backends.gcs import GCSBackend

    mock_client = Mock()
    mock_bucket = Mock()
    mock_blob = Mock()

    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    mock_blob.download_as_text.return_value = "Hello world"
    mock_storage.Client.return_value = mock_client

    backend = GCSBackend(bucket="test-bucket")

    with pytest.raises(ValueError, match="String not found"):
        backend.edit("test.txt", "Goodbye", "Hello")


@patch("src.backends.gcs.storage")
def test_edit_file_concurrency_error(mock_storage):
    """Test editing a file with concurrent modification raises ConcurrencyError."""
    from google.api_core import exceptions as gcs_exceptions

    from src.backends.gcs import GCSBackend

    mock_client = Mock()
    mock_bucket = Mock()
    mock_blob = Mock()

    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    mock_blob.download_as_text.return_value = "Hello world"
    mock_blob.generation = 123
    mock_blob.upload_from_string.side_effect = gcs_exceptions.PreconditionFailed(
        "Precondition failed"
    )
    mock_storage.Client.return_value = mock_client

    backend = GCSBackend(bucket="test-bucket")

    with pytest.raises(ConcurrencyError, match="test.txt"):
        backend.edit("test.txt", "Hello", "Goodbye")


# ============================================================================
# Test ls_info() with directory listing
# ============================================================================


@patch("src.backends.gcs.storage")
def test_ls_info_directory(mock_storage):
    """Test listing files in a directory."""
    from src.backends.gcs import GCSBackend

    mock_client = Mock()
    mock_bucket = Mock()

    # Mock blobs and prefixes
    mock_blob1 = Mock()
    mock_blob1.name = "workspace/file1.txt"
    mock_blob1.size = 100
    mock_blob1.updated = Mock()
    mock_blob1.updated.isoformat.return_value = "2024-01-01T00:00:00Z"

    mock_blob2 = Mock()
    mock_blob2.name = "workspace/file2.txt"
    mock_blob2.size = 200
    mock_blob2.updated = Mock()
    mock_blob2.updated.isoformat.return_value = "2024-01-02T00:00:00Z"

    mock_client.bucket.return_value = mock_bucket
    mock_client.list_blobs.return_value = Mock(
        __iter__=lambda self: iter([mock_blob1, mock_blob2]),
        prefixes=["workspace/subdir/"],
    )
    mock_storage.Client.return_value = mock_client

    backend = GCSBackend(bucket="test-bucket", prefix="workspace")
    result = backend.ls_info("")

    assert len(result) == 3  # 2 files + 1 directory
    assert any(f["path"] == "workspace/file1.txt" and not f["is_dir"] for f in result)
    assert any(f["path"] == "workspace/file2.txt" and not f["is_dir"] for f in result)
    assert any(f["path"] == "workspace/subdir/" and f["is_dir"] for f in result)


@patch("src.backends.gcs.storage")
def test_ls_info_empty_directory(mock_storage):
    """Test listing an empty directory."""
    from src.backends.gcs import GCSBackend

    mock_client = Mock()
    mock_bucket = Mock()

    mock_client.bucket.return_value = mock_bucket
    mock_client.list_blobs.return_value = Mock(
        __iter__=lambda self: iter([]),
        prefixes=[],
    )
    mock_storage.Client.return_value = mock_client

    backend = GCSBackend(bucket="test-bucket")
    result = backend.ls_info("empty/")

    assert result == []


# ============================================================================
# Test glob_info() with pattern matching
# ============================================================================


@patch("src.backends.gcs.storage")
def test_glob_info_pattern_match(mock_storage):
    """Test finding files matching a glob pattern."""
    from src.backends.gcs import GCSBackend

    mock_client = Mock()
    mock_bucket = Mock()

    mock_blob1 = Mock()
    mock_blob1.name = "test.py"
    mock_blob1.size = 100
    mock_blob1.updated = Mock()
    mock_blob1.updated.isoformat.return_value = "2024-01-01T00:00:00Z"

    mock_blob2 = Mock()
    mock_blob2.name = "test.txt"
    mock_blob2.size = 200
    mock_blob2.updated = Mock()
    mock_blob2.updated.isoformat.return_value = "2024-01-02T00:00:00Z"

    mock_blob3 = Mock()
    mock_blob3.name = "main.py"
    mock_blob3.size = 300
    mock_blob3.updated = Mock()
    mock_blob3.updated.isoformat.return_value = "2024-01-03T00:00:00Z"

    mock_client.bucket.return_value = mock_bucket
    mock_client.list_blobs.return_value = [mock_blob1, mock_blob2, mock_blob3]
    mock_storage.Client.return_value = mock_client

    backend = GCSBackend(bucket="test-bucket")
    result = backend.glob_info("*.py")

    assert len(result) == 2
    assert any(f["path"] == "test.py" for f in result)
    assert any(f["path"] == "main.py" for f in result)


@patch("src.backends.gcs.storage")
def test_glob_info_no_matches(mock_storage):
    """Test glob pattern with no matches."""
    from src.backends.gcs import GCSBackend

    mock_client = Mock()
    mock_bucket = Mock()

    mock_blob = Mock()
    mock_blob.name = "test.txt"

    mock_client.bucket.return_value = mock_bucket
    mock_client.list_blobs.return_value = [mock_blob]
    mock_storage.Client.return_value = mock_client

    backend = GCSBackend(bucket="test-bucket")
    result = backend.glob_info("*.py")

    assert result == []


# ============================================================================
# Test grep_raw() with regex search
# ============================================================================


@patch("src.backends.gcs.storage")
def test_grep_raw_pattern_match(mock_storage):
    """Test searching file contents with regex pattern."""
    from src.backends.gcs import GCSBackend

    mock_client = Mock()
    mock_bucket = Mock()

    mock_blob1 = Mock()
    mock_blob1.name = "file1.txt"
    mock_blob1.download_as_text.return_value = "Hello world\nGoodbye world"

    mock_blob2 = Mock()
    mock_blob2.name = "file2.txt"
    mock_blob2.download_as_text.return_value = "No match here"

    mock_client.bucket.return_value = mock_bucket
    mock_client.list_blobs.return_value = [mock_blob1, mock_blob2]
    mock_storage.Client.return_value = mock_client

    backend = GCSBackend(bucket="test-bucket")
    result = backend.grep_raw(r"world")

    assert len(result) == 2
    assert any(m["path"] == "file1.txt" and m["line"] == 1 and "Hello world" in m["text"] for m in result)
    assert any(m["path"] == "file1.txt" and m["line"] == 2 and "Goodbye world" in m["text"] for m in result)


@patch("src.backends.gcs.storage")
def test_grep_raw_with_glob_filter(mock_storage):
    """Test searching with glob filter."""
    from src.backends.gcs import GCSBackend

    mock_client = Mock()
    mock_bucket = Mock()

    mock_blob1 = Mock()
    mock_blob1.name = "test.py"
    mock_blob1.download_as_text.return_value = "def hello():\n    pass"

    mock_blob2 = Mock()
    mock_blob2.name = "test.txt"
    mock_blob2.download_as_text.return_value = "def hello():\n    pass"

    mock_client.bucket.return_value = mock_bucket
    mock_client.list_blobs.return_value = [mock_blob1, mock_blob2]
    mock_storage.Client.return_value = mock_client

    backend = GCSBackend(bucket="test-bucket")
    result = backend.grep_raw(r"def", glob="*.py")

    assert len(result) == 1
    assert result[0]["path"] == "test.py"


@patch("src.backends.gcs.storage")
def test_grep_raw_no_matches(mock_storage):
    """Test grep with no matches."""
    from src.backends.gcs import GCSBackend

    mock_client = Mock()
    mock_bucket = Mock()

    mock_blob = Mock()
    mock_blob.name = "file.txt"
    mock_blob.download_as_text.return_value = "Hello world"

    mock_client.bucket.return_value = mock_bucket
    mock_client.list_blobs.return_value = [mock_blob]
    mock_storage.Client.return_value = mock_client

    backend = GCSBackend(bucket="test-bucket")
    result = backend.grep_raw(r"nomatch")

    assert result == []


# ============================================================================
# Test upload_files() and download_files()
# ============================================================================


@patch("src.backends.gcs.storage")
def test_upload_files(mock_storage):
    """Test uploading multiple files."""
    from src.backends.gcs import GCSBackend

    mock_client = Mock()
    mock_bucket = Mock()
    mock_blob = Mock()

    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    mock_storage.Client.return_value = mock_client

    backend = GCSBackend(bucket="test-bucket")

    files = [
        {"path": "file1.txt", "content": "content1"},
        {"path": "file2.txt", "content": "content2"},
    ]

    result = backend.upload_files(files)

    assert len(result) == 2
    assert all(isinstance(r, dict) for r in result)
    assert all(r["error"] is None for r in result)
    assert mock_blob.upload_from_string.call_count == 2


@patch("src.backends.gcs.storage")
def test_download_files(mock_storage):
    """Test downloading multiple files."""
    from src.backends.gcs import GCSBackend

    mock_client = Mock()
    mock_bucket = Mock()
    mock_blob = Mock()

    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    mock_blob.download_as_text.side_effect = ["content1", "content2"]
    mock_storage.Client.return_value = mock_client

    backend = GCSBackend(bucket="test-bucket")

    result = backend.download_files(["file1.txt", "file2.txt"])

    assert len(result) == 2
    assert all(isinstance(r, dict) for r in result)
    assert result[0]["content"] == "content1"
    assert result[1]["content"] == "content2"


# ============================================================================
# Test Error Mapping
# ============================================================================


@patch("src.backends.gcs.storage")
def test_error_mapping_service_unavailable(mock_storage):
    """Test that ServiceUnavailable is mapped to StorageUnavailableError."""
    from google.api_core import exceptions as gcs_exceptions

    from src.backends.gcs import GCSBackend

    mock_client = Mock()
    mock_bucket = Mock()
    mock_blob = Mock()

    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    mock_blob.download_as_text.side_effect = gcs_exceptions.ServiceUnavailable("Service down")
    mock_storage.Client.return_value = mock_client

    backend = GCSBackend(bucket="test-bucket")

    with pytest.raises(StorageUnavailableError):
        backend.read("test.txt")
