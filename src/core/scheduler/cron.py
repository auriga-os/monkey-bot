"""Simple in-memory cron scheduler for background jobs.

This module provides a lightweight scheduler for executing background jobs
at specified times. Jobs are persisted to disk and survive agent restarts.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class CronScheduler:
    """Simple in-memory cron scheduler for background jobs.

    For MVP, this is a simple polling-based scheduler.
    Future: Use APScheduler or similar for production.

    Features:
        - Schedule jobs for future execution
        - Automatic retry on failure (max 3 attempts)
        - Persistent storage (survives restarts)
        - Async execution

    Example:
        >>> scheduler = CronScheduler(agent_state)
        >>> job_id = await scheduler.schedule_job(
        ...     job_type="post_content",
        ...     schedule_at=datetime.utcnow() + timedelta(hours=1),
        ...     payload={"platform": "x", "content": "Hello"}
        ... )
        >>> await scheduler.start()  # Start background processing
    """

    def __init__(self, agent_state: Any, check_interval_seconds: int = 10):
        """Initialize scheduler.

        Args:
            agent_state: Agent state for accessing skills and memory
            check_interval_seconds: How often to check for due jobs (default 10)
        """
        self.agent_state = agent_state
        self.check_interval = check_interval_seconds
        self.jobs: list[dict[str, Any]] = []
        self.running = False
        self._job_handlers: dict[str, Any] = {}
        self._load_jobs()

    async def schedule_job(
        self,
        job_type: str,
        schedule_at: datetime,
        payload: dict[str, Any]
    ) -> str:
        """Schedule a job to run at specified time.

        Args:
            job_type: Type of job (e.g., "post_content")
            schedule_at: When to run the job (datetime)
            payload: Job-specific data

        Returns:
            Job ID (UUID)

        Example:
            >>> job_id = await scheduler.schedule_job(
            ...     job_type="post_content",
            ...     schedule_at=datetime.utcnow() + timedelta(hours=1),
            ...     payload={"campaign_id": "abc", "platform": "x"}
            ... )
        """
        job_id = str(uuid4())

        job = {
            "id": job_id,
            "job_type": job_type,
            "schedule_at": schedule_at.isoformat(),
            "payload": payload,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "attempts": 0,
            "max_attempts": 3
        }

        self.jobs.append(job)
        self._save_jobs()

        logger.info(
            "Job scheduled",
            extra={
                "job_id": job_id,
                "job_type": job_type,
                "schedule_at": schedule_at.isoformat()
            }
        )

        return job_id

    async def start(self):
        """Start the scheduler background task.

        This method runs continuously, checking for due jobs every
        check_interval seconds. Call stop() to terminate.

        Example:
            >>> scheduler = CronScheduler(agent_state)
            >>> task = asyncio.create_task(scheduler.start())
            >>> # ... later ...
            >>> await scheduler.stop()
        """
        self.running = True
        logger.info("Cron scheduler started")

        while self.running:
            await self._check_and_execute_jobs()
            await asyncio.sleep(self.check_interval)

    async def stop(self):
        """Stop the scheduler.

        This sets the running flag to False, causing the background
        task to exit on its next iteration.
        """
        self.running = False
        logger.info("Cron scheduler stopped")

    def register_handler(self, job_type: str, handler: Any):
        """Register a job handler for a specific job type.

        This allows external code to register custom handlers for different
        job types, making the scheduler extensible and framework-agnostic.

        Args:
            job_type: Type of job (e.g., "post_content", "collect_metrics")
            handler: Async callable that takes a job dict as argument

        Example:
            >>> async def my_handler(job):
            ...     print(f"Executing job: {job['id']}")
            >>> scheduler.register_handler("my_job_type", my_handler)
        """
        self._job_handlers[job_type] = handler
        logger.info(f"Registered handler for job type: {job_type}")

    async def _check_and_execute_jobs(self):
        """Check for due jobs and execute them."""
        now = datetime.utcnow()

        for job in self.jobs:
            if job["status"] != "pending":
                continue

            schedule_at = datetime.fromisoformat(job["schedule_at"])

            if schedule_at <= now:
                await self._execute_job(job)

    async def _execute_job(self, job: dict[str, Any]):
        """Execute a single job using registered handlers.

        Args:
            job: Job dict with id, job_type, payload, etc.
        """
        job_id = job["id"]
        job_type = job["job_type"]

        logger.info(f"Executing job {job_id} (type: {job_type})")

        try:
            job["status"] = "running"
            job["started_at"] = datetime.utcnow().isoformat()
            self._save_jobs()

            # Look up handler from registry
            handler = self._job_handlers.get(job_type)
            if not handler:
                raise ValueError(f"No handler registered for job type: {job_type}")

            # Inject agent state into job context for handlers to use
            job["_agent_state"] = self.agent_state

            try:
                # Execute the handler
                await handler(job)
            finally:
                # Always clean up agent state from job dict (even on error)
                job.pop("_agent_state", None)

            # Mark as completed
            job["status"] = "completed"
            job["completed_at"] = datetime.utcnow().isoformat()

            logger.info(f"Job {job_id} completed successfully")

        except Exception as e:
            job["attempts"] += 1
            logger.error(f"Job {job_id} failed: {e}", extra={"job": job})

            if job["attempts"] >= job["max_attempts"]:
                job["status"] = "failed"
                job["error"] = str(e)
            else:
                # Retry later (reschedule for 5 minutes from now)
                retry_at = datetime.utcnow() + timedelta(minutes=5)
                job["schedule_at"] = retry_at.isoformat()
                job["status"] = "pending"
                logger.info(f"Job {job_id} will retry at {retry_at}")

        finally:
            # Ensure agent state is cleaned up before saving
            job.pop("_agent_state", None)
            self._save_jobs()

    def _load_jobs(self):
        """Load jobs from disk (persistence)."""
        jobs_file = self.agent_state.memory_dir / "scheduler" / "jobs.json"

        if jobs_file.exists():
            self.jobs = json.loads(jobs_file.read_text())
            logger.info(f"Loaded {len(self.jobs)} jobs from disk")

    def _save_jobs(self):
        """Save jobs to disk (persistence)."""
        jobs_file = self.agent_state.memory_dir / "scheduler" / "jobs.json"
        jobs_file.parent.mkdir(parents=True, exist_ok=True)
        jobs_file.write_text(json.dumps(self.jobs, indent=2))

    def get_pending_jobs(self) -> list[dict[str, Any]]:
        """Get all pending jobs.

        Returns:
            List of job dicts with status="pending"
        """
        return [job for job in self.jobs if job["status"] == "pending"]

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        """Get job by ID.

        Args:
            job_id: Job UUID to lookup

        Returns:
            Job dict if found, None otherwise
        """
        for job in self.jobs:
            if job["id"] == job_id:
                return job
        return None
