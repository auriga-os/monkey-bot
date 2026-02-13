"""
Sandbox backend for isolated code execution.

This module provides sandbox backends for running untrusted code in isolated
environments. Currently supports Modal as an optional backend.

Example:
    >>> from src.sandbox import ModalSandboxBackend
    >>> sandbox = ModalSandboxBackend()
    >>> result = await sandbox.execute("echo 'Hello from sandbox'")
    >>> print(result.output)
"""

from __future__ import annotations

# Try to import Modal backend
try:
    from .modal import (
        ModalSandboxBackend,
        SandboxError,
        SandboxTimeoutError,
        SandboxUnavailableError,
    )

    __all__ = [
        "ModalSandboxBackend",
        "SandboxError",
        "SandboxTimeoutError",
        "SandboxUnavailableError",
    ]
except ImportError:
    # Modal not installed - provide helpful error message
    class ModalSandboxBackend:  # type: ignore[no-redef]
        """Placeholder for ModalSandboxBackend when modal is not installed."""

        def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise ImportError(
                "modal package required for sandbox execution. "
                "Install with: pip install emonk[modal]"
            )

    class SandboxError(Exception):  # type: ignore[no-redef]
        """Base sandbox error."""
        pass

    class SandboxTimeoutError(SandboxError):  # type: ignore[no-redef]
        """Command exceeded timeout."""
        pass

    class SandboxUnavailableError(SandboxError):  # type: ignore[no-redef]
        """Sandbox service unreachable."""
        pass

    __all__ = [
        "ModalSandboxBackend",
        "SandboxError",
        "SandboxTimeoutError",
        "SandboxUnavailableError",
    ]
