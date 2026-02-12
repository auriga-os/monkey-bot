"""LangGraph-based agent orchestration.

This module implements the core agent logic, coordinating between the LLM,
skills engine, and memory manager to process user messages.
"""

import asyncio
import contextlib
import logging

from .interfaces import (
    AgentCoreInterface,
    AgentError,
    MemoryManagerInterface,
    Message,
    SkillsEngineInterface,
)
from .llm_client import LLMClient
from .scheduler import CronScheduler

logger = logging.getLogger(__name__)

# Configuration constants
# These can be overridden via environment variables in production
CONVERSATION_CONTEXT_LIMIT = 10  # Last N messages sent to LLM
DEFAULT_MODEL = "gemini-2.5-flash-002"


class AgentCore(AgentCoreInterface):
    """LangGraph-based agent orchestration.

    This is the central orchestrator that coordinates all agent components:
    - Manages conversation context (last N messages)
    - Routes messages to LLM
    - Executes skills (future - Story 4)
    - Persists conversation history

    Simple single-step agent for Sprint 1:
        1. Load conversation context (last 10 messages)
        2. Call LLM with context + new message
        3. Save conversation history (user + assistant messages)
        4. Return response

    Future (Story 4):
        - Add multi-step reasoning
        - Add tool calling (skills as LangGraph tools)
        - Add streaming support
        - Add retry logic

    Key design principles:
        - Simple and maintainable
        - Clear error handling
        - Comprehensive logging with trace IDs
        - Dependency injection for testability

    Example:
        >>> from src.core import create_agent_with_mocks
        >>> agent = create_agent_with_mocks()
        >>> response = await agent.process_message(
        ...     user_id="user123",
        ...     content="Hello, how are you?",
        ...     trace_id="trace_abc"
        ... )
        >>> print(response)
        "Hello! I'm Emonk, your AI assistant. How can I help you today?"
    """

    def __init__(
        self,
        llm_client: LLMClient,
        skills_engine: SkillsEngineInterface,
        memory_manager: MemoryManagerInterface,
        scheduler_check_interval: int = 10,
    ) -> None:
        """Initialize Agent Core.

        Uses dependency injection for testability - all dependencies are
        passed in rather than created internally.

        Args:
            llm_client: LLM client wrapper for Vertex AI
            skills_engine: Skills execution engine (MockSkillsEngine for Sprint 1)
            memory_manager: Memory manager (MockMemoryManager for Sprint 1)
            scheduler_check_interval: Seconds between scheduler checks (default 10)
        """
        self.llm = llm_client
        self.skills = skills_engine
        self.memory = memory_manager

        # Initialize scheduler for background jobs (Sprint 3)
        # Note: Scheduler must be explicitly started with start_scheduler()
        self.scheduler = CronScheduler(
            agent_state=memory_manager,  # Pass memory manager as agent state
            check_interval_seconds=scheduler_check_interval
        )
        self._scheduler_task = None

    async def process_message(self, user_id: str, content: str, trace_id: str) -> str:
        """Process user message and return response.

        This is the main entry point for all user interactions. It orchestrates
        the entire request flow from message receipt to response generation.

        Flow:
            1. Load conversation context (last 10 messages from memory)
            2. Build messages list for LLM (history + new user message)
            3. Call LLM to generate response
            4. Save user message to memory
            5. Save assistant response to memory
            6. Return response to caller (Gateway)

        Args:
            user_id: Hashed user identifier (not email - already filtered by Gateway)
            content: Message text (PII already filtered by Gateway)
            trace_id: Request trace ID for debugging and log correlation

        Returns:
            Response text to send back to user via Gateway

        Raises:
            AgentError: If processing fails (LLM error, memory error, etc.)
                       The error message includes the root cause for debugging.

        Example:
            >>> agent = AgentCore(llm, skills, memory)
            >>> response = await agent.process_message(
            ...     user_id="abc123",
            ...     content="Remember that I prefer Python",
            ...     trace_id="trace_xyz"
            ... )
            >>> print(response)
            "I'll remember that you prefer Python for all code examples."
        """
        logger.info(
            "Processing message",
            extra={
                "trace_id": trace_id,
                "component": "agent_core",
                "user_id": user_id,
                "content_length": len(content),
            },
        )

        try:
            # Step 1: Load conversation context (last N messages)
            history = await self.memory.read_conversation_history(
                user_id, limit=CONVERSATION_CONTEXT_LIMIT
            )

            logger.debug(
                f"Loaded conversation history: {len(history)} messages",
                extra={
                    "trace_id": trace_id,
                    "component": "agent_core",
                    "history_count": len(history),
                },
            )

            # Step 2: Build messages for LLM (history + new user message)
            messages = self._build_llm_messages(history, content)

            # Step 3: Call LLM to generate response
            response = await self.llm.chat(
                messages=messages,
                model=DEFAULT_MODEL,
                stream=False,  # Streaming deferred to Story 4
            )

            # Step 4: Save user message to memory
            await self.memory.write_conversation(user_id, "user", content, trace_id)

            # Step 5: Save assistant response to memory
            await self.memory.write_conversation(user_id, "assistant", response, trace_id)

            logger.info(
                "Message processed successfully",
                extra={
                    "trace_id": trace_id,
                    "component": "agent_core",
                    "response_length": len(response),
                },
            )

            return response

        except Exception as e:
            # Wrap all errors in AgentError for consistent error handling
            error_msg = f"Message processing failed: {e}"
            logger.error(
                error_msg,
                extra={
                    "trace_id": trace_id,
                    "component": "agent_core",
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
            )
            raise AgentError(error_msg) from e

    def _build_llm_messages(self, history: list[Message], new_content: str) -> list[dict[str, str]]:
        """Build messages list for LLM from history + new message.

        Converts Message objects to LLM-friendly dict format and appends
        the new user message.

        Args:
            history: Recent conversation messages (from memory)
            new_content: New user message content

        Returns:
            List of message dicts in LLM format: [{"role": "user", "content": "..."}]

        Example:
            >>> history = [
            ...     Message(role="user", content="Hi", timestamp="...", trace_id="..."),
            ...     Message(role="assistant", content="Hello!", timestamp="...", trace_id="...")
            ... ]
            >>> messages = agent._build_llm_messages(history, "How are you?")
            >>> print(messages)
            [
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello!"},
                {"role": "user", "content": "How are you?"}
            ]
        """
        messages: list[dict[str, str]] = []

        # Add conversation history
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})

        # Add new user message
        messages.append({"role": "user", "content": new_content})

        return messages

    async def start_scheduler(self):
        """Start the background scheduler for scheduled posts.

        The scheduler runs in a background task and processes jobs
        at their scheduled times. Call stop_scheduler() to terminate.

        Example:
            >>> agent = AgentCore(llm, skills, memory)
            >>> await agent.start_scheduler()
            >>> # ... agent processes messages ...
            >>> await agent.stop_scheduler()
        """
        if self._scheduler_task is None:
            self._scheduler_task = asyncio.create_task(self.scheduler.start())
            logger.info("Scheduler started")
        else:
            logger.warning("Scheduler already running")

    async def stop_scheduler(self):
        """Stop the background scheduler.

        Terminates the scheduler background task and waits for
        it to complete cleanup.
        """
        if self._scheduler_task is not None:
            await self.scheduler.stop()
            with contextlib.suppress(asyncio.CancelledError):
                await self._scheduler_task
            self._scheduler_task = None
            logger.info("Scheduler stopped")
        else:
            logger.warning("Scheduler not running")


# ============================================================================
# Factory Functions
# ============================================================================


def create_agent_with_mocks() -> AgentCore:
    """Create agent with mock dependencies for testing.

    This factory function is useful for:
        - Quick testing without setting up real dependencies
        - Integration tests that don't need real LLM/Skills/Memory
        - Demonstration and examples

    Returns:
        AgentCore with MockVertexAI, MockSkillsEngine, MockMemoryManager

    Example:
        >>> agent = create_agent_with_mocks()
        >>> response = await agent.process_message(
        ...     user_id="test_user",
        ...     content="Hello",
        ...     trace_id="test_trace"
        ... )
        >>> print(response)
        "Hello! I'm Emonk, your AI assistant. How can I help you today?"
    """
    from .mocks import MockMemoryManager, MockSkillsEngine, MockVertexAI

    llm_client = LLMClient(vertex_client=MockVertexAI())
    skills_engine = MockSkillsEngine()
    memory_manager = MockMemoryManager()

    return AgentCore(llm_client, skills_engine, memory_manager)
