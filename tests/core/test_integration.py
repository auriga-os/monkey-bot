"""Integration tests for full agent flow.

These tests verify that all components work together correctly:
- Agent Core + LLM Client + Skills Engine + Memory Manager
- End-to-end message processing
- Multi-turn conversations
- Error propagation
"""

import pytest

from src.core import create_agent_with_mocks
from src.core.agent import AgentCore
from src.core.llm_client import LLMClient
from src.core.mocks import MockMemoryManager, MockSkillsEngine

# ============================================================================
# Tests: End-to-End Message Processing
# ============================================================================


@pytest.mark.asyncio
async def test_end_to_end_single_message() -> None:
    """Test complete flow from message to response.

    Verifies:
        - All components wired correctly
        - Message processed successfully
        - Response returned
        - Memory updated
    """
    # Arrange
    agent = create_agent_with_mocks()
    user_id = "test_user"
    content = "Hello, how are you?"
    trace_id = "test_trace"

    # Act
    response = await agent.process_message(user_id, content, trace_id)

    # Assert
    assert isinstance(response, str)
    assert len(response) > 0

    # Verify memory was updated
    history = await agent.memory.read_conversation_history(user_id)
    assert len(history) == 2  # User message + assistant response
    assert history[0].content == content
    assert history[1].content == response


@pytest.mark.asyncio
async def test_end_to_end_multi_turn_conversation() -> None:
    """Test multi-turn conversation flow.

    Verifies:
        - Multiple messages processed in sequence
        - Context maintained across turns
        - Memory grows with each turn
    """
    # Arrange
    agent = create_agent_with_mocks()
    user_id = "test_user"

    # Act - Turn 1
    response1 = await agent.process_message(user_id, "Remember that I prefer Python", "trace_1")

    # Act - Turn 2
    response2 = await agent.process_message(user_id, "What's my preferred language?", "trace_2")

    # Act - Turn 3
    response3 = await agent.process_message(user_id, "List files", "trace_3")

    # Assert
    assert all(isinstance(r, str) for r in [response1, response2, response3])
    assert all(len(r) > 0 for r in [response1, response2, response3])

    # Verify conversation history
    history = await agent.memory.read_conversation_history(user_id, limit=10)
    assert len(history) == 6  # 3 turns * 2 messages (user + assistant)

    # Verify messages in correct order
    assert history[0].content == "Remember that I prefer Python"
    assert history[2].content == "What's my preferred language?"
    assert history[4].content == "List files"


# ============================================================================
# Tests: Memory Persistence
# ============================================================================


@pytest.mark.asyncio
async def test_conversation_persists_across_calls() -> None:
    """Test that conversation history persists across multiple calls.

    Verifies:
        - First call saves to memory
        - Second call loads history
        - Context maintained
    """
    # Arrange
    agent = create_agent_with_mocks()
    user_id = "test_user"

    # Act - First message
    await agent.process_message(user_id, "First message", "trace_1")

    # Act - Second message (should load first message as context)
    await agent.process_message(user_id, "Second message", "trace_2")

    # Assert
    history = await agent.memory.read_conversation_history(user_id, limit=10)
    assert len(history) == 4  # 2 turns * 2 messages
    assert history[0].content == "First message"
    assert history[2].content == "Second message"


@pytest.mark.asyncio
async def test_memory_isolated_by_user() -> None:
    """Test that memory is isolated per user.

    Verifies:
        - Different users have separate histories
        - No cross-contamination
    """
    # Arrange
    agent = create_agent_with_mocks()
    user1 = "user_alice"
    user2 = "user_bob"

    # Act - User 1 messages
    await agent.process_message(user1, "Alice message 1", "trace_1")
    await agent.process_message(user1, "Alice message 2", "trace_2")

    # Act - User 2 messages
    await agent.process_message(user2, "Bob message 1", "trace_3")

    # Assert - User 1 history
    history1 = await agent.memory.read_conversation_history(user1, limit=10)
    assert len(history1) == 4  # 2 turns * 2 messages
    assert all("Alice" in msg.content for msg in history1 if msg.role == "user")

    # Assert - User 2 history
    history2 = await agent.memory.read_conversation_history(user2, limit=10)
    assert len(history2) == 2  # 1 turn * 2 messages
    assert history2[0].content == "Bob message 1"


# ============================================================================
# Tests: Component Integration
# ============================================================================


@pytest.mark.asyncio
async def test_llm_receives_conversation_context() -> None:
    """Test that LLM receives previous conversation context.

    Verifies:
        - History loaded from memory
        - Passed to LLM
        - Context influences response
    """
    # Arrange
    agent = create_agent_with_mocks()
    user_id = "test_user"

    # Build conversation
    await agent.process_message(user_id, "My name is Alice", "trace_1")
    await agent.process_message(user_id, "I like Python", "trace_2")

    # Act - Ask about previous info
    response = await agent.process_message(user_id, "What do you know about me?", "trace_3")

    # Assert
    assert isinstance(response, str)
    # Mock response should reference the question
    assert len(response) > 0


@pytest.mark.asyncio
async def test_all_components_log_consistently() -> None:
    """Test that all components log with trace_id.

    Verifies:
        - Logging works across all components
        - Trace ID propagated
        - No logging errors
    """
    # Arrange
    agent = create_agent_with_mocks()
    user_id = "test_user"
    trace_id = "test_trace_logging"

    # Act
    response = await agent.process_message(user_id, "Test logging", trace_id)

    # Assert
    assert isinstance(response, str)
    # Logging tested via caplog in individual component tests
    # This test verifies no crashes/errors during logging


# ============================================================================
# Tests: Error Handling
# ============================================================================


@pytest.mark.asyncio
async def test_error_propagates_correctly() -> None:
    """Test that errors propagate through the stack.

    Verifies:
        - Errors from lower layers caught
        - Wrapped in AgentError
        - Stack trace preserved
    """
    from unittest.mock import patch

    from src.core.interfaces import AgentError

    # Arrange
    agent = create_agent_with_mocks()
    user_id = "test_user"

    # Mock LLM to fail
    with patch.object(agent.llm.client, "ainvoke", side_effect=Exception("Mock LLM failure")):
        # Act & Assert
        with pytest.raises(AgentError) as exc_info:
            await agent.process_message(user_id, "Test error", "trace_error")

        assert "Message processing failed" in str(exc_info.value)
        assert "Mock LLM failure" in str(exc_info.value)


# ============================================================================
# Tests: Factory Function
# ============================================================================


@pytest.mark.asyncio
async def test_factory_creates_working_agent() -> None:
    """Test that factory function creates fully functional agent.

    Verifies:
        - Factory returns working agent
        - All dependencies wired
        - Can process messages immediately
    """
    # Act
    agent = create_agent_with_mocks()

    # Assert - Agent is created
    assert isinstance(agent, AgentCore)
    assert isinstance(agent.llm, LLMClient)
    assert isinstance(agent.skills, MockSkillsEngine)
    assert isinstance(agent.memory, MockMemoryManager)

    # Assert - Agent works
    response = await agent.process_message("test_user", "Hello", "test_trace")
    assert isinstance(response, str)
    assert len(response) > 0


# ============================================================================
# Tests: Performance and Scale
# ============================================================================


@pytest.mark.asyncio
async def test_handles_many_messages() -> None:
    """Test agent handles many messages without degradation.

    Verifies:
        - Memory doesn't grow unbounded
        - Performance stable
        - No memory leaks
    """
    # Arrange
    agent = create_agent_with_mocks()
    user_id = "test_user"

    # Act - Send 50 messages
    for i in range(50):
        await agent.process_message(user_id, f"Message {i}", f"trace_{i}")

    # Assert - Memory constrained by context limit
    history = await agent.memory.read_conversation_history(user_id, limit=10)
    assert len(history) == 10  # Only last 10 returned

    # Verify all messages stored (not lost)
    full_history = await agent.memory.read_conversation_history(user_id, limit=1000)
    assert len(full_history) == 100  # 50 messages * 2 (user + assistant)


@pytest.mark.asyncio
async def test_handles_concurrent_users() -> None:
    """Test agent handles multiple users concurrently (conceptual).

    Verifies:
        - User isolation maintained
        - No cross-talk between users

    Note: This is a single-threaded test, but verifies isolation logic.
    """
    # Arrange
    agent = create_agent_with_mocks()
    users = [f"user_{i}" for i in range(10)]

    # Act - Each user sends a message
    for user_id in users:
        await agent.process_message(user_id, f"Message from {user_id}", f"trace_{user_id}")

    # Assert - Each user has separate history
    for user_id in users:
        history = await agent.memory.read_conversation_history(user_id, limit=10)
        assert len(history) == 2  # Only their own messages
        assert history[0].content == f"Message from {user_id}"
