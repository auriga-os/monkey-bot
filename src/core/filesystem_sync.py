"""GCS-backed filesystem sync for agent persistent memory.

Uses the google-cloud-storage Python library directly — no gsutil required.

Strategy: startup pull + periodic push + close() flush on shutdown.
All sync failures are non-fatal — agent continues with local state.
"""

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class GCSFilesystemSync:
    """Syncs a local directory with a GCS bucket prefix.

    On startup: pulls latest from GCS → local.
    Periodically: pushes local → GCS every sync_interval seconds.
    On shutdown: call close() for final push (wire to FastAPI lifespan).

    Uses google-cloud-storage Python library — no gsutil dependency.

    Example:
        >>> sync = GCSFilesystemSync("auriga-marketing-memory", "./data/memory")
        >>> await sync.sync_from_gcs()      # startup pull
        >>> await sync.start_periodic_sync()  # background task
        >>> # On shutdown (FastAPI lifespan):
        >>> await sync.close()
    """

    def __init__(
        self,
        bucket_name: str,
        local_dir: str | Path = "./data/memory",
        gcs_prefix: str = "memory/",
        sync_interval: int = 300,
        project_id: str | None = None,
    ) -> None:
        """
        Args:
            bucket_name:    GCS bucket name (e.g., "auriga-marketing-memory")
            local_dir:      Local directory to sync (created if missing)
            gcs_prefix:     Key prefix inside bucket (trailing slash added if missing)
            sync_interval:  Seconds between periodic background syncs (default: 300)
            project_id:     GCP project ID (uses ADC credentials if None)
        """
        self.bucket_name = bucket_name
        self.local_dir = Path(local_dir)
        self.gcs_prefix = gcs_prefix.rstrip("/") + "/"
        self.sync_interval = sync_interval
        self.project_id = project_id
        self._sync_task: asyncio.Task | None = None

    @property
    def _gcs_uri(self) -> str:
        return f"gs://{self.bucket_name}/{self.gcs_prefix}"

    def _get_client(self):
        from google.cloud import storage
        return storage.Client(project=self.project_id)

    def _pull_from_gcs(self) -> None:
        """Pull GCS bucket prefix → local_dir (blocking, runs in executor)."""
        client = self._get_client()
        blobs = list(client.list_blobs(self.bucket_name, prefix=self.gcs_prefix))
        for blob in blobs:
            relative = blob.name[len(self.gcs_prefix):]
            if not relative:
                continue
            local_path = self.local_dir / relative
            local_path.parent.mkdir(parents=True, exist_ok=True)
            blob.download_to_filename(str(local_path))
            logger.debug(f"GCS filesystem sync: pulled {blob.name} → {local_path}")

    def _push_to_gcs(self) -> None:
        """Push local_dir → GCS bucket prefix (blocking, runs in executor)."""
        client = self._get_client()
        bucket = client.bucket(self.bucket_name)
        for local_path in self.local_dir.rglob("*"):
            if local_path.is_file():
                relative = local_path.relative_to(self.local_dir)
                gcs_path = self.gcs_prefix + str(relative)
                blob = bucket.blob(gcs_path)
                blob.upload_from_filename(str(local_path))
                logger.debug(f"GCS filesystem sync: pushed {local_path} → {gcs_path}")

    async def sync_from_gcs(self) -> None:
        """Pull GCS → local disk.

        Called once at startup before agent begins serving requests.
        Creates local_dir if it doesn't exist.
        Non-fatal: logs error and returns if GCS is unreachable.
        """
        self.local_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"GCS filesystem sync: pulling from {self._gcs_uri} → {self.local_dir}")
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._pull_from_gcs)
            logger.info("GCS filesystem sync: pull complete")
        except Exception as e:
            logger.error(f"GCS filesystem sync: pull failed: {e}")

    async def sync_to_gcs(self) -> None:
        """Push local disk → GCS.

        Called periodically by the background task and on clean shutdown.
        Non-fatal: logs error and returns on failure.
        """
        self.local_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"GCS filesystem sync: pushing {self.local_dir} → {self._gcs_uri}")
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._push_to_gcs)
            logger.info("GCS filesystem sync: push complete")
        except Exception as e:
            logger.error(f"GCS filesystem sync: push failed: {e}")

    async def start_periodic_sync(self) -> asyncio.Task:
        """Start background asyncio task that calls sync_to_gcs every sync_interval seconds.

        Returns:
            The background asyncio.Task (cancel it to stop periodic sync).
        """
        async def _loop() -> None:
            while True:
                await asyncio.sleep(self.sync_interval)
                try:
                    await self.sync_to_gcs()
                except Exception as e:
                    logger.error(f"GCS filesystem sync: periodic push error: {e}")

        self._sync_task = asyncio.create_task(_loop())
        logger.info(
            f"GCS filesystem sync: periodic task started "
            f"(interval={self.sync_interval}s, bucket={self.bucket_name})"
        )
        return self._sync_task

    async def close(self) -> None:
        """Cancel the periodic task and do a final sync_to_gcs.

        Wire this to FastAPI lifespan shutdown for clean container exit.
        """
        if self._sync_task and not self._sync_task.done():
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        await self.sync_to_gcs()
        logger.info("GCS filesystem sync: closed")
