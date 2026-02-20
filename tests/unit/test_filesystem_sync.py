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


def _mock_proc(returncode: int = 0, stdout: bytes = b"", stderr: bytes = b""):
    proc = AsyncMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    return proc


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
        with patch("asyncio.create_subprocess_exec", return_value=_mock_proc(0)):
            await s.sync_from_gcs()
        assert local_dir.exists()

    @pytest.mark.asyncio
    async def test_calls_gsutil_rsync_with_gcs_as_source(self, sync):
        with patch("asyncio.create_subprocess_exec", return_value=_mock_proc(0)) as mock_exec:
            await sync.sync_from_gcs()
        args = mock_exec.call_args[0]
        assert args[0] == "gsutil"
        assert "-m" in args
        assert "rsync" in args
        assert "-r" in args
        assert "gs://test-bucket/memory/" in args

    @pytest.mark.asyncio
    async def test_gcs_is_source_not_destination(self, sync):
        """GCS URI must appear before local_dir in rsync for pull."""
        with patch("asyncio.create_subprocess_exec", return_value=_mock_proc(0)) as mock_exec:
            await sync.sync_from_gcs()
        args = list(mock_exec.call_args[0])
        gcs_idx = next(i for i, a in enumerate(args) if a.startswith("gs://"))
        local_idx = next(i for i, a in enumerate(args) if str(sync.local_dir) in a)
        assert gcs_idx < local_idx

    @pytest.mark.asyncio
    async def test_non_fatal_on_nonzero_exit(self, sync):
        with patch("asyncio.create_subprocess_exec", return_value=_mock_proc(1, stderr=b"err")):
            await sync.sync_from_gcs()  # must not raise

    @pytest.mark.asyncio
    async def test_non_fatal_when_gsutil_not_found(self, sync):
        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError):
            await sync.sync_from_gcs()  # must not raise


class TestSyncToGCS:
    @pytest.mark.asyncio
    async def test_calls_gsutil_rsync_with_gcs_as_destination(self, sync):
        with patch("asyncio.create_subprocess_exec", return_value=_mock_proc(0)) as mock_exec:
            await sync.sync_to_gcs()
        args = list(mock_exec.call_args[0])
        gcs_idx = next(i for i, a in enumerate(args) if a.startswith("gs://"))
        local_idx = next(i for i, a in enumerate(args) if str(sync.local_dir) in a)
        assert local_idx < gcs_idx

    @pytest.mark.asyncio
    async def test_non_fatal_on_nonzero_exit(self, sync):
        with patch("asyncio.create_subprocess_exec", return_value=_mock_proc(1, stderr=b"err")):
            await sync.sync_to_gcs()  # must not raise

    @pytest.mark.asyncio
    async def test_non_fatal_when_gsutil_not_found(self, sync):
        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError):
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
