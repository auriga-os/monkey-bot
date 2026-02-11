"""Shared interfaces for Emonk agent components.

This file is owned by Story 2 and defines ALL interfaces used across the project.
Story 3 imports from this file to implement SkillsEngineInterface and MemoryManagerInterface.

This is the single source of truth for:
- All abstract base classes (interfaces)
- All data structures (dataclasses)
- All custom exceptions
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class Message:
    """Conversation message.
    
    Attributes:
        role: Message role ("user", "assistant", or "system")
        content: Message text content
        timestamp: ISO8601 timestamp when message was created
        trace_id: Request trace ID for debugging and log correlation
    """

    role: str
    content: str
    timestamp: str
    trace_id: str


@dataclass
class SkillResult:
    """Result from skill execution.
    
    Attributes:
        success: True if skill executed successfully, False otherwise
        output: Skill output text (stdout or result data)
        error: Error message if success is False, None otherwise
    """

    success: bool
    output: str
    error: Optional[str] = None


@dataclass
class ExecutionResult:
    """Result from terminal command execution.
    
    Attributes:
        stdout: Standard output from command
        stderr: Standard error from command
        exit_code: Process exit code (0 = success, non-zero = error)
    """

    stdout: str
    stderr: str
    exit_code: int


# ============================================================================
# Exceptions
# ============================================================================


class EmonkError(Exception):
    """Base exception for all Emonk errors.
    
    All custom exceptions in Emonk inherit from this base class.
    This allows catching all Emonk-specific errors with a single except clause.
    """

    pass


class AgentError(EmonkError):
    """Raised when agent processing fails.
    
    Examples:
        - LLM call fails
        - Message processing fails
        - Conversation history unavailable
    """

    pass


class LLMError(EmonkError):
    """Raised when LLM API call fails.
    
    Examples:
        - Vertex AI timeout
        - Rate limit exceeded (429)
        - Model unavailable (503)
        - Invalid API credentials
    """

    pass


class SkillError(EmonkError):
    """Raised when skill execution fails.
    
    Examples:
        - Skill not found
        - Skill execution timeout
        - Terminal executor failure
        - Invalid skill arguments
    """

    pass


class SecurityError(EmonkError):
    """Raised when security validation fails.
    
    Examples:
        - Command not in ALLOWED_COMMANDS
        - Path not in ALLOWED_PATHS
        - Unauthorized user access attempt
    
    This is a critical security boundary - all SecurityErrors should be logged
    and investigated.
    """

    pass


# ============================================================================
# Agent Core Interface
# ============================================================================


class AgentCoreInterface(ABC):
    """Contract that Gateway will call.
    
    This interface defines how external components (Gateway) interact with
    the agent core. Implemented by AgentCore in src/core/agent.py.
    
    Key responsibilities:
        - Process user messages
        - Manage conversation context
        - Route to appropriate skills
        - Return formatted responses
    """

    @abstractmethod
    async def process_message(self, user_id: str, content: str, trace_id: str) -> str:
        """Process user message and return response.
        
        This is the main entry point for all user interactions. The Gateway
        filters PII before calling this method, so user_id is already hashed
        and content contains only safe user input.
        
        Args:
            user_id: Hashed user identifier (NOT email - already filtered by Gateway)
            content: Message text (PII already filtered by Gateway)
            trace_id: Request trace ID for debugging and log correlation
            
        Returns:
            Response text to send back to user via Gateway
            
        Raises:
            AgentError: If processing fails (LLM error, memory error, etc.)
            
        Example:
            >>> agent = AgentCore(llm, skills, memory)
            >>> response = await agent.process_message(
            ...     user_id="abc123",
            ...     content="Remember that I prefer Python",
            ...     trace_id="trace_xyz"
            ... )
            >>> print(response)
            "✅ I'll remember that. Stored: code_language_preference = Python"
        """
        pass


# ============================================================================
# Skills Engine Interface
# ============================================================================


class SkillsEngineInterface(ABC):
    """Contract for Skills Engine.
    
    This interface defines how the agent core interacts with the skills system.
    Implemented by SkillsEngine in src/skills/executor.py (Story 3).
    
    Key responsibilities:
        - Execute skills by name
        - List available skills
        - Manage skill lifecycle
    """

    @abstractmethod
    async def execute_skill(self, skill_name: str, args: Dict[str, Any]) -> SkillResult:
        """Execute a skill by name with arguments.
        
        Skills are discovered from ./skills/ directory at startup. Each skill
        has a SKILL.md file with metadata and a Python entry point.
        
        Args:
            skill_name: Skill identifier from SKILL.md (e.g., "file-ops", "memory")
            args: Skill arguments from LLM tool call (e.g., {"path": "./data/memory/"})
            
        Returns:
            SkillResult with success status and output
            
        Raises:
            SkillError: If skill not found or execution fails
            
        Example:
            >>> skills = SkillsEngine(terminal_executor)
            >>> result = await skills.execute_skill(
            ...     skill_name="file-ops",
            ...     args={"action": "list", "path": "./data/memory/"}
            ... )
            >>> print(result.success)  # True
            >>> print(result.output)   # "SYSTEM_PROMPT.md\nCONVERSATION_HISTORY/\n..."
        """
        pass

    @abstractmethod
    def list_skills(self) -> List[str]:
        """Return list of available skill names.
        
        Returns:
            List of skill names (e.g., ["file-ops", "memory", "shell"])
            
        Example:
            >>> skills = SkillsEngine(terminal_executor)
            >>> print(skills.list_skills())
            ["file-ops", "memory-remember", "memory-recall"]
        """
        pass


# ============================================================================
# Memory Manager Interface
# ============================================================================


class MemoryManagerInterface(ABC):
    """Contract for Memory Manager.
    
    This interface defines how the agent core interacts with persistent memory.
    Implemented by MemoryManager in src/core/memory.py (Story 3).
    
    Key responsibilities:
        - Read/write conversation history
        - Read/write knowledge facts
        - Sync to GCS (optional)
    """

    @abstractmethod
    async def read_conversation_history(self, user_id: str, limit: int = 10) -> List[Message]:
        """Read recent conversation history.
        
        Returns the most recent conversation messages for context window.
        Messages are returned in chronological order (oldest first).
        
        Args:
            user_id: Hashed user identifier
            limit: Max messages to return (default 10 for context window)
            
        Returns:
            List of recent messages (oldest first)
            
        Example:
            >>> memory = MemoryManager()
            >>> history = await memory.read_conversation_history("user123", limit=5)
            >>> for msg in history:
            ...     print(f"{msg.role}: {msg.content[:30]}...")
            user: Remember that I prefer Pyt...
            assistant: ✅ I'll remember that...
        """
        pass

    @abstractmethod
    async def write_conversation(
        self, user_id: str, role: str, content: str, trace_id: str
    ) -> None:
        """Write a conversation message.
        
        Appends message to conversation history file and optionally syncs to GCS.
        
        Args:
            user_id: Hashed user identifier
            role: "user" or "assistant" (system messages handled separately)
            content: Message content
            trace_id: Request trace ID for debugging
            
        Example:
            >>> memory = MemoryManager()
            >>> await memory.write_conversation(
            ...     user_id="user123",
            ...     role="user",
            ...     content="What's my preferred language?",
            ...     trace_id="trace_abc"
            ... )
        """
        pass

    @abstractmethod
    async def read_fact(self, user_id: str, key: str) -> Optional[str]:
        """Read a fact from knowledge base.
        
        Facts are persistent key-value pairs stored per user.
        
        Args:
            user_id: Hashed user identifier
            key: Fact key (e.g., "code_language_preference")
            
        Returns:
            Fact value if exists, None otherwise
            
        Example:
            >>> memory = MemoryManager()
            >>> preference = await memory.read_fact("user123", "code_language_preference")
            >>> print(preference)  # "Python"
        """
        pass

    @abstractmethod
    async def write_fact(self, user_id: str, key: str, value: str) -> None:
        """Write a fact to knowledge base.
        
        Stores or updates a fact in the knowledge base file and optionally syncs to GCS.
        
        Args:
            user_id: Hashed user identifier
            key: Fact key (e.g., "code_language_preference")
            value: Fact value (e.g., "Python")
            
        Example:
            >>> memory = MemoryManager()
            >>> await memory.write_fact(
            ...     user_id="user123",
            ...     key="code_language_preference",
            ...     value="Python"
            ... )
        """
        pass
