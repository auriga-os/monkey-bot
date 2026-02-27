"""Unit tests for GCSFilesystemSync."""

import asyncio
import signal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.filesystem_sync import GCSFilesystemSync


@pytest.fixture
def sync(tmp_path):
    """GCSFilesystemSync with tmp_path as local_dir."""
    return GCSFilesystemSync(
        bucket_name="test-bucket",
        local_dir=tmp_path / "memory",
        gcs_prefix="memory/",
        sync_interval=1,
    )


class TestGcsUri:
    def test_gcs_uri_includes_trailing_slash_on_prefix(self, tmp_path):
        s = GCSFilesystemSync("my-bucket", tmp_path, gcs_prefix="mem")
        assert s._gcs_uri == "gs://my-bucket/mem/"

    def test_gcs_uri_does_not_double_slash(self, tmp_path):
        s = GCSFilesystemSync("my-bucket", tmp_path, gcs_prefix="mem/")
        assert s._gcs_uri == "gs://my-bucket/mem/"


class TestSyncFromGCS:
    @pytest.mark.asyncio
    async def test_creates_local_dir_if_missing(self, tmp_path):
        local_dir = tmp_path / "nonexistent" / "memory"
        s = GCSFilesystemSync("bucket", local_dir=local_dir)
        mock_client = MagicMock()
        mock_client.list_blobs.return_value = []
        with patch.object(s, "_get_client", return_value=mock_client):
            await s.sync_from_gcs()
        assert local_dir.exists()

    @pytest.mark.asyncio
    async def test_calls_gsutil_rsync_with_gcs_as_source(self, sync):
        """sync_from_gcs pulls from GCS bucket with correct prefix."""
        mock_client = MagicMock()
        mock_client.list_blobs.return_value = []
        with patch.object(sync, "_get_client", return_value=mock_client):
            await sync.sync_from_gcs()
        mock_client.list_blobs.assert_called_once_with("test-bucket", prefix="memory/")

    @pytest.mark.asyncio
    async def test_gcs_is_source_not_destination(self, sync):
        """Pull downloads FROM GCS (list_blobs + download_to_filename), not upload."""
        mock_client = MagicMock()
        mock_blob = MagicMock()
        mock_blob.name = "memory/file.txt"
        mock_client.list_blobs.return_value = [mock_blob]
        sync.local_dir.mkdir(parents=True, exist_ok=True)
        with patch.object(sync, "_get_client", return_value=mock_client):
            await sync.sync_from_gcs()
        mock_blob.download_to_filename.assert_called_once()
        mock_client.bucket.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_fatal_on_nonzero_exit(self, sync):
        with patch.object(sync, "_get_client", side_effect=Exception("GCS error")):
            await sync.sync_from_gcs()  # must not raise

    @pytest.mark.asyncio
    async def test_non_fatal_when_gsutil_not_found(self, sync):
        with patch.object(sync, "_get_client", side_effect=FileNotFoundError):
            await sync.sync_from_gcs()  # must not raise


class TestSyncToGCS:
    @pytest.mark.asyncio
    async def test_calls_gsutil_rsync_with_gcs_as_destination(self, sync):
        """sync_to_gcs uploads local files TO GCS bucket."""
        sync.local_dir.mkdir(parents=True, exist_ok=True)
        (sync.local_dir / "test.txt").write_text("hello")

        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_client.bucket.return_value = mock_bucket
        with patch.object(sync, "_get_client", return_value=mock_client):
            await sync.sync_to_gcs()
        mock_client.bucket.assert_called_once_with("test-bucket")
        mock_blob.upload_from_filename.assert_called_once()

    @pytest.mark.asyncio
    async def test_non_fatal_on_nonzero_exit(self, sync):
        with patch.object(sync, "_get_client", side_effect=Exception("GCS error")):
            await sync.sync_to_gcs()  # must not raise

    @pytest.mark.asyncio
    async def test_non_fatal_when_gsutil_not_found(self, sync):
        with patch.object(sync, "_get_client", side_effect=FileNotFoundError):
            await sync.sync_to_gcs()  # must not raise


class TestPeriodicSync:
    @pytest.mark.asyncio
    async def test_start_returns_asyncio_task(self, sync):
        with patch.object(sync, "sync_to_gcs", new_callable=AsyncMock):
            task = await sync.start_periodic_sync()
            assert isinstance(task, asyncio.Task)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_periodic_task_stored_on_instance(self, sync):
        with patch.object(sync, "sync_to_gcs", new_callable=AsyncMock):
            task = await sync.start_periodic_sync()
            assert sync._sync_task is task
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


class TestClose:
    @pytest.mark.asyncio
    async def test_close_cancels_periodic_task(self, sync):
        cancelled = False

        async def _noop():
            nonlocal cancelled
            try:
                await asyncio.sleep(9999)
            except asyncio.CancelledError:
                cancelled = True
                raise

        sync._sync_task = asyncio.create_task(_noop())
        # Yield to let the task start (enter the sleep) before cancelling
        await asyncio.sleep(0)
        with patch.object(sync, "sync_to_gcs", new_callable=AsyncMock):
            await sync.close()
        assert cancelled

    @pytest.mark.asyncio
    async def test_close_calls_final_sync(self, sync):
        with patch.object(sync, "sync_to_gcs", new_callable=AsyncMock) as mock_sync:
            await sync.close()
        mock_sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_safe_when_no_task(self, sync):
        assert sync._sync_task is None
        with patch.object(sync, "sync_to_gcs", new_callable=AsyncMock):
            await sync.close()  # must not raise


class TestSIGTERM:
    def test_register_sigterm_handler_sets_signal(self, sync):
        original = signal.getsignal(signal.SIGTERM)
        try:
            sync.register_sigterm_handler()
            handler = signal.getsignal(signal.SIGTERM)
            assert handler is not None
            assert callable(handler)
        finally:
            signal.signal(signal.SIGTERM, original)
