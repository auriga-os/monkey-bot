"""Job handler pattern for CronScheduler.

Provides a base class and utilities for registering job handlers that execute
scheduled tasks. Handlers are async functions that receive job dicts and
perform work when jobs are due.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Callable

logger = logging.getLogger(__name__)


class JobHandler(ABC):
    """Base class for job handlers.

    Handlers are registered with the scheduler and executed when jobs of their
    type become due. Subclass this and implement handle() for your job type.

    Example:
        >>> class EmailHandler(JobHandler):
        ...     async def handle(self, job: dict[str, Any]) -> None:
        ...         payload = job["payload"]
        ...         recipient = payload["email"]
        ...         await send_email(recipient, payload["message"])
        ...
        >>> scheduler = CronScheduler(...)
        >>> scheduler.register_handler("send_email", EmailHandler())
    """

    @abstractmethod
    async def handle(self, job: dict[str, Any]) -> None:
        """Handle a scheduled job.

        This method is called when a job of this handler's type is due for
        execution. It receives the full job dict including payload data.

        Args:
            job: Job dict containing:
                - id: Job ID (str)
                - job_type: Job type (str)
                - payload: Job-specific data (dict)
                - schedule_at: When job was scheduled (ISO datetime str)
                - created_at: When job was created (ISO datetime str)
                - attempts: Number of execution attempts (int)
                - status: Job status (str)

        Raises:
            Exception: Any exception raised will mark the job as failed
                and be logged. If attempts < max_attempts, job will be retried.

        Example:
            >>> job = {
            ...     "id": "abc123",
            ...     "job_type": "send_email",
            ...     "payload": {"email": "user@example.com", "message": "Hello"},
            ...     "schedule_at": "2024-02-14T09:00:00+00:00",
            ...     "created_at": "2024-02-14T08:00:00+00:00",
            ...     "attempts": 0,
            ...     "status": "pending"
            ... }
            >>> handler = EmailHandler()
            >>> await handler.handle(job)
        """
        pass


class FunctionJobHandler(JobHandler):
    """Wrapper to use a simple function as a job handler.

    This allows using async functions directly as handlers without
    subclassing JobHandler. Used internally by register_handler().

    Args:
        func: Async function that takes a job dict and returns None

    Example:
        >>> async def my_handler(job: dict[str, Any]) -> None:
        ...     print(f"Handling job: {job['id']}")
        ...
        >>> handler = FunctionJobHandler(my_handler)
        >>> await handler.handle(job)
    """

    def __init__(self, func: Callable[[dict[str, Any]], Any]):
        """Initialize function handler wrapper.

        Args:
            func: Async function to wrap as a handler
        """
        self.func = func

    async def handle(self, job: dict[str, Any]) -> None:
        """Delegate to wrapped function.

        Args:
            job: Job dict to pass to function
        """
        await self.func(job)


def register_handler(
    scheduler,
    job_type: str,
    handler: JobHandler | Callable[[dict[str, Any]], Any],
) -> None:
    """Register a job handler with the scheduler.

    This is a convenience function for registering handlers. It supports both
    JobHandler instances and simple async functions.

    Args:
        scheduler: CronScheduler instance to register with
        job_type: Job type string (e.g., "send_email", "generate_report")
        handler: JobHandler instance or async function(job) -> None

    Example:
        >>> # Register a JobHandler subclass instance
        >>> scheduler = CronScheduler(...)
        >>> handler = EmailHandler()
        >>> register_handler(scheduler, "send_email", handler)

        >>> # Register a simple async function
        >>> async def report_handler(job: dict[str, Any]) -> None:
        ...     print(f"Generating report: {job['payload']}")
        ...
        >>> register_handler(scheduler, "generate_report", report_handler)
    """
    # If handler is a callable function (not a JobHandler instance),
    # wrap it in FunctionJobHandler
    if not isinstance(handler, JobHandler):
        if not callable(handler):
            raise TypeError(
                f"Handler must be a JobHandler instance or callable, got {type(handler)}"
            )
        handler = FunctionJobHandler(handler)

    # Register with scheduler
    scheduler.register_handler(job_type, handler)
    logger.info(f"Registered handler for job type: {job_type}")
