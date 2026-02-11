"""Core agent components for Emonk.

This module provides the main agent orchestration components including:
- Agent Core (LangGraph orchestration)
- LLM Client (Vertex AI wrapper)
- Memory Manager (persistent storage)
- Terminal Executor (secure command execution)
- Shared interfaces for all components
"""

# Import interfaces first (no dependencies)
from .interfaces import (
    AgentCoreInterface,
    AgentError,
    EmonkError,
    ExecutionResult,
    LLMError,
    MemoryManagerInterface,
    Message,
    SecurityError,
    SkillError,
    SkillResult,
    SkillsEngineInterface,
)

# Import implementations (depend on interfaces)
from .llm_client import LLMClient
from .agent import AgentCore, create_agent_with_mocks

# Story 3 components (if they exist)
try:
    from .terminal import TerminalExecutor
    from .memory import MemoryManager
    _story3_available = True
except ImportError:
    _story3_available = False

# Build __all__ dynamically
__all__ = [
    # Story 2: Core classes
    "AgentCore",
    "LLMClient",
    "create_agent_with_mocks",
    # Story 2: Interfaces
    "AgentCoreInterface",
    "SkillsEngineInterface",
    "MemoryManagerInterface",
    # Story 2: Data classes
    "Message",
    "SkillResult",
    "ExecutionResult",
    # Story 2: Exceptions
    "EmonkError",
    "AgentError",
    "LLMError",
    "SkillError",
    "SecurityError",
]

# Add Story 3 exports if available
if _story3_available:
    __all__.extend(["TerminalExecutor", "MemoryManager"])
