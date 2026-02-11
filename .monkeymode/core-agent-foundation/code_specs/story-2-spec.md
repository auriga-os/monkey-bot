# Code Spec: Story 2 - Agent Core + LLM Client

**Story**: Agent Core + LLM Client - Orchestration & Intelligence  
**Design Reference**: Phase 1A (Agent Core Module), Phase 1B (Agent Core → LLM Client)  
**Author**: Emonk MonkeyMode  
**Date**: 2026-02-11

---

## Implementation Summary

- **Files to Create**: 8 files (5 source, 3 test)
- **Files to Modify**: 0 (greenfield implementation)
- **Tests to Add**: 2 test files (unit tests for agent + llm_client)
- **Estimated Complexity**: M (3-5 days)
- **Dependencies**: NONE (Sprint 1 - fully parallel with Story 1 and Story 3)

---

## Codebase Conventions

**Project Setup**:
- Python 3.11+ (modern async, type hints)
- Package manager: `uv` (fast Python package installer)
- Formatter: `ruff` (fast linter + formatter)
- Testing: `pytest` + `pytest-asyncio` + `pytest-cov`
- Type checking: `mypy` (strict mode)

**File/Module Naming**:
- Modules: `snake_case.py` (e.g., `llm_client.py`)
- Classes: `PascalCase` (e.g., `AgentCore`)
- Functions: `snake_case` (e.g., `process_message`)
- Private methods: `_snake_case` (e.g., `_build_context`)

**Import Order** (ruff will enforce):
1. Standard library
2. Third-party (LangChain, LangGraph, etc.)
3. Local imports

**Error Handling**:
- Custom exceptions inherit from base `EmonkError`
- Specific error classes: `AgentError`, `LLMError`, `SkillError`
- Always include helpful error messages
- Log errors with trace_id for debugging

**Type Hints**:
- All public functions must have type hints
- Use `typing` module types (List, Dict, Optional)
- Use dataclasses for structured data

**Docstrings** (Google style):
```python
def process_message(self, user_id: str, content: str, trace_id: str) -> str:
    """Process user message and return response.
    
    Args:
        user_id: Hashed user identifier (not email)
        content: Message text (PII already filtered)
        trace_id: Request trace ID for debugging
        
    Returns:
        Response text to send back to user
        
    Raises:
        AgentError: If processing fails
    """
```

**Logging**:
- Use Python's `logging` module
- Structured format: Include timestamp, level, component, trace_id
- Log at appropriate levels: DEBUG, INFO, WARNING, ERROR
- Example: `logger.info("Processing message", extra={"trace_id": trace_id, "component": "agent_core"})`

---

## Technical Context

**Key Dependencies**:
- `langgraph` - Agent orchestration (0.2.x)
- `langchain-google-vertexai` - Vertex AI LangChain integration
- `google-cloud-aiplatform` - Vertex AI SDK
- `pydantic` - Data validation (used by LangChain)

**LLM Models**:
- **Primary**: Gemini 2.5 Flash (`gemini-2.5-flash-002`)
- **Fallback**: Claude Haiku 4.5 (future - not in Sprint 1)
- **Testing**: MockVertexAI (simple callable mock)

**Integration Points**:
- Story 2 owns `src/core/interfaces.py` - ALL shared interfaces defined here
- Story 3 imports from this file (SkillsEngineInterface, MemoryManagerInterface)
- Story 1 imports AgentCoreInterface from this file (removed in Story 4)

**Gotchas**:
- LangGraph requires async functions - use `async def` everywhere
- Mock dependencies for Sprint 1 - no real Vertex AI calls yet
- Conversation context limited to 10 messages (configurable constant)
- Streaming deferred to Story 4 (document but don't implement)

---

## Task Breakdown

### Task 1: Project Structure + Dependencies

**Dependencies:** None

**Files to Create**:
- `pyproject.toml` - Project metadata + dependencies
- `requirements.txt` - Pinned dependencies (generated from pyproject.toml)
- `.python-version` - Python version (3.11)
- `pytest.ini` - Pytest configuration
- `mypy.ini` - Type checking configuration
- `ruff.toml` - Linter/formatter configuration

**Implementation**:

Create project with modern Python tooling:

**pyproject.toml**:
```toml
[project]
name = "emonk"
version = "1.0.0"
description = "Open-source framework for building single-purpose AI agents"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "langgraph>=0.2.0",
    "langchain-google-vertexai>=2.0.0",
    "google-cloud-aiplatform>=1.70.0",
    "google-cloud-storage>=2.18.0",
    "pydantic>=2.10.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "mypy>=1.13.0",
    "ruff>=0.8.0",
    "httpx>=0.27.0",  # For testing FastAPI
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]  # Error, pyflakes, isort, naming, warnings
ignore = ["E501"]  # Line too long (handled by formatter)

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
asyncio_mode = "auto"
addopts = "--cov=src --cov-report=term-missing --cov-report=html"

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

**Directory structure**:
```
emonk/
├── src/
│   └── core/
│       ├── __init__.py
│       ├── interfaces.py  # Story 2 owns this - ALL shared interfaces
│       ├── agent.py
│       ├── llm_client.py
│       └── mocks.py
├── tests/
│   └── core/
│       ├── __init__.py
│       ├── test_agent.py
│       └── test_llm_client.py
├── pyproject.toml
├── requirements.txt
├── .python-version
└── README.md
```

**Commands to run**:
```bash
# Create structure
mkdir -p src/core tests/core
touch src/core/__init__.py tests/core/__init__.py

# Set Python version
echo "3.11" > .python-version

# Generate requirements.txt from pyproject.toml
uv pip compile pyproject.toml -o requirements.txt

# Install dependencies
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

**Tests**: Not applicable (setup task)

---

### Task 2: Create Shared Interfaces (src/core/interfaces.py)

**Dependencies:** Task 1

**Files to Create**:
- `src/core/interfaces.py` - ALL shared interfaces for entire project

**Implementation**:

**CRITICAL**: Story 2 owns this file. Story 3 imports from here. This is the single source of truth for all interfaces.

```python
# src/core/interfaces.py
"""Shared interfaces for Emonk agent components.

This file is owned by Story 2 and defines ALL interfaces used across the project.
Story 3 imports from this file to implement SkillsEngineInterface and MemoryManagerInterface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class Message:
    """Conversation message."""
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: str  # ISO8601 format
    trace_id: str


@dataclass
class SkillResult:
    """Result from skill execution."""
    success: bool
    output: str
    error: Optional[str] = None


@dataclass
class ExecutionResult:
    """Result from terminal command execution."""
    stdout: str
    stderr: str
    exit_code: int


# ============================================================================
# Exceptions
# ============================================================================

class EmonkError(Exception):
    """Base exception for all Emonk errors."""
    pass


class AgentError(EmonkError):
    """Raised when agent processing fails."""
    pass


class LLMError(EmonkError):
    """Raised when LLM API call fails."""
    pass


class SkillError(EmonkError):
    """Raised when skill execution fails."""
    pass


class SecurityError(EmonkError):
    """Raised when security validation fails (terminal executor)."""
    pass


# ============================================================================
# Agent Core Interface
# ============================================================================

class AgentCoreInterface(ABC):
    """Contract that Gateway will call.
    
    This interface is implemented by AgentCore in src/core/agent.py.
    """
    
    @abstractmethod
    async def process_message(
        self, 
        user_id: str, 
        content: str, 
        trace_id: str
    ) -> str:
        """Process user message and return response.
        
        Args:
            user_id: Hashed user identifier (not email)
            content: Message text (PII already filtered)
            trace_id: Request trace ID for debugging
            
        Returns:
            Response text to send back to user
            
        Raises:
            AgentError: If processing fails
        """
        pass


# ============================================================================
# Skills Engine Interface
# ============================================================================

class SkillsEngineInterface(ABC):
    """Contract for Skills Engine.
    
    This interface is implemented by SkillsEngine in src/skills/executor.py (Story 3).
    """
    
    @abstractmethod
    async def execute_skill(
        self, 
        skill_name: str, 
        args: Dict[str, Any]
    ) -> SkillResult:
        """Execute a skill by name with arguments.
        
        Args:
            skill_name: Skill identifier from SKILL.md
            args: Skill arguments from LLM tool call
            
        Returns:
            SkillResult with success status and output
            
        Raises:
            SkillError: If skill not found or execution fails
        """
        pass
    
    @abstractmethod
    def list_skills(self) -> List[str]:
        """Return list of available skill names."""
        pass


# ============================================================================
# Memory Manager Interface
# ============================================================================

class MemoryManagerInterface(ABC):
    """Contract for Memory Manager.
    
    This interface is implemented by MemoryManager in src/core/memory.py (Story 3).
    """
    
    @abstractmethod
    async def read_conversation_history(
        self, 
        user_id: str, 
        limit: int = 10
    ) -> List[Message]:
        """Read recent conversation history.
        
        Args:
            user_id: Hashed user identifier
            limit: Max messages to return (default 10)
            
        Returns:
            List of recent messages (oldest first)
        """
        pass
    
    @abstractmethod
    async def write_conversation(
        self,
        user_id: str,
        role: str,
        content: str,
        trace_id: str
    ) -> None:
        """Write a conversation message.
        
        Args:
            user_id: Hashed user identifier
            role: "user" or "assistant"
            content: Message content
            trace_id: Request trace ID
        """
        pass
    
    @abstractmethod
    async def read_fact(self, user_id: str, key: str) -> Optional[str]:
        """Read a fact from knowledge base.
        
        Args:
            user_id: Hashed user identifier
            key: Fact key
            
        Returns:
            Fact value if exists, None otherwise
        """
        pass
    
    @abstractmethod
    async def write_fact(self, user_id: str, key: str, value: str) -> None:
        """Write a fact to knowledge base.
        
        Args:
            user_id: Hashed user identifier
            key: Fact key
            value: Fact value
        """
        pass
```

**Tests**:
- Import test: `from src.core.interfaces import AgentCoreInterface, SkillsEngineInterface`
- Type checking: `mypy src/core/interfaces.py` should pass
- Dataclass validation: Create Message/SkillResult instances

---

### Task 3: Create Mock Dependencies (src/core/mocks.py)

**Dependencies:** Task 2

**Files to Create**:
- `src/core/mocks.py` - Mock implementations for testing

**Implementation**:

```python
# src/core/mocks.py
"""Mock implementations for parallel development and testing."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .interfaces import (
    ExecutionResult,
    MemoryManagerInterface,
    Message,
    SkillResult,
    SkillsEngineInterface,
)

logger = logging.getLogger(__name__)


class MockSkillsEngine(SkillsEngineInterface):
    """Mock Skills Engine for Agent Core testing.
    
    Returns canned responses for skill execution without real terminal execution.
    Story 4 replaces this with real SkillsEngine implementation.
    """
    
    async def execute_skill(self, skill_name: str, args: Dict[str, Any]) -> SkillResult:
        """Return mock success response for any skill."""
        logger.info(f"[MOCK] Executing skill: {skill_name} with args: {args}")
        return SkillResult(
            success=True,
            output=f"Mock execution of '{skill_name}' with args: {args}"
        )
    
    def list_skills(self) -> List[str]:
        """Return list of mock skills."""
        return ["memory-remember", "memory-recall", "file-ops"]


class MockMemoryManager(MemoryManagerInterface):
    """Mock Memory Manager for Agent Core testing.
    
    Stores data in-memory (dict) instead of filesystem/GCS.
    Story 4 replaces this with real MemoryManager implementation.
    """
    
    def __init__(self) -> None:
        self.conversation_history: List[Message] = []
        self.facts: Dict[str, str] = {}
    
    async def read_conversation_history(self, user_id: str, limit: int = 10) -> List[Message]:
        """Return last N messages from in-memory history."""
        return self.conversation_history[-limit:]
    
    async def write_conversation(
        self,
        user_id: str,
        role: str,
        content: str,
        trace_id: str
    ) -> None:
        """Append message to in-memory history."""
        self.conversation_history.append(Message(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(),
            trace_id=trace_id
        ))
        logger.info(f"[MOCK] Wrote conversation: role={role}, content_len={len(content)}")
    
    async def read_fact(self, user_id: str, key: str) -> Optional[str]:
        """Read fact from in-memory dict."""
        return self.facts.get(key)
    
    async def write_fact(self, user_id: str, key: str, value: str) -> None:
        """Write fact to in-memory dict."""
        self.facts[key] = value
        logger.info(f"[MOCK] Wrote fact: {key}={value}")


class MockVertexAI:
    """Mock Vertex AI client for LLM testing.
    
    Returns canned responses without real API calls.
    Story 4 replaces this with real ChatVertexAI from langchain-google-vertexai.
    """
    
    async def ainvoke(self, messages: List[Dict[str, str]]) -> str:
        """Return mock LLM response based on last user message."""
        last_message = messages[-1]["content"]
        
        # Simple mock logic for testing
        if "remember" in last_message.lower():
            return "I'll remember that preference."
        elif "recall" in last_message.lower() or "what" in last_message.lower():
            return "According to my memory, you prefer Python."
        else:
            return f"Mock LLM response to: {last_message[:50]}..."
```

**Tests** (follow pattern in Task 5 - test_agent.py):
- Mock returns correct responses
- Mock stores data correctly (in-memory)
- Mock logging works

---

### Task 4: Create LLM Client (src/core/llm_client.py)

**Dependencies:** Task 2, Task 3

**Files to Create**:
- `src/core/llm_client.py` - Vertex AI client wrapper

**Implementation**:

```python
# src/core/llm_client.py
"""LLM client wrapper for Vertex AI integration."""

import logging
from typing import Any, Dict, List

from .interfaces import LLMError

logger = logging.getLogger(__name__)

# Configuration constants
DEFAULT_MODEL = "gemini-2.5-flash-002"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 2048


class LLMClient:
    """Vertex AI Gemini client wrapper.
    
    For Sprint 1: Uses MockVertexAI (passed via constructor).
    For Story 4: Uses real ChatVertexAI from langchain-google-vertexai.
    """
    
    def __init__(self, vertex_client: Any) -> None:
        """Initialize LLM client.
        
        Args:
            vertex_client: MockVertexAI for Sprint 1 testing
                          (Real ChatVertexAI added in Story 4)
        """
        self.client = vertex_client
        self.model = DEFAULT_MODEL
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = DEFAULT_MODEL,
        stream: bool = False
    ) -> str:
        """Call LLM with conversation context.
        
        Args:
            messages: Conversation history [{"role": "user", "content": "..."}]
            model: "gemini-2.5-flash-002" (default) or "claude-haiku-4.5" (future)
            stream: Enable streaming for long responses (Story 4 - defer implementation)
            
        Returns:
            LLM response text
            
        Raises:
            LLMError: If API call fails after retries
            
        Note:
            Streaming is deferred to Story 4. Set stream=True but don't implement yet.
            Story 4 will add real streaming support for responses > 200 tokens.
        """
        logger.info(
            f"Calling LLM: {model}",
            extra={
                "component": "llm_client",
                "model": model,
                "message_count": len(messages),
                "stream": stream
            }
        )
        
        try:
            # For Sprint 1: Use MockVertexAI (simple mock)
            # Story 4: Replace with real ChatVertexAI with retry logic (3x exponential backoff)
            response = await self.client.ainvoke(messages)
            
            logger.info(
                "LLM response received",
                extra={
                    "component": "llm_client",
                    "response_length": len(response)
                }
            )
            
            return response
        
        except Exception as e:
            logger.error(
                f"LLM call failed: {e}",
                extra={"component": "llm_client", "error": str(e)}
            )
            raise LLMError(f"LLM call failed: {e}") from e
```

**Tests** (concise - follow pattern in test_agent.py):
- Call with valid messages → Returns response
- Call with mock that raises exception → Raises LLMError
- Verify logging includes model, message_count

---

### Task 5: Create Agent Core with LangGraph (src/core/agent.py)

**Dependencies:** Task 2, Task 3, Task 4

**Files to Create**:
- `src/core/agent.py` - LangGraph agent orchestration

**Implementation**:

**Pattern**: Simple single-step agent (user message → LLM → response). No multi-step reasoning in Sprint 1.

```python
# src/core/agent.py
"""LangGraph-based agent orchestration."""

import logging
from typing import List

from .interfaces import (
    AgentCoreInterface,
    AgentError,
    MemoryManagerInterface,
    Message,
    SkillsEngineInterface,
)
from .llm_client import LLMClient

logger = logging.getLogger(__name__)

# Configuration constants
CONVERSATION_CONTEXT_LIMIT = 10  # Last N messages sent to LLM


class AgentCore(AgentCoreInterface):
    """LangGraph-based agent orchestration.
    
    Simple single-step agent for Sprint 1:
    - Load conversation context (last 10 messages)
    - Call LLM with context + new message
    - Save conversation history
    - Return response
    
    Future (Story 4): Add multi-step reasoning, tool calling, streaming.
    """
    
    def __init__(
        self,
        llm_client: LLMClient,
        skills_engine: SkillsEngineInterface,
        memory_manager: MemoryManagerInterface
    ) -> None:
        """Initialize Agent Core.
        
        Args:
            llm_client: LLM client wrapper
            skills_engine: Skills execution engine (MockSkillsEngine for Sprint 1)
            memory_manager: Memory manager (MockMemoryManager for Sprint 1)
        """
        self.llm = llm_client
        self.skills = skills_engine
        self.memory = memory_manager
    
    async def process_message(
        self, 
        user_id: str, 
        content: str, 
        trace_id: str
    ) -> str:
        """Process user message and return response.
        
        Flow:
        1. Load conversation context (last 10 messages)
        2. Build messages for LLM (history + new user message)
        3. Call LLM
        4. Save user message + assistant response to memory
        5. Return response
        
        Args:
            user_id: Hashed user identifier (not email)
            content: Message text (PII already filtered)
            trace_id: Request trace ID for debugging
            
        Returns:
            Response text to send back to user
            
        Raises:
            AgentError: If processing fails
        """
        logger.info(
            "Processing message",
            extra={
                "trace_id": trace_id,
                "component": "agent_core",
                "user_id": user_id,
                "content_length": len(content)
            }
        )
        
        try:
            # Step 1: Load conversation context
            history = await self.memory.read_conversation_history(
                user_id, 
                limit=CONVERSATION_CONTEXT_LIMIT
            )
            
            # Step 2: Build messages for LLM (history + new user message)
            messages = self._build_llm_messages(history, content)
            
            # Step 3: Call LLM
            response = await self.llm.chat(
                messages=messages,
                model="gemini-2.5-flash-002",
                stream=False  # Streaming deferred to Story 4
            )
            
            # Step 4: Save conversation to memory
            await self.memory.write_conversation(user_id, "user", content, trace_id)
            await self.memory.write_conversation(user_id, "assistant", response, trace_id)
            
            logger.info(
                "Message processed successfully",
                extra={
                    "trace_id": trace_id,
                    "component": "agent_core",
                    "response_length": len(response)
                }
            )
            
            return response
        
        except Exception as e:
            logger.error(
                f"Message processing failed: {e}",
                extra={
                    "trace_id": trace_id,
                    "component": "agent_core",
                    "error": str(e)
                }
            )
            raise AgentError(f"Message processing failed: {e}") from e
    
    def _build_llm_messages(self, history: List[Message], new_content: str) -> List[dict]:
        """Build messages list for LLM from history + new message.
        
        Args:
            history: Recent conversation messages
            new_content: New user message
            
        Returns:
            List of message dicts: [{"role": "user", "content": "..."}]
        """
        messages = []
        
        # Add conversation history
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})
        
        # Add new user message
        messages.append({"role": "user", "content": new_content})
        
        return messages


# Factory function for testing
def create_agent_with_mocks() -> AgentCore:
    """Create agent with mock dependencies for testing.
    
    Returns:
        AgentCore with MockVertexAI, MockSkillsEngine, MockMemoryManager
    """
    from .mocks import MockMemoryManager, MockSkillsEngine, MockVertexAI
    
    llm_client = LLMClient(vertex_client=MockVertexAI())
    skills_engine = MockSkillsEngine()
    memory_manager = MockMemoryManager()
    
    return AgentCore(llm_client, skills_engine, memory_manager)
```

**Tests** (see Task 6 for complete test file example):
- Process message with empty history → Returns response
- Process message with 10 messages history → Context sent to LLM
- Process message saves to memory → Verify write_conversation called 2x
- LLM fails → Raises AgentError with clear message
- Verify trace_id in logs

---

### Task 6: Unit Tests for Agent Core

**Dependencies:** Task 5

**Files to Create**:
- `tests/core/test_agent.py` - Unit tests for AgentCore

**Implementation**:

**COMPLETE TEST EXAMPLE** (pattern for all other test files):

```python
# tests/core/test_agent.py
"""Unit tests for Agent Core."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.agent import AgentCore, create_agent_with_mocks
from src.core.interfaces import AgentError, Message
from src.core.llm_client import LLMClient
from src.core.mocks import MockMemoryManager, MockSkillsEngine, MockVertexAI


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client."""
    vertex_client = MockVertexAI()
    return LLMClient(vertex_client)


@pytest.fixture
def mock_skills_engine():
    """Create mock skills engine."""
    return MockSkillsEngine()


@pytest.fixture
def mock_memory_manager():
    """Create mock memory manager."""
    return MockMemoryManager()


@pytest.fixture
def agent_core(mock_llm_client, mock_skills_engine, mock_memory_manager):
    """Create AgentCore with mocked dependencies."""
    return AgentCore(mock_llm_client, mock_skills_engine, mock_memory_manager)


@pytest.mark.asyncio
async def test_process_message_empty_history(agent_core):
    """Test processing message with no conversation history."""
    # Arrange
    user_id = "user_123"
    content = "Hello, how are you?"
    trace_id = "trace_abc"
    
    # Act
    response = await agent_core.process_message(user_id, content, trace_id)
    
    # Assert
    assert isinstance(response, str)
    assert len(response) > 0
    assert "Mock LLM response" in response


@pytest.mark.asyncio
async def test_process_message_with_history(agent_core, mock_memory_manager):
    """Test processing message with existing conversation history."""
    # Arrange
    user_id = "user_123"
    
    # Pre-populate history
    await mock_memory_manager.write_conversation(
        user_id, "user", "Previous message", "trace_1"
    )
    await mock_memory_manager.write_conversation(
        user_id, "assistant", "Previous response", "trace_1"
    )
    
    # Act
    response = await agent_core.process_message(
        user_id, "What did I say before?", "trace_2"
    )
    
    # Assert
    assert isinstance(response, str)
    # Verify history was read (2 previous messages)
    history = await mock_memory_manager.read_conversation_history(user_id)
    assert len(history) == 4  # 2 previous + 2 new (user + assistant)


@pytest.mark.asyncio
async def test_process_message_saves_conversation(agent_core, mock_memory_manager):
    """Test that message processing saves both user and assistant messages."""
    # Arrange
    user_id = "user_123"
    content = "Remember that I prefer Python"
    trace_id = "trace_xyz"
    
    # Act
    await agent_core.process_message(user_id, content, trace_id)
    
    # Assert
    history = await mock_memory_manager.read_conversation_history(user_id)
    assert len(history) == 2  # User message + assistant response
    assert history[0].role == "user"
    assert history[0].content == content
    assert history[1].role == "assistant"


@pytest.mark.asyncio
async def test_process_message_llm_failure_raises_error(agent_core):
    """Test that LLM failure raises AgentError."""
    # Arrange
    user_id = "user_123"
    content = "This will fail"
    trace_id = "trace_error"
    
    # Mock LLM to raise exception
    with patch.object(agent_core.llm, 'chat', side_effect=Exception("LLM API error")):
        # Act & Assert
        with pytest.raises(AgentError) as exc_info:
            await agent_core.process_message(user_id, content, trace_id)
        
        assert "Message processing failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_build_llm_messages_formats_correctly(agent_core, mock_memory_manager):
    """Test that _build_llm_messages formats messages correctly."""
    # Arrange
    user_id = "user_123"
    await mock_memory_manager.write_conversation(
        user_id, "user", "Message 1", "trace_1"
    )
    await mock_memory_manager.write_conversation(
        user_id, "assistant", "Response 1", "trace_1"
    )
    
    history = await mock_memory_manager.read_conversation_history(user_id)
    new_content = "Message 2"
    
    # Act
    messages = agent_core._build_llm_messages(history, new_content)
    
    # Assert
    assert len(messages) == 3  # 2 history + 1 new
    assert messages[0] == {"role": "user", "content": "Message 1"}
    assert messages[1] == {"role": "assistant", "content": "Response 1"}
    assert messages[2] == {"role": "user", "content": new_content}


@pytest.mark.asyncio
async def test_create_agent_with_mocks():
    """Test factory function creates agent with mocks."""
    # Act
    agent = create_agent_with_mocks()
    
    # Assert
    assert isinstance(agent, AgentCore)
    assert agent.llm is not None
    assert agent.skills is not None
    assert agent.memory is not None
    
    # Verify it works end-to-end
    response = await agent.process_message("user_123", "Hello", "trace_test")
    assert isinstance(response, str)


@pytest.mark.asyncio
async def test_conversation_context_limit(agent_core, mock_memory_manager):
    """Test that conversation context is limited to CONVERSATION_CONTEXT_LIMIT."""
    # Arrange
    user_id = "user_123"
    
    # Add 15 messages (exceeds limit of 10)
    for i in range(15):
        await mock_memory_manager.write_conversation(
            user_id, "user", f"Message {i}", f"trace_{i}"
        )
        await mock_memory_manager.write_conversation(
            user_id, "assistant", f"Response {i}", f"trace_{i}"
        )
    
    # Act
    await agent_core.process_message(user_id, "Latest message", "trace_final")
    
    # Assert
    # Verify only last 10 messages were used (plus the new one = 11 total)
    history = await mock_memory_manager.read_conversation_history(user_id, limit=10)
    assert len(history) == 10  # Last 10 before new message
```

**Test Coverage**:
- ✅ Empty history case
- ✅ With history case
- ✅ Saves conversation
- ✅ LLM failure handling
- ✅ Message formatting
- ✅ Factory function
- ✅ Context limit enforcement

---

### Task 7: Unit Tests for LLM Client

**Dependencies:** Task 4

**Files to Create**:
- `tests/core/test_llm_client.py` - Unit tests for LLMClient

**Test Cases** (follow pattern in test_agent.py):
- Call with valid messages → Returns response
- Call with mock exception → Raises LLMError
- Verify logging includes model, message_count, response_length
- Test with different models (gemini-2.5-flash-002)
- Test stream parameter (deferred to Story 4, just verify it's accepted)

**Concise spec** (AI agent will write full test file):
```python
# Key test functions to implement:
# - test_chat_success
# - test_chat_with_custom_model
# - test_chat_failure_raises_llm_error
# - test_chat_logs_correctly
# - test_stream_parameter_accepted (don't implement streaming, just accept param)
```

---

### Task 8: Integration Test (End-to-End with Mocks)

**Dependencies:** Task 5, Task 6, Task 7

**Files to Create**:
- `tests/core/test_integration.py` - Integration test for full flow

**Test Cases** (concise):
- Create agent with mocks → Process message → Verify response returned
- Process multiple messages → Verify conversation history grows
- Verify memory persistence (in-memory for mocks)
- Verify logging at all stages (agent → llm → memory)

---

## Reference Code Examples

### Testing Pattern

**All tests follow this pattern** (from test_agent.py above):
1. **Fixtures**: Create mocked dependencies (llm_client, skills_engine, memory_manager)
2. **Arrange**: Set up test data (user_id, content, trace_id)
3. **Act**: Call the function under test
4. **Assert**: Verify output and side effects (logging, memory writes)

**Example test structure**:
```python
@pytest.mark.asyncio
async def test_something(agent_core, mock_dependency):
    # Arrange
    user_id = "user_123"
    
    # Act
    result = await agent_core.process_message(user_id, "test", "trace")
    
    # Assert
    assert result is not None
```

### Logging Pattern

**All modules use this logging pattern**:
```python
import logging

logger = logging.getLogger(__name__)

# In functions:
logger.info(
    "Event description",
    extra={
        "trace_id": trace_id,
        "component": "agent_core",
        "key": "value"
    }
)
```

---

## Implementation Notes

### Story 4 Integration Notes

**TODO for Story 4 (Integration & Deployment)**:

1. **Replace MockVertexAI with real ChatVertexAI**:
   ```python
   from langchain_google_vertexai import ChatVertexAI
   vertex_llm = ChatVertexAI(model_name="gemini-2.5-flash-002")
   llm_client = LLMClient(vertex_llm)
   ```

2. **Add retry logic** (3x exponential backoff):
   - Use `tenacity` library or LangChain's built-in retry
   - Handle 429 (rate limit), 503 (service unavailable)
   - Timeout: 60 seconds

3. **Add streaming support**:
   - Enable streaming for responses > 200 tokens
   - Use `astream()` instead of `ainvoke()`
   - Buffer chunks and return complete response

4. **Wire real implementations**:
   - Replace `MockSkillsEngine` with real `SkillsEngine` from Story 3
   - Replace `MockMemoryManager` with real `MemoryManager` from Story 3
   - Remove mock imports from `src/main.py`

5. **Add Vertex AI initialization**:
   ```python
   from google.cloud import aiplatform
   aiplatform.init(project=PROJECT_ID, location=LOCATION)
   ```

### Development Workflow

**Local development**:
```bash
# Install dependencies
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Run tests
pytest tests/core/

# Run with coverage
pytest --cov=src/core --cov-report=term-missing

# Type check
mypy src/core/

# Format code
ruff format src/ tests/
ruff check src/ tests/ --fix
```

**Testing strategy**:
- Sprint 1: All tests use mocks (no real Vertex AI, Skills Engine, Memory Manager)
- Story 4: Add integration tests with real components
- Keep unit tests with mocks for fast execution

---

## Final Verification Checklist

**Functionality**:
- [ ] AgentCore implements AgentCoreInterface
- [ ] LLMClient calls MockVertexAI successfully
- [ ] Conversation context limited to 10 messages
- [ ] Messages saved to mock memory (user + assistant)
- [ ] Error handling works (LLMError, AgentError)

**Code Quality**:
- [ ] All functions have type hints
- [ ] All public functions have docstrings (Google style)
- [ ] Follows naming conventions (snake_case, PascalCase)
- [ ] No hardcoded values (use constants)
- [ ] Logging includes trace_id and component

**Testing**:
- [ ] Unit tests pass (`pytest tests/core/`)
- [ ] Test coverage > 80% (`pytest --cov`)
- [ ] Tests use mocks (no real API calls)
- [ ] Test logging output (use caplog fixture)

**Type Checking**:
- [ ] `mypy src/core/` passes with no errors
- [ ] All interfaces properly typed
- [ ] Dataclasses validated

**Code Style**:
- [ ] `ruff format src/ tests/` applied
- [ ] `ruff check src/ tests/` passes
- [ ] Imports sorted (isort via ruff)
- [ ] Line length < 100 chars

**Documentation**:
- [ ] README.md created with quick start
- [ ] All interfaces documented in interfaces.py
- [ ] Story 4 integration notes added to this spec
- [ ] Mock usage clearly documented

---

## Success Criteria

✅ **All acceptance criteria met**:
- Agent Core processes messages with empty history
- Agent Core processes messages with conversation context (last 10)
- LLM Client calls MockVertexAI successfully
- Messages saved to memory (user + assistant)
- Error handling works (LLMError → AgentError)
- All tests pass independently (no dependencies on Story 1 or Story 3)
- Type hints and docstrings on all public functions

✅ **Ready for Story 4 integration**:
- Interfaces defined and documented
- Mocks provided for Gateway (Story 1) and Skills/Memory (Story 3)
- Clear integration notes for wiring real implementations

✅ **Code quality standards**:
- 80%+ test coverage
- Type checking passes
- Linting passes
- Logging structured and consistent

---

**Story 2 Complete!** ✓ Ready for parallel execution with Story 1 and Story 3.
