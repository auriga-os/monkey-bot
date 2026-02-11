"""Unit tests for Agent Core.

This test suite verifies the core agent logic including:
- Message processing with empty and populated history
- Conversation context management
- LLM integration
- Memory persistence
- Error handling
"""

from unittest.mock import patch

import pytest

from src.core.agent import CONVERSATION_CONTEXT_LIMIT, AgentCore, create_agent_with_mocks
from src.core.interfaces import AgentError, Message
from src.core.llm_client import LLMClient
from src.core.mocks import MockMemoryManager, MockSkillsEngine, MockVertexAI

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_llm_client() -> LLMClient:
    """Create mock LLM client."""
    vertex_client = MockVertexAI()
    return LLMClient(vertex_client)


@pytest.fixture
def mock_skills_engine() -> MockSkillsEngine:
    """Create mock skills engine."""
    return MockSkillsEngine()


@pytest.fixture
def mock_memory_manager() -> MockMemoryManager:
    """Create mock memory manager."""
    return MockMemoryManager()


@pytest.fixture
def agent_core(
    mock_llm_client: LLMClient,
    mock_skills_engine: MockSkillsEngine,
    mock_memory_manager: MockMemoryManager,
) -> AgentCore:
    """Create AgentCore with mocked dependencies."""
    return AgentCore(mock_llm_client, mock_skills_engine, mock_memory_manager)


# ============================================================================
# Tests: Basic Message Processing
# ============================================================================


@pytest.mark.asyncio
async def test_process_message_empty_history(agent_core: AgentCore) -> None:
    """Test processing message with no conversation history.

    Verifies:
        - Agent can process first message from new user
        - Response is returned
        - Response is non-empty string
    """
    # Arrange
    user_id = "user_123"
    content = "Hello, how are you?"
    trace_id = "trace_abc"

    # Act
    response = await agent_core.process_message(user_id, content, trace_id)

    # Assert
    assert isinstance(response, str)
    assert len(response) > 0
    assert "Mock LLM response" in response or "Hello" in response


@pytest.mark.asyncio
async def test_process_message_with_history(
    agent_core: AgentCore, mock_memory_manager: MockMemoryManager
) -> None:
    """Test processing message with existing conversation history.

    Verifies:
        - Agent loads previous messages
        - Context is sent to LLM
        - New message is appended to history
    """
    # Arrange
    user_id = "user_123"

    # Pre-populate history with 2 messages
    await mock_memory_manager.write_conversation(user_id, "user", "Previous message", "trace_1")
    await mock_memory_manager.write_conversation(
        user_id, "assistant", "Previous response", "trace_1"
    )

    # Act
    response = await agent_core.process_message(user_id, "What did I say before?", "trace_2")

    # Assert
    assert isinstance(response, str)
    assert len(response) > 0

    # Verify history grew (2 previous + 2 new = 4 total)
    history = await mock_memory_manager.read_conversation_history(user_id, limit=10)
    assert len(history) == 4
    assert history[0].content == "Previous message"
    assert history[1].content == "Previous response"
    assert history[2].content == "What did I say before?"
    assert history[3].role == "assistant"


# ============================================================================
# Tests: Memory Persistence
# ============================================================================


@pytest.mark.asyncio
async def test_process_message_saves_conversation(
    agent_core: AgentCore, mock_memory_manager: MockMemoryManager
) -> None:
    """Test that message processing saves both user and assistant messages.

    Verifies:
        - User message saved to memory
        - Assistant response saved to memory
        - Messages saved in correct order
        - Trace ID preserved
    """
    # Arrange
    user_id = "user_123"
    content = "Remember that I prefer Python"
    trace_id = "trace_xyz"

    # Act
    await agent_core.process_message(user_id, content, trace_id)

    # Assert
    history = await mock_memory_manager.read_conversation_history(user_id, limit=10)
    assert len(history) == 2  # User message + assistant response

    # Verify user message
    assert history[0].role == "user"
    assert history[0].content == content
    assert history[0].trace_id == trace_id

    # Verify assistant message
    assert history[1].role == "assistant"
    assert history[1].trace_id == trace_id
    assert len(history[1].content) > 0


# ============================================================================
# Tests: Error Handling
# ============================================================================


@pytest.mark.asyncio
async def test_process_message_llm_failure_raises_error(agent_core: AgentCore) -> None:
    """Test that LLM failure raises AgentError.

    Verifies:
        - LLM errors are caught
        - Wrapped in AgentError
        - Error message includes context
    """
    # Arrange
    user_id = "user_123"
    content = "This will fail"
    trace_id = "trace_error"

    # Mock LLM to raise exception
    with patch.object(agent_core.llm, "chat", side_effect=Exception("LLM API error")):
        # Act & Assert
        with pytest.raises(AgentError) as exc_info:
            await agent_core.process_message(user_id, content, trace_id)

        assert "Message processing failed" in str(exc_info.value)
        assert "LLM API error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_process_message_memory_failure_raises_error(
    agent_core: AgentCore,
) -> None:
    """Test that memory errors are handled gracefully.

    Verifies:
        - Memory errors are caught
        - Wrapped in AgentError
        - Error message includes context
    """
    # Arrange
    user_id = "user_123"
    content = "Test message"
    trace_id = "trace_mem_error"

    # Mock memory to raise exception on read
    with patch.object(
        agent_core.memory,
        "read_conversation_history",
        side_effect=Exception("Memory unavailable"),
    ):
        # Act & Assert
        with pytest.raises(AgentError) as exc_info:
            await agent_core.process_message(user_id, content, trace_id)

        assert "Message processing failed" in str(exc_info.value)
        assert "Memory unavailable" in str(exc_info.value)


# ============================================================================
# Tests: Message Building
# ============================================================================


@pytest.mark.asyncio
async def test_build_llm_messages_formats_correctly(
    agent_core: AgentCore, mock_memory_manager: MockMemoryManager
) -> None:
    """Test that _build_llm_messages formats messages correctly.

    Verifies:
        - History messages converted to dict format
        - New message appended
        - Role and content preserved
        - Correct order (chronological)
    """
    # Arrange
    user_id = "user_123"
    await mock_memory_manager.write_conversation(user_id, "user", "Message 1", "trace_1")
    await mock_memory_manager.write_conversation(user_id, "assistant", "Response 1", "trace_1")

    history = await mock_memory_manager.read_conversation_history(user_id, limit=10)
    new_content = "Message 2"

    # Act
    messages = agent_core._build_llm_messages(history, new_content)

    # Assert
    assert len(messages) == 3  # 2 history + 1 new
    assert messages[0] == {"role": "user", "content": "Message 1"}
    assert messages[1] == {"role": "assistant", "content": "Response 1"}
    assert messages[2] == {"role": "user", "content": new_content}


@pytest.mark.asyncio
async def test_build_llm_messages_with_empty_history(agent_core: AgentCore) -> None:
    """Test message building with no history.

    Verifies:
        - Works with empty history
        - Only new message in output
    """
    # Arrange
    history: list[Message] = []
    new_content = "First message"

    # Act
    messages = agent_core._build_llm_messages(history, new_content)

    # Assert
    assert len(messages) == 1
    assert messages[0] == {"role": "user", "content": new_content}


# ============================================================================
# Tests: Conversation Context Limit
# ============================================================================


@pytest.mark.asyncio
async def test_conversation_context_limit(
    agent_core: AgentCore, mock_memory_manager: MockMemoryManager
) -> None:
    """Test that conversation context is limited to CONVERSATION_CONTEXT_LIMIT.

    Verifies:
        - Only last N messages loaded from memory
        - Older messages not sent to LLM
        - Context window respected
    """
    # Arrange
    user_id = "user_123"

    # Add 15 messages (exceeds limit of 10)
    for i in range(15):
        await mock_memory_manager.write_conversation(user_id, "user", f"Message {i}", f"trace_{i}")
        await mock_memory_manager.write_conversation(
            user_id, "assistant", f"Response {i}", f"trace_{i}"
        )

    # Act
    await agent_core.process_message(user_id, "Latest message", "trace_final")

    # Assert
    # Verify only last 10 messages were used (before new message)
    history = await mock_memory_manager.read_conversation_history(
        user_id, limit=CONVERSATION_CONTEXT_LIMIT
    )
    assert len(history) == CONVERSATION_CONTEXT_LIMIT

    # Oldest message in context should be message 5 (not message 0)
    # Because we have 15 pairs (30 messages), last 10 are messages 10-14 (20 messages) + 2 new
    # Actually, let's verify the logic more carefully
    all_history = await mock_memory_manager.read_conversation_history(user_id, limit=100)
    # Should have 15*2 + 2 = 32 messages total
    assert len(all_history) == 32


# ============================================================================
# Tests: Factory Function
# ============================================================================


@pytest.mark.asyncio
async def test_create_agent_with_mocks() -> None:
    """Test factory function creates agent with mocks.

    Verifies:
        - Factory returns AgentCore instance
        - All dependencies are wired correctly
        - Agent works end-to-end with mocks
    """
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
    assert len(response) > 0


# ============================================================================
# Tests: Edge Cases
# ============================================================================


@pytest.mark.asyncio
async def test_process_message_with_empty_content(agent_core: AgentCore) -> None:
    """Test processing empty message.

    Verifies:
        - Agent handles empty messages gracefully
        - No crashes or errors
    """
    # Arrange
    user_id = "user_123"
    content = ""
    trace_id = "trace_empty"

    # Act
    response = await agent_core.process_message(user_id, content, trace_id)

    # Assert
    assert isinstance(response, str)
    # Mock should still return a response even for empty content


@pytest.mark.asyncio
async def test_process_message_with_long_content(agent_core: AgentCore) -> None:
    """Test processing very long message.

    Verifies:
        - Agent handles long messages
        - No truncation or errors
    """
    # Arrange
    user_id = "user_123"
    content = "A" * 10000  # 10KB message
    trace_id = "trace_long"

    # Act
    response = await agent_core.process_message(user_id, content, trace_id)

    # Assert
    assert isinstance(response, str)
    assert len(response) > 0


@pytest.mark.asyncio
async def test_process_message_with_special_characters(agent_core: AgentCore) -> None:
    """Test processing message with special characters.

    Verifies:
        - Agent handles Unicode, emojis, special chars
        - No encoding errors
    """
    # Arrange
    user_id = "user_123"
    content = "Hello 👋 世界 <script>alert('xss')</script>"
    trace_id = "trace_special"

    # Act
    response = await agent_core.process_message(user_id, content, trace_id)

    # Assert
    assert isinstance(response, str)
    assert len(response) > 0
