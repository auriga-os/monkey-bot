"""GCS-backed filesystem sync for agent persistent memory.

Syncs a local directory to/from GCS so agent memory files survive
Cloud Run container restarts.

Strategy: startup pull + periodic push + SIGTERM flush.
All sync failures are non-fatal — agent continues with local state.
"""

import asyncio
import logging
import signal
from pathlib import Path

logger = logging.getLogger(__name__)


class GCSFilesystemSync:
    """Syncs a local directory with a GCS bucket prefix.

    On startup: pulls latest from GCS → local.
    Periodically: pushes local → GCS every sync_interval seconds.
    On SIGTERM: final push before Cloud Run kills the container.

    Example:
        >>> sync = GCSFilesystemSync("auriga-marketing-memory", "./data/memory")
        >>> await sync.sync_from_gcs()      # startup pull
        >>> await sync.start_periodic_sync()  # background task
        >>> sync.register_sigterm_handler()   # SIGTERM flush
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

    async def sync_from_gcs(self) -> None:
        """Pull GCS → local disk.

        Called once at startup before agent begins serving requests.
        Creates local_dir if it doesn't exist.
        Non-fatal: logs error and returns if GCS is unreachable.
        """
        self.local_dir.mkdir(parents=True, exist_ok=True)
        cmd = ["gsutil", "-m", "rsync", "-r", self._gcs_uri, str(self.local_dir) + "/"]
        logger.info(f"GCS filesystem sync: pulling from {self._gcs_uri} → {self.local_dir}")
        await self._run_gsutil(cmd, direction="pull")

    async def sync_to_gcs(self) -> None:
        """Push local disk → GCS.

        Called periodically by the background task and on SIGTERM/shutdown.
        Non-fatal: logs error and returns on failure.
        """
        self.local_dir.mkdir(parents=True, exist_ok=True)
        cmd = ["gsutil", "-m", "rsync", "-r", str(self.local_dir) + "/", self._gcs_uri]
        logger.info(f"GCS filesystem sync: pushing {self.local_dir} → {self._gcs_uri}")
        await self._run_gsutil(cmd, direction="push")

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

    def register_sigterm_handler(self) -> None:
        """Register SIGTERM handler for final sync before Cloud Run kills the container.

        Cloud Run sends SIGTERM 10s before SIGKILL.
        Handler runs sync_to_gcs() synchronously (new event loop) and exits cleanly.
        """
        def _handler(signum: int, frame: object) -> None:
            logger.info("GCS filesystem sync: SIGTERM received, running final flush...")
            asyncio.run(self.sync_to_gcs())
            logger.info("GCS filesystem sync: final flush complete")

        signal.signal(signal.SIGTERM, _handler)
        logger.debug("GCS filesystem sync: SIGTERM handler registered")

    async def close(self) -> None:
        """Cancel the periodic task and do a final sync_to_gcs.

        Call this on clean application shutdown.
        """
        if self._sync_task and not self._sync_task.done():
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        await self.sync_to_gcs()
        logger.info("GCS filesystem sync: closed")

    async def _run_gsutil(self, cmd: list[str], direction: str) -> None:
        """Run a gsutil command. Logs result. Never raises."""
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                logger.error(
                    f"GCS filesystem sync: {direction} failed "
                    f"(exit {proc.returncode}): {stderr.decode().strip()}"
                )
            else:
                logger.info(f"GCS filesystem sync: {direction} complete")
                if stdout.strip():
                    logger.debug(f"GCS filesystem sync: {stdout.decode().strip()}")
        except FileNotFoundError:
            logger.error(
                "GCS filesystem sync: gsutil not found — "
                "install google-cloud-sdk or add it to PATH"
            )
        except Exception as e:
            logger.error(f"GCS filesystem sync: {direction} unexpected error: {e}")
